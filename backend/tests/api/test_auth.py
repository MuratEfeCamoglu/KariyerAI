import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import AUTH_COOKIE_NAME
from app.models import AuditLog, User
from tests.conftest import ADMIN_PASSWORD, RECRUITER_PASSWORD


def test_login_sets_httponly_lax_cookie_valid_for_8_hours(client: TestClient, admin: User) -> None:
    response = client.post(
        "/api/auth/login", json={"email": admin.email, "password": ADMIN_PASSWORD}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["email"] == admin.email
    assert body["role"] == "admin"
    assert "password" not in response.text and "password_hash" not in body
    set_cookie = response.headers["set-cookie"].lower()
    assert set_cookie.startswith(f"{AUTH_COOKIE_NAME}=")
    assert "httponly" in set_cookie
    assert "samesite=lax" in set_cookie
    assert "max-age=28800" in set_cookie


def test_login_email_is_case_insensitive(client: TestClient, admin: User) -> None:
    response = client.post(
        "/api/auth/login", json={"email": "ADMIN@Example.com", "password": ADMIN_PASSWORD}
    )

    assert response.status_code == 200


def test_wrong_password_returns_401_with_generic_message(client: TestClient, admin: User) -> None:
    response = client.post(
        "/api/auth/login", json={"email": admin.email, "password": "yanlis-sifre-123"}
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "E-posta veya şifre hatalı"}
    assert AUTH_COOKIE_NAME not in response.cookies


def test_unknown_email_returns_same_generic_message(client: TestClient) -> None:
    response = client.post(
        "/api/auth/login", json={"email": "yok@example.com", "password": "herhangi-sifre"}
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "E-posta veya şifre hatalı"}


def test_more_than_10_failed_logins_per_minute_returns_429(client: TestClient, admin: User) -> None:
    for _ in range(10):
        response = client.post(
            "/api/auth/login", json={"email": admin.email, "password": "yanlis-sifre-123"}
        )
        assert response.status_code == 401

    blocked = client.post(
        "/api/auth/login", json={"email": admin.email, "password": ADMIN_PASSWORD}
    )

    assert blocked.status_code == 429
    assert "detail" in blocked.json()


def test_pending_login_correct_password_403(client: TestClient, pending_recruiter: User) -> None:
    response = client.post(
        "/api/auth/login", json={"email": pending_recruiter.email, "password": RECRUITER_PASSWORD}
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "Hesabınız yönetici onayı bekliyor"}
    assert AUTH_COOKIE_NAME not in response.cookies


def test_pending_login_wrong_password_401(client: TestClient, pending_recruiter: User) -> None:
    response = client.post(
        "/api/auth/login", json={"email": pending_recruiter.email, "password": "yanlis-sifre-123"}
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "E-posta veya şifre hatalı"}


def test_pending_login_does_not_count_as_failure(
    client: TestClient, pending_recruiter: User
) -> None:
    for _ in range(12):
        response = client.post(
            "/api/auth/login",
            json={"email": pending_recruiter.email, "password": RECRUITER_PASSWORD},
        )
        assert response.status_code == 403


def test_unapproved_token_rejected(
    recruiter_client: TestClient, recruiter: User, db: Session
) -> None:
    recruiter.is_approved = False
    db.commit()

    assert recruiter_client.get("/api/auth/me").status_code == 401


def test_me_requires_session(client: TestClient) -> None:
    response = client.get("/api/auth/me")

    assert response.status_code == 401
    assert response.json() == {"detail": "Oturum açmanız gerekiyor"}


def test_me_returns_current_user(recruiter_client: TestClient, recruiter: User) -> None:
    response = recruiter_client.get("/api/auth/me")

    assert response.status_code == 200
    assert response.json()["id"] == recruiter.id
    assert response.json()["role"] == "recruiter"


def test_invalid_token_cookie_returns_401(client: TestClient) -> None:
    client.cookies.set(AUTH_COOKIE_NAME, "bozuk.token.degeri")

    response = client.get("/api/auth/me")

    assert response.status_code == 401


def test_logout_clears_cookie(recruiter_client: TestClient) -> None:
    response = recruiter_client.post("/api/auth/logout")

    assert response.status_code == 204
    assert recruiter_client.get("/api/auth/me").status_code == 401


def test_logout_requires_session(client: TestClient) -> None:
    assert client.post("/api/auth/logout").status_code == 401


def test_successful_login_is_audited_without_personal_data(
    client: TestClient, recruiter: User, db: Session
) -> None:
    client.post("/api/auth/login", json={"email": recruiter.email, "password": RECRUITER_PASSWORD})

    entry = db.scalars(select(AuditLog).where(AuditLog.action == "auth.login")).one()
    assert entry.actor_id == recruiter.id
    assert entry.entity_type == "user"
    assert entry.entity_id == recruiter.id
    assert recruiter.email not in str(entry.payload)
    assert recruiter.full_name not in str(entry.payload)


def test_cookie_is_secure_when_configured(
    client: TestClient, admin: User, monkeypatch: pytest.MonkeyPatch
) -> None:
    from app.api import auth as auth_api
    from app.core.config import Settings

    secure_settings = Settings.model_validate({"jwt_secret": "y" * 48, "cookie_secure": True})
    monkeypatch.setattr(auth_api, "get_settings", lambda: secure_settings)

    response = client.post(
        "/api/auth/login", json={"email": admin.email, "password": ADMIN_PASSWORD}
    )

    assert "secure" in response.headers["set-cookie"].lower()
