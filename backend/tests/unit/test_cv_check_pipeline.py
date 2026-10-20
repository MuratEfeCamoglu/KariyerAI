from typing import Any

from sqlalchemy.orm import Session, sessionmaker

from app.llm.base import LLMError
from app.models import CVCheck, ProcessingStatus, User
from app.services import pipeline

CV_TEXT = "Deniz Arslan\nSkills: Python, FastAPI\nLanguages: English (C1)\n" + "x" * 200


class _FailingLLM:
    model_name = "failing"

    def parse_cv(self, cv_text: str) -> dict[str, Any]:
        raise LLMError("bağlantı hatası")


def _check(db: Session, owner: User, **overrides: Any) -> CVCheck:
    check = CVCheck(
        owner_id=owner.id,
        title="Backend",
        required_skills=["Python"],
        original_filename="cv.pdf",
        stored_path="a" * 32 + ".pdf",
        file_hash="0" * 64,
        cv_text=CV_TEXT,
        **overrides,
    )
    db.add(check)
    db.commit()
    return check


def test_parse_failure_marks_score_failed(
    db: Session, session_factory: sessionmaker[Session], seeker: User
) -> None:
    check = _check(db, seeker)

    pipeline.process_cv_check(check.id, session_factory, llm_factory=_FailingLLM)  # type: ignore[arg-type]

    db.expire_all()
    stored = db.get(CVCheck, check.id)
    assert stored is not None
    assert stored.parse_status is ProcessingStatus.FAILED
    assert stored.parse_error == "Ayrıştırma servisine ulaşılamadı"
    assert stored.score_status is ProcessingStatus.FAILED
    assert stored.score_error == pipeline.PARSE_FAILED


def test_process_cv_check_scores_with_fake_llm(
    db: Session, session_factory: sessionmaker[Session], seeker: User
) -> None:
    check = _check(db, seeker)

    pipeline.process_cv_check(check.id, session_factory)

    db.expire_all()
    stored = db.get(CVCheck, check.id)
    assert stored is not None
    assert stored.score_status is ProcessingStatus.DONE
    assert stored.score is not None
    assert stored.prompt_version == "score_v1"


def test_unfinished_cv_checks_listed_for_requeue(
    db: Session, session_factory: sessionmaker[Session], seeker: User
) -> None:
    pending = _check(db, seeker)
    scoring = _check(
        db,
        seeker,
        parse_status=ProcessingStatus.DONE,
        parsed_data={"skills": []},
        score_status=ProcessingStatus.PROCESSING,
    )
    _check(
        db,
        seeker,
        parse_status=ProcessingStatus.DONE,
        parsed_data={"skills": []},
        score_status=ProcessingStatus.DONE,
    )

    assert pipeline.unfinished_cv_check_ids(session_factory) == [pending.id, scoring.id]
