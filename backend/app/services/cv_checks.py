"""İş arayanın CV değerlendirmeleri: oluşturma, listeleme, yeniden deneme, silme.

Her sorgu sahibine göre süzülür; başkasının kaydı "bulunamadı" döner (varlığı sızmasın).
"""

import hashlib
from datetime import timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.db import utc_now
from app.core.errors import ConflictError, FieldValidationError, NotFoundError, TooManyRequestsError
from app.models import CVCheck, ProcessingStatus
from app.schemas.cv_check import CVCheckCriteria
from app.services import audit
from app.services.candidates import (
    EMPTY_FILE,
    NO_TEXT,
    TOO_LARGE,
    UNREADABLE,
    UNSUPPORTED_TYPE,
    IncomingFile,
    safe_filename,
)
from app.services.cv_extract import (
    MAX_FILE_BYTES,
    MIN_TEXT_LENGTH,
    ExtractionError,
    detect_kind,
    extract_text,
)
from app.services.pipeline import PARSE_FAILED
from app.storage.files import FileStorage

# Herkese açık kayıtla ücretsiz LLM kotası hızla tükenmesin diye kullanıcı başına sınır.
DAILY_LIMIT = 10
_LIMIT_WINDOW = timedelta(hours=24)
NOT_FOUND = "Değerlendirme bulunamadı"
_EXTRACTION_ERRORS = frozenset({NO_TEXT, UNREADABLE})


def _check_daily_limit(db: Session, owner_id: int) -> None:
    recent = db.scalar(
        select(func.count())
        .select_from(CVCheck)
        .where(CVCheck.owner_id == owner_id, CVCheck.created_at >= utc_now() - _LIMIT_WINDOW)
    )
    if (recent or 0) >= DAILY_LIMIT:
        raise TooManyRequestsError(
            f"Günlük değerlendirme sınırına ulaştın ({DAILY_LIMIT}). Yarın tekrar deneyebilirsin."
        )


def create_check(
    db: Session,
    storage: FileStorage,
    *,
    owner_id: int,
    criteria: CVCheckCriteria,
    file: IncomingFile,
) -> CVCheck:
    """Dosyayı doğrular, saklar, metni çıkarır; ayrıştırma ve puanlama arka planda yapılır."""
    _check_daily_limit(db, owner_id)
    if not file.data:
        raise FieldValidationError("file", EMPTY_FILE)
    if len(file.data) > MAX_FILE_BYTES:
        raise FieldValidationError("file", TOO_LARGE)
    kind = detect_kind(file.data)
    if kind is None:
        raise FieldValidationError("file", UNSUPPORTED_TYPE)

    parse_error: str | None = None
    try:
        cv_text = extract_text(file.data, kind)
    except ExtractionError:
        cv_text, parse_error = "", UNREADABLE
    if parse_error is None and len(cv_text) < MIN_TEXT_LENGTH:
        parse_error = NO_TEXT
    failed = parse_error is not None

    stored_name = storage.save(file.data, kind.value)
    try:
        check = CVCheck(
            owner_id=owner_id,
            **criteria.model_dump(mode="json"),
            original_filename=safe_filename(file.filename),
            stored_path=stored_name,
            file_hash=hashlib.sha256(file.data).hexdigest(),
            cv_text=cv_text,
            parse_status=ProcessingStatus.FAILED if failed else ProcessingStatus.PENDING,
            parse_error=parse_error,
            score_status=ProcessingStatus.FAILED if failed else ProcessingStatus.PENDING,
            score_error=PARSE_FAILED if failed else None,
        )
        db.add(check)
        db.flush()
        audit.record(
            db,
            actor_id=owner_id,
            action="cv_check.create",
            entity_type="cv_check",
            entity_id=check.id,
            payload={"status": check.parse_status.value},
        )
        db.commit()
    except Exception:
        # Kayıt yazılamadıysa dosya diskte sahipsiz kalmasın.
        db.rollback()
        storage.delete(stored_name)
        raise
    return check


def list_checks(db: Session, owner_id: int) -> list[CVCheck]:
    return list(
        db.scalars(
            select(CVCheck)
            .where(CVCheck.owner_id == owner_id)
            .order_by(CVCheck.created_at.desc(), CVCheck.id.desc())
        )
    )


def get_check(db: Session, *, check_id: int, owner_id: int) -> CVCheck:
    check = db.get(CVCheck, check_id)
    if check is None or check.owner_id != owner_id:
        raise NotFoundError(NOT_FOUND)
    return check


def retry_check(db: Session, *, check_id: int, owner_id: int) -> int:
    """Ayrıştırma başarısızsa yeniden ayrıştırma + puanlama, yalnızca puanlama ise puanlama."""
    check = get_check(db, check_id=check_id, owner_id=owner_id)
    if check.parse_status is ProcessingStatus.FAILED:
        if check.parse_error in _EXTRACTION_ERRORS:
            raise ConflictError(
                "Bu dosyadan metin çıkarılamadı; yeniden denemek sonucu değiştirmez. "
                "CV'ni metin içeren bir PDF veya DOCX olarak yeniden yükle."
            )
        check.parse_status = ProcessingStatus.PENDING
        check.parse_error = None
        step = "parse"
    elif check.score_status is ProcessingStatus.FAILED:
        step = "score"
    else:
        raise ConflictError("Yeniden denenecek bir hata yok")

    check.score_status = ProcessingStatus.PENDING
    check.score_error = None
    audit.record(
        db,
        actor_id=owner_id,
        action="cv_check.retry",
        entity_type="cv_check",
        entity_id=check_id,
        payload={"step": step},
    )
    db.commit()
    return check_id


def delete_check(db: Session, storage: FileStorage, *, check_id: int, owner_id: int) -> None:
    check = get_check(db, check_id=check_id, owner_id=owner_id)
    stored_path = check.stored_path
    db.delete(check)
    audit.record(
        db,
        actor_id=owner_id,
        action="cv_check.delete",
        entity_type="cv_check",
        entity_id=check_id,
    )
    db.commit()
    storage.delete(stored_path)
