from collections.abc import Iterator

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app import cli
from app.models import User, UserRole


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
