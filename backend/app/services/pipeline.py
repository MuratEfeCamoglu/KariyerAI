"""Arka plan iş akışı: ayrıştırma → puanlama. ISKELET.md §3.1.

FastAPI BackgroundTasks bu fonksiyonları istek bittikten sonra thread havuzunda çalıştırır;
bu yüzden her adım kendi kısa ömürlü DB oturumunu açar ve LLM çağrısı sırasında oturum tutmaz.
"""

import logging
import threading
from collections.abc import Callable

from pydantic import ValidationError
from sqlalchemy import or_, select
from sqlalchemy.orm import Session, sessionmaker

from app.llm.base import (
    PARSE_PROMPT_VERSION,
    LLMClient,
    LLMError,
    LLMOutputError,
    LLMRefusalError,
)
from app.llm.factory import get_llm_client
from app.models import Application, Candidate, CVCheck, Job, ProcessingStatus
from app.schemas.parsed_cv import ParsedCV
from app.services import audit, cv_parser, scoring

logger = logging.getLogger(__name__)

SessionFactory = sessionmaker[Session]
LLMFactory = Callable[[], LLMClient]

# Sağlayıcı hız sınırını aşmamak için aynı anda en fazla 5 LLM çağrısı (§3.1).
_llm_slots = threading.Semaphore(5)

_ACTIVE = (ProcessingStatus.PENDING, ProcessingStatus.PROCESSING)

PARSE_FAILED = "Ayrıştırma başarısız"
# Sıra önemli: alt sınıflar (LLMOutputError, LLMRefusalError) genel LLMError'dan önce gelir.
_PARSE_ERROR_MESSAGES: dict[type[Exception], str] = {
    LLMRefusalError: "AI bu CV'yi işlemedi",
    LLMOutputError: "AI çıktısı beklenen biçimde değil",
    ValidationError: "AI çıktısı beklenen biçimde değil",
    LLMError: "Ayrıştırma servisine ulaşılamadı",
}
_SCORE_ERROR_MESSAGES: dict[type[Exception], str] = {
    LLMRefusalError: "AI bu CV'yi değerlendirmedi",
    LLMOutputError: "AI çıktısı beklenen biçimde değil",
    ValidationError: "AI çıktısı beklenen biçimde değil",
    LLMError: "Puanlama servisine ulaşılamadı",
}


def _message_for(exc: Exception, messages: dict[type[Exception], str]) -> str:
    return next(msg for kind, msg in messages.items() if isinstance(exc, kind))


def _clip(value: str | None, max_length: int) -> str | None:
    # LLM çıktısı güvenilmez veridir; kolon uzunluğunu aşmasın.
    return value[:max_length] if value else None


def _parse_candidate(
    candidate_id: int, session_factory: SessionFactory, llm_factory: LLMFactory
) -> None:
    with session_factory() as db:
        candidate = db.get(Candidate, candidate_id)
        if candidate is None or candidate.parse_status not in _ACTIVE:
            return
        candidate.parse_status = ProcessingStatus.PROCESSING
        db.commit()
        cv_text = candidate.cv_text

    parsed: ParsedCV | None = None
    error: str | None = None
    model_name: str | None = None
    try:
        llm = llm_factory()
        with _llm_slots:
            try:
                parsed = cv_parser.parse_cv(cv_text, llm)
            finally:
                # Çağrıdan sonra okunur: yedekli istemcide hizmet eden sağlayıcı o an belli olur.
                model_name = llm.model_name
    except (LLMError, ValidationError) as exc:
        error = _message_for(exc, _PARSE_ERROR_MESSAGES)
        # Yalnızca id ve hata türü loglanır; istisna mesajı CV içeriği taşıyabilir.
        logger.warning(
            "Ayrıştırma başarısız: candidate_id=%s (%s)", candidate_id, type(exc).__name__
        )

    with session_factory() as db:
        candidate = db.get(Candidate, candidate_id)
        if candidate is None:  # Bu arada silinmiş olabilir (F11).
            return
        if parsed is not None:
            candidate.parsed_data = parsed.model_dump(mode="json")
            candidate.full_name = _clip(parsed.full_name, 200)
            candidate.email = _clip(parsed.email, 254)
            candidate.phone = _clip(parsed.phone, 50)
            candidate.parse_status = ProcessingStatus.DONE
            candidate.parse_error = None
        else:
            candidate.parse_status = ProcessingStatus.FAILED
            candidate.parse_error = error
            for application in db.scalars(
                select(Application).where(Application.candidate_id == candidate_id)
            ):
                application.score_status = ProcessingStatus.FAILED
                application.score_error = PARSE_FAILED
        payload: dict[str, str] = {
            "status": candidate.parse_status.value,
            "prompt": PARSE_PROMPT_VERSION,
        }
        if model_name is not None:
            payload["model"] = model_name
        audit.record(
            db,
            actor_id=None,
            action="cv.parse",
            entity_type="candidate",
            entity_id=candidate_id,
            payload=payload,
        )
        db.commit()


