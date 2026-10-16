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
from app.models import Application, Candidate, Job, ProcessingStatus
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
