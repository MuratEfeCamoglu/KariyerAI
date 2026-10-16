from typing import Any

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.llm.base import LLMError
from app.llm.fake_client import FakeLLMClient
from app.models import (
    Application,
    AuditLog,
    Candidate,
    EducationLevel,
    Job,
    JobStatus,
    ProcessingStatus,
    User,
)
from app.services import pipeline

CV_TEXT = (
    "Deniz Arslan\n"
    "deniz.arslan@example.com | +90 555 000 11 22\n"
    "Skills: Python, FastAPI\n"
    "Languages: English (C1)\n"
)


def _application(
    db: Session, owner: User, parse_status: ProcessingStatus = ProcessingStatus.PENDING
) -> Application:
    job = Job(
        title="Backend",
        required_skills=["Python"],
        min_education=EducationLevel.NONE,
        status=JobStatus.OPEN,
        created_by=owner.id,
    )
    candidate = Candidate(
        original_filename="cv.pdf",
        stored_path="a" * 32 + ".pdf",
        file_hash="0" * 64,
        cv_text=CV_TEXT,
        parse_status=parse_status,
    )
    db.add_all([job, candidate])
    db.flush()
    application = Application(job_id=job.id, candidate_id=candidate.id)
    db.add(application)
    db.commit()
    return application


class _FailingLLM:
    model_name = "failing"

    def parse_cv(self, cv_text: str) -> dict[str, Any]:
        raise LLMError("bağlantı hatası")


class _InvalidLLM:
    model_name = "invalid"

    def parse_cv(self, cv_text: str) -> dict[str, Any]:
        return {"skills": "liste değil"}


def test_successful_parse_stores_parsed_cv_and_contact_fields(
    db: Session, session_factory: sessionmaker[Session], recruiter: User
) -> None:
    application = _application(db, recruiter)

    pipeline.process_application(application.id, session_factory, FakeLLMClient)

    db.expire_all()
    candidate = db.get(Candidate, application.candidate_id)
    assert candidate is not None
    assert candidate.parse_status is ProcessingStatus.DONE
    assert candidate.parsed_data is not None
    assert candidate.parsed_data["skills"] == ["Python", "FastAPI"]
    assert (candidate.full_name, candidate.email) == ("Deniz Arslan", "deniz.arslan@example.com")
    stored = db.get(Application, application.id)
    assert stored is not None
    # Puanlama Aşama 5'te eklenir; ayrıştırma bitince başvuru puan beklemeye devam eder.
    assert stored.score_status is ProcessingStatus.PENDING
    entry = db.scalars(select(AuditLog).where(AuditLog.action == "cv.parse")).one()
    assert entry.payload == {"status": "done", "model": "fake"}


@pytest.mark.parametrize(
    ("llm", "message"),
    [
        (_FailingLLM, "Ayrıştırma servisine ulaşılamadı"),
        (_InvalidLLM, "AI çıktısı beklenen biçimde değil"),
    ],
)
def test_parse_failure_marks_candidate_and_application_failed(
    db: Session,
    session_factory: sessionmaker[Session],
    recruiter: User,
    llm: Any,
    message: str,
    caplog: pytest.LogCaptureFixture,
) -> None:
    application = _application(db, recruiter)

    pipeline.process_application(application.id, session_factory, llm)

    db.expire_all()
    candidate = db.get(Candidate, application.candidate_id)
    stored = db.get(Application, application.id)
    assert candidate is not None and stored is not None
    assert candidate.parse_status is ProcessingStatus.FAILED
    assert candidate.parse_error == message
    assert stored.score_status is ProcessingStatus.FAILED
    assert stored.score_error == "Ayrıştırma başarısız"
    # Loglarda CV içeriği/kişisel veri yok.
    assert "Deniz" not in caplog.text and "example.com" not in caplog.text


def test_already_processed_candidate_is_not_parsed_again(
    db: Session, session_factory: sessionmaker[Session], recruiter: User
) -> None:
    application = _application(db, recruiter, parse_status=ProcessingStatus.DONE)

    pipeline.process_application(application.id, session_factory, _FailingLLM)

    db.expire_all()
    candidate = db.get(Candidate, application.candidate_id)
    assert candidate is not None
    assert candidate.parse_status is ProcessingStatus.DONE


def test_requeue_finds_pending_and_interrupted_work(
    db: Session, session_factory: sessionmaker[Session], recruiter: User
) -> None:
    pending = _application(db, recruiter, ProcessingStatus.PENDING)
    interrupted = _application(db, recruiter, ProcessingStatus.PROCESSING)
    _application(db, recruiter, ProcessingStatus.DONE)
    _application(db, recruiter, ProcessingStatus.FAILED)

    assert pipeline.requeue_unfinished(session_factory) == [pending.id, interrupted.id]

    db.expire_all()
    statuses = {
        db.get(Candidate, app.candidate_id).parse_status  # type: ignore[union-attr]
        for app in (pending, interrupted)
    }
    assert statuses == {ProcessingStatus.DONE}