def _score_application(
    application_id: int, session_factory: SessionFactory, llm_factory: LLMFactory
) -> None:
    with session_factory() as db:
        application = db.get(Application, application_id)
        if application is None or application.score_status not in _ACTIVE:
            return
        candidate = db.get(Candidate, application.candidate_id)
        job = db.get(Job, application.job_id)
        if candidate is None or job is None or candidate.parse_status is not ProcessingStatus.DONE:
            return
        parsed = ParsedCV.model_validate(candidate.parsed_data or {})
        cv_text = candidate.cv_text
        application.score_status = ProcessingStatus.PROCESSING
        db.commit()
        db.expunge(job)  # Oturum kapandıktan sonra kriterler okunabilsin.

    evaluation: scoring.ScoreEvaluation | None = None
    error: str | None = None
    try:
        llm = llm_factory()
        with _llm_slots:
            evaluation = scoring.evaluate(job, parsed, cv_text, llm)
    except (LLMError, ValidationError) as exc:
        error = _message_for(exc, _SCORE_ERROR_MESSAGES)
        logger.warning(
            "Puanlama başarısız: application_id=%s (%s)", application_id, type(exc).__name__
        )

    with session_factory() as db:
        application = db.get(Application, application_id)
        # Puanlama sürerken ilan kriterleri değiştiyse kayıt yeniden "pending" yapılmıştır (F6f);
        # eski kriterlerle hesaplanan sonuç yazılmaz, yeni puanlama işi bunu ele alır.
        if application is None or application.score_status is not ProcessingStatus.PROCESSING:
            return
        payload: dict[str, str | int]
        if evaluation is not None:
            application.score = evaluation.score
            application.score_breakdown = evaluation.breakdown.model_dump(mode="json")
            application.ai_summary = evaluation.summary
            application.llm_model = evaluation.model
            application.prompt_version = evaluation.prompt_version
            application.score_status = ProcessingStatus.DONE
            application.score_error = None
            payload = {
                "status": "done",
                "score": evaluation.score,
                "model": evaluation.model,
                "prompt": evaluation.prompt_version,
            }
        else:
            application.score_status = ProcessingStatus.FAILED
            application.score_error = error
            payload = {"status": "failed"}
        audit.record(
            db,
            actor_id=None,
            action="score.result",
            entity_type="application",
            entity_id=application_id,
            payload=payload,
        )
        db.commit()


def process_application(
    application_id: int,
    session_factory: SessionFactory,
    llm_factory: LLMFactory = get_llm_client,
) -> None:
    """Başvuruyu işlenebildiği yere kadar ilerletir; tekrar çağrılması güvenlidir."""
    try:
        with session_factory() as db:
            application = db.get(Application, application_id)
            if application is None:
                return
            candidate_id = application.candidate_id
        _parse_candidate(candidate_id, session_factory, llm_factory)
        _score_application(application_id, session_factory, llm_factory)
    except Exception:
        # Arka plan işi sessizce ölmesin; kayıt pending/processing kalır, açılışta yeniden denenir.
        logger.exception("Pipeline hatası: application_id=%s", application_id)


def unfinished_application_ids(session_factory: SessionFactory) -> list[int]:
    """Süreç yeniden başladığında yarıda kalmış işler (R7): ayrıştırma ya da puanlama."""
    with session_factory() as db:
        return list(
            db.scalars(
                select(Application.id)
                .join(Candidate, Candidate.id == Application.candidate_id)
                .where(
                    or_(
                        Candidate.parse_status.in_(_ACTIVE),
                        (Candidate.parse_status == ProcessingStatus.DONE)
                        & Application.score_status.in_(_ACTIVE),
                    )
                )
                .order_by(Application.id)
            )
        )


def requeue_unfinished(session_factory: SessionFactory) -> list[int]:
    ids = unfinished_application_ids(session_factory)
    if ids:
        # Yarıda kalan "processing" kayıtlar bu süreçte artık işlenmiyor; yeniden başlatılır.
        with session_factory() as db:
            for application in db.scalars(select(Application).where(Application.id.in_(ids))):
                if application.score_status is ProcessingStatus.PROCESSING:
                    application.score_status = ProcessingStatus.PENDING
            db.commit()
        logger.info("Yeniden kuyruğa alınan başvuru sayısı: %s", len(ids))
    for application_id in ids:
        process_application(application_id, session_factory)
    return ids


# --- İş arayan değerlendirmeleri (CVCheck): aynı adımlar, ayrı tablo. ---


