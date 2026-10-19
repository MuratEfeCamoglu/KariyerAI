import hashlib
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import ConflictError, FieldValidationError, NotFoundError
from app.models import Application, Candidate, JobStatus, ProcessingStatus
from app.services import audit
from app.services.cv_extract import (
    MAX_FILE_BYTES,
    MIN_TEXT_LENGTH,
    ExtractionError,
    detect_kind,
    extract_text,
)
from app.services.jobs import get_job
from app.services.pipeline import PARSE_FAILED
from app.storage.files import FileStorage

MAX_FILES_PER_UPLOAD = 20

DUPLICATE_CV = "Bu CV bu ilana zaten yüklendi"
TOO_LARGE = "Dosya 5 MB'tan büyük"
UNSUPPORTED_TYPE = "Yalnızca PDF ve DOCX dosyaları kabul edilir"
EMPTY_FILE = "Dosya boş"
UNREADABLE = "Dosya okunamadı"
NO_TEXT = "Metin çıkarılamadı (taranmış/görsel PDF olabilir)"


@dataclass(frozen=True)
class IncomingFile:
    filename: str
    # Boyut kontrolü için en fazla MAX_FILE_BYTES + 1 bayt okunmuş içerik.
    data: bytes


@dataclass(frozen=True)
class FileResult:
    filename: str
    application_id: int | None = None
    status_code: int | None = None
    detail: str | None = None

    @property
    def accepted(self) -> bool:
        return self.application_id is not None


def safe_filename(name: str) -> str:
    # Bazı tarayıcılar tam yol gönderir; yalnızca dosya adı saklanır.
    base = name.replace("\\", "/").rsplit("/", 1)[-1].strip()
    return (base or "dosya")[:255]


def _existing_hashes(db: Session, job_id: int, hashes: set[str]) -> set[str]:
    return set(
        db.scalars(
            select(Candidate.file_hash)
            .join(Application, Application.candidate_id == Candidate.id)
            .where(Application.job_id == job_id, Candidate.file_hash.in_(hashes))
        )
    )


def upload_cvs(
    db: Session,
    storage: FileStorage,
    *,
    job_id: int,
    files: list[IncomingFile],
    actor_id: int,
) -> list[FileResult]:
    """F4: dosyaları doğrular, saklar, metni çıkarır ve aday + başvuru oluşturur.

    Geçersiz dosya yalnızca kendisi reddedilir; diğerleri işlenir (F4b). Ayrıştırma arka
    planda yapılır; dönen başvuruların pipeline'a verilmesi çağıranın işidir.
    """
    job = get_job(db, job_id)
    if job.status is JobStatus.CLOSED:
        raise ConflictError("Kapalı ilana CV yüklenemez")
    if not files:
        raise FieldValidationError("files", "En az 1 dosya seçin")
    if len(files) > MAX_FILES_PER_UPLOAD:
        raise FieldValidationError(
            "files", f"Tek seferde en fazla {MAX_FILES_PER_UPLOAD} dosya yüklenebilir"
        )

    hashes = {hashlib.sha256(file.data).hexdigest() for file in files}
    seen_hashes = _existing_hashes(db, job_id, hashes)
    results: list[FileResult] = []
    saved_names: list[str] = []
    accepted: list[tuple[Application, Candidate]] = []

    try:
        for file in files:
            filename = safe_filename(file.filename)
            if not file.data:
                results.append(FileResult(filename, status_code=422, detail=EMPTY_FILE))
                continue
            if len(file.data) > MAX_FILE_BYTES:
                results.append(FileResult(filename, status_code=422, detail=TOO_LARGE))
                continue
            kind = detect_kind(file.data)
            if kind is None:
                results.append(FileResult(filename, status_code=422, detail=UNSUPPORTED_TYPE))
                continue
            file_hash = hashlib.sha256(file.data).hexdigest()
            if file_hash in seen_hashes:
                results.append(FileResult(filename, status_code=409, detail=DUPLICATE_CV))
                continue
            seen_hashes.add(file_hash)

            parse_error: str | None = None
            try:
                cv_text = extract_text(file.data, kind)
            except ExtractionError:
                cv_text, parse_error = "", UNREADABLE
            if parse_error is None and len(cv_text) < MIN_TEXT_LENGTH:
                parse_error = NO_TEXT

            stored_name = storage.save(file.data, kind.value)
            saved_names.append(stored_name)
            failed = parse_error is not None
            candidate = Candidate(
                original_filename=filename,
                stored_path=stored_name,
                file_hash=file_hash,
                cv_text=cv_text,
                parse_status=ProcessingStatus.FAILED if failed else ProcessingStatus.PENDING,
                parse_error=parse_error,
            )
            db.add(candidate)
            db.flush()
            application = Application(
                job_id=job_id,
                candidate_id=candidate.id,
                score_status=ProcessingStatus.FAILED if failed else ProcessingStatus.PENDING,
                score_error=PARSE_FAILED if failed else None,
            )
            db.add(application)
            db.flush()
            accepted.append((application, candidate))
            results.append(FileResult(filename, application_id=application.id))

        for application, candidate in accepted:
            # Dosya adı kişisel veri sayılır (F12); audit'e yalnızca id ve durum yazılır.
            audit.record(
                db,
                actor_id=actor_id,
                action="cv.upload",
                entity_type="application",
                entity_id=application.id,
                payload={
                    "job_id": job_id,
                    "candidate_id": candidate.id,
                    "parse_status": candidate.parse_status.value,
                },
            )
        db.commit()
    except Exception:
        db.rollback()
        for name in saved_names:
            storage.delete(name)
        raise
    return results


def delete_candidate(
    db: Session, storage: FileStorage, *, candidate_id: int, actor_id: int
) -> None:
    """F11 (KVKK): aday kaydı, tüm başvuruları, notları ve CV dosyası kalıcı olarak silinir.

    Başvurular ve notlar veritabanında ON DELETE CASCADE ile silinir. Audit kaydına yalnızca
    "aday #id silindi" yazılır; ad, e-posta, dosya adı gibi kişisel veri yazılmaz.
    """
    candidate = db.get(Candidate, candidate_id)
    if candidate is None:
        raise NotFoundError("Aday bulunamadı")
    stored_path = candidate.stored_path
    db.delete(candidate)
    audit.record(
        db,
        actor_id=actor_id,
        action="candidate.delete",
        entity_type="candidate",
        entity_id=candidate_id,
    )
    db.commit()
    # Dosya, kayıt silindikten sonra silinir: DB işlemi başarısız olursa dosya kaybolmasın.
    storage.delete(stored_path)
