import random
from datetime import date

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from app import cli
from app.models import Application, Candidate, Job, ProcessingStatus, User
from app.services import demo
from app.services.cv_extract import FileKind, extract_text
from app.storage.files import FileStorage

TODAY = date(2026, 10, 16)


def test_synthetic_cv_is_consistent_and_contains_no_protected_attributes() -> None:
    cv = demo.synthetic_cv(random.Random(1), 7, TODAY)

    assert cv.parsed.email == "aday0007@example.com"
    assert all(skill in cv.text for skill in cv.parsed.skills)
    assert cv.parsed.total_experience_years > 0
    dumped = cv.parsed.model_dump()
    for key in ("age", "gender", "marital_status", "religion", "nationality", "photo"):
        assert key not in dumped


def test_seed_is_deterministic() -> None:
    first = demo.synthetic_cv(random.Random(42), 1, TODAY)
    second = demo.synthetic_cv(random.Random(42), 1, TODAY)

    assert first == second


def test_seed_demo_creates_scored_applications_with_files(
    db: Session, admin: User, storage: FileStorage
) -> None:
    result = demo.seed_demo(db, storage, owner_id=admin.id, applications=12, today=TODAY)

    job = db.get(Job, result.job_id)
    assert job is not None and job.created_by == admin.id
    applications = db.scalars(select(Application).where(Application.job_id == job.id)).all()
    assert len(applications) == 12
    assert all(a.score is not None and 0 <= a.score <= 100 for a in applications)
    assert all(a.score_status is ProcessingStatus.DONE for a in applications)
    assert len({a.score for a in applications}) > 1, "puanlar çeşitli olmalı"
    assert {a.llm_model for a in applications} == {"fake"}

    candidate = db.get(Candidate, applications[0].candidate_id)
    assert candidate is not None
    stored = storage.path_for(candidate.stored_path).read_bytes()
    # Saklanan dosya gerçek bir DOCX ve CV metnini içeriyor.
    assert candidate.full_name is not None
    assert candidate.full_name in extract_text(stored, FileKind.DOCX)


def test_cli_seed_demo_requires_recruiter(
    monkeypatch: pytest.MonkeyPatch,
    session_factory: sessionmaker[Session],
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(cli, "SessionLocal", session_factory)

    assert cli.main(["seed-demo"]) == 1
    assert "Önce bir İK hesabı oluşturun" in capsys.readouterr().err


def test_cli_seed_demo_with_applications_option(
    monkeypatch: pytest.MonkeyPatch,
    session_factory: sessionmaker[Session],
    storage: FileStorage,
    recruiter: User,
    db: Session,
) -> None:
    monkeypatch.setattr(cli, "SessionLocal", session_factory)
    monkeypatch.setattr(cli, "get_storage", lambda: storage)

    assert cli.main(["seed-demo", "--applications", "25"]) == 0
    assert db.scalar(select(func.count(Application.id))) == 25


def test_seeded_status_changes_appear_in_history(
    db: Session, admin: User, storage: FileStorage
) -> None:
    from app.models import ApplicationStatus
    from app.services.applications import get_detail

    result = demo.seed_demo(db, storage, owner_id=admin.id, applications=15, today=TODAY)

    changed = [
        a
        for a in db.scalars(select(Application).where(Application.job_id == result.job_id))
        if a.status is not ApplicationStatus.NEW
    ]
    assert changed, "tohum en az bir durum değişikliği üretmeli"
    for application in changed:
        [change] = get_detail(db, application.id, owner_id=admin.id).status_history
        assert (change.from_status, change.to_status) == (ApplicationStatus.NEW, application.status)
        assert change.actor_id == admin.id