def _parse_cv_check(
    check_id: int, session_factory: SessionFactory, llm_factory: LLMFactory
) -> None:
    with session_factory() as db:
        check = db.get(CVCheck, check_id)
        if check is None or check.parse_status not in _ACTIVE:
            return
        check.parse_status = ProcessingStatus.PROCESSING
        db.commit()
        cv_text = check.cv_text

    parsed: ParsedCV | None = None
    error: str | None = None
    model_name: str | None = None
    try:
        llm = llm_factory()
        with _llm_slots:
            try:
                parsed = cv_parser.parse_cv(cv_text, llm)
            finally:
                model_name = llm.model_name
    except (LLMError, ValidationError) as exc:
        error = _message_for(exc, _PARSE_ERROR_MESSAGES)
        logger.warning("Ayrıştırma başarısız: cv_check_id=%s (%s)", check_id, type(exc).__name__)

    with session_factory() as db:
        check = db.get(CVCheck, check_id)
        if check is None:  # Bu arada sahibi silmiş olabilir.
            return
        if parsed is not None:
            check.parsed_data = parsed.model_dump(mode="json")
            check.parse_status = ProcessingStatus.DONE
            check.parse_error = None
        else:
            check.parse_status = ProcessingStatus.FAILED
            check.parse_error = error
            check.score_status = ProcessingStatus.FAILED
            check.score_error = PARSE_FAILED
        payload: dict[str, str] = {
            "status": check.parse_status.value,
            "prompt": PARSE_PROMPT_VERSION,
        }
        if model_name is not None:
            payload["model"] = model_name
        audit.record(
            db,
            actor_id=None,
            action="cv_check.parse",
            entity_type="cv_check",
            entity_id=check_id,
            payload=payload,
        )
        db.commit()


def _score_cv_check(
    check_id: int, session_factory: SessionFactory, llm_factory: LLMFactory
) -> None:
    with session_factory() as db:
        check = db.get(CVCheck, check_id)
        if (
            check is None
            or check.score_status not in _ACTIVE
            or check.parse_status is not ProcessingStatus.DONE
        ):
            return
        parsed = ParsedCV.model_validate(check.parsed_data or {})
        cv_text = check.cv_text
        job = check.criteria_job()
        check.score_status = ProcessingStatus.PROCESSING
        db.commit()

    evaluation: scoring.ScoreEvaluation | None = None
    error: str | None = None
    try:
        llm = llm_factory()
        with _llm_slots:
            evaluation = scoring.evaluate(job, parsed, cv_text, llm)
    except (LLMError, ValidationError) as exc:
        error = _message_for(exc, _SCORE_ERROR_MESSAGES)
        logger.warning("Puanlama başarısız: cv_check_id=%s (%s)", check_id, type(exc).__name__)

    with session_factory() as db:
        check = db.get(CVCheck, check_id)
        if check is None or check.score_status is not ProcessingStatus.PROCESSING:
            return
        payload: dict[str, str | int]
        if evaluation is not None:
            check.score = evaluation.score
            check.score_breakdown = evaluation.breakdown.model_dump(mode="json")
            check.ai_summary = evaluation.summary
            check.llm_model = evaluation.model
            check.prompt_version = evaluation.prompt_version
            check.score_status = ProcessingStatus.DONE
            check.score_error = None
            payload = {
                "status": "done",
                "score": evaluation.score,
                "model": evaluation.model,
                "prompt": evaluation.prompt_version,
            }
        else:
            check.score_status = ProcessingStatus.FAILED
            check.score_error = error
            payload = {"status": "failed"}
        audit.record(
            db,
            actor_id=None,
            action="cv_check.score",
            entity_type="cv_check",
            entity_id=check_id,
            payload=payload,
        )
        db.commit()


def process_cv_check(
    check_id: int,
    session_factory: SessionFactory,
    llm_factory: LLMFactory = get_llm_client,
) -> None:
    """Değerlendirmeyi işlenebildiği yere kadar ilerletir; tekrar çağrılması güvenlidir."""
    try:
        _parse_cv_check(check_id, session_factory, llm_factory)
        _score_cv_check(check_id, session_factory, llm_factory)
    except Exception:
        logger.exception("Pipeline hatası: cv_check_id=%s", check_id)


def unfinished_cv_check_ids(session_factory: SessionFactory) -> list[int]:
    with session_factory() as db:
        return list(
            db.scalars(
                select(CVCheck.id)
                .where(
                    or_(
                        CVCheck.parse_status.in_(_ACTIVE),
                        (CVCheck.parse_status == ProcessingStatus.DONE)
                        & CVCheck.score_status.in_(_ACTIVE),
                    )
                )
                .order_by(CVCheck.id)
            )
        )


def requeue_unfinished_cv_checks(session_factory: SessionFactory) -> list[int]:
    ids = unfinished_cv_check_ids(session_factory)
    if ids:
        with session_factory() as db:
            for check in db.scalars(select(CVCheck).where(CVCheck.id.in_(ids))):
                if check.parse_status is ProcessingStatus.PROCESSING:
                    check.parse_status = ProcessingStatus.PENDING
                if check.score_status is ProcessingStatus.PROCESSING:
                    check.score_status = ProcessingStatus.PENDING
            db.commit()
        logger.info("Yeniden kuyruğa alınan değerlendirme sayısı: %s", len(ids))
    for check_id in ids:
        process_cv_check(check_id, session_factory)
    return ids
