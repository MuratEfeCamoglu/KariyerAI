from collections.abc import Iterator

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app import cli
from app.models import AuditLog, Job, User, UserRole
from app.storage.files import FileStorage


@pytest.fixture(autouse=True)
def _use_test_db(monkeypatch: pytest.MonkeyPatch, session_factory: sessionmaker[Session]) -> None:
    monkeypatch.setattr(cli, "SessionLocal", session_factory)


def _fake_getpass(answers: list[str]) -> Iterator[str]:
    return iter(answers)


@pytest.mark.real_bcrypt
def test_create_admin_prompts_hidden_password_and_creates_admin(
    monkeypatch: pytest.MonkeyPatch, db: Session, capsys: pytest.CaptureFixture[str]
) -> None:
    answers = _fake_getpass(["kisa", "guclu-sifre-123", "guclu-sifre-123"])
    monkeypatch.setattr(cli.getpass, "getpass", lambda _prompt: next(answers))

    exit_code = cli.main(["create-admin", "--email", "admin@example.com"])

    assert exit_code == 0
    user = db.scalars(select(User)).one()
    assert user.email == "admin@example.com"
    assert user.role == UserRole.ADMIN
    assert user.password_hash.startswith("$2b$12$")
    output = capsys.readouterr()
    assert "en az 10 karakter" in output.err
    assert "guclu-sifre-123" not in output.out + output.err


def test_create_admin_retries_when_confirmation_differs(
    monkeypatch: pytest.MonkeyPatch, db: Session
) -> None:
    answers = _fake_getpass(
        ["guclu-sifre-123", "farkli-sifre-1", "guclu-sifre-123", "guclu-sifre-123"]
    )
    monkeypatch.setattr(cli.getpass, "getpass", lambda _prompt: next(answers))

    assert cli.main(["create-admin", "--email", "admin@example.com"]) == 0
    assert db.scalars(select(User)).one().role == UserRole.ADMIN


def test_create_admin_fails_for_existing_email(
    monkeypatch: pytest.MonkeyPatch, admin: User
) -> None:
    answers = _fake_getpass(["guclu-sifre-123", "guclu-sifre-123"])
    monkeypatch.setattr(cli.getpass, "getpass", lambda _prompt: next(answers))

    assert cli.main(["create-admin", "--email", admin.email]) == 1


def _make_job(db: Session, owner: User, title: str) -> Job:
    job = Job(title=title, required_skills=["Python"], created_by=owner.id)
    db.add(job)
    db.commit()
    return job


def test_transfer_jobs(db: Session, admin: User, recruiter: User) -> None:
    first = _make_job(db, admin, "İlan bir")
    second = _make_job(db, admin, "İlan iki")

    assert cli.main(["transfer-jobs", "--from", admin.email, "--to", recruiter.email]) == 0

    db.expire_all()
    for job in (first, second):
        reloaded = db.get(Job, job.id)
        assert reloaded is not None
        assert reloaded.created_by == recruiter.id
    logs = db.scalars(select(AuditLog).where(AuditLog.action == "job.transfer")).all()
    assert len(logs) == 2
    assert all(
        log.payload == {"from_user_id": admin.id, "to_user_id": recruiter.id}
        and log.actor_id is None
        for log in logs
    )


def test_transfer_jobs_lowercases_emails(db: Session, admin: User, recruiter: User) -> None:
    _make_job(db, admin, "İlan")

    args = ["transfer-jobs", "--from", admin.email.upper(), "--to", recruiter.email.upper()]
    assert cli.main(args) == 0


@pytest.mark.parametrize("target", ["admin", "seeker", "pending", "missing"])
def test_transfer_jobs_rejects_non_recruiter_target(
    target: str,
    db: Session,
    admin: User,
    recruiter: User,
    seeker: User,
    pending_recruiter: User,
    capsys: pytest.CaptureFixture[str],
) -> None:
    job = _make_job(db, recruiter, "İlan")
    emails = {
        "admin": admin.email,
        "seeker": seeker.email,
        "pending": pending_recruiter.email,
        "missing": "yok@example.com",
    }

    assert cli.main(["transfer-jobs", "--from", recruiter.email, "--to", emails[target]]) == 1

    assert capsys.readouterr().err
    db.expire_all()
    reloaded = db.get(Job, job.id)
    assert reloaded is not None
    assert reloaded.created_by == recruiter.id


def test_transfer_jobs_rejects_unknown_source(
    recruiter: User, capsys: pytest.CaptureFixture[str]
) -> None:
    assert cli.main(["transfer-jobs", "--from", "yok@example.com", "--to", recruiter.email]) == 1
    assert capsys.readouterr().err


def test_seed_demo_uses_owner(
    monkeypatch: pytest.MonkeyPatch,
    db: Session,
    storage: FileStorage,
    recruiter: User,
    other_recruiter: User,
) -> None:
    monkeypatch.setattr(cli, "get_storage", lambda: storage)

    assert cli.main(["seed-demo", "--applications", "2", "--owner", other_recruiter.email]) == 0

    assert db.scalars(select(Job)).one().created_by == other_recruiter.id


def test_seed_demo_defaults_to_first_recruiter(
    monkeypatch: pytest.MonkeyPatch,
    db: Session,
    storage: FileStorage,
    admin: User,
    pending_recruiter: User,
    recruiter: User,
    other_recruiter: User,
) -> None:
    monkeypatch.setattr(cli, "get_storage", lambda: storage)

    assert cli.main(["seed-demo", "--applications", "2"]) == 0

    assert db.scalars(select(Job)).one().created_by == recruiter.id


def test_seed_demo_without_recruiter_fails(
    admin: User, pending_recruiter: User, capsys: pytest.CaptureFixture[str]
) -> None:
    assert cli.main(["seed-demo", "--applications", "2"]) == 1
    assert "Önce bir İK hesabı oluşturun" in capsys.readouterr().err


def test_seed_demo_rejects_non_recruiter_owner(
    admin: User, recruiter: User, capsys: pytest.CaptureFixture[str]
) -> None:
    assert cli.main(["seed-demo", "--owner", admin.email]) == 1
    assert capsys.readouterr().err
