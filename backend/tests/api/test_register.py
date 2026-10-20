import httpx
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import AUTH_COOKIE_NAME
from app.models import AuditLog, User, UserRole

PASSWORD = "aday-sifresi-123"


def _register(client: TestClient, email: str = "yeni@example.com", **extra: str) -> httpx.Response:
    body = {"email": email, "full_name": "Deniz Aday", "password": PASSWORD, **extra}
    return client.post("/api/auth/register", json=body)


def test_register_creates_seeker_and_sets_cookie(client: TestClient) -> None:
    response = _register(client)

    assert response.status_code == 201
    assert response.json()["role"] == "seeker"
    assert AUTH_COOKIE_NAME in response.cookies
    assert client.get("/api/auth/me").json()["email"] == "yeni@example.com"


def test_register_recruiter_is_pending(client: TestClient, db: Session) -> None:
    response = _register(client, account_type="recruiter")

    assert response.status_code == 202
    assert response.json() == {"status": "pending_approval"}
    assert AUTH_COOKIE_NAME not in response.cookies
    user = db.scalar(select(User).where(User.email == "yeni@example.com"))
    assert user is not None
    assert user.role is UserRole.RECRUITER
    assert user.is_approved is False


def test_register_default_is_seeker(client: TestClient, db: Session) -> None:
    response = _register(client)

    assert response.status_code == 201
    user = db.scalar(select(User).where(User.email == "yeni@example.com"))
    assert user is not None
    assert user.role is UserRole.SEEKER
    assert user.is_approved is True


def test_register_ignores_role_field(client: TestClient, db: Session) -> None:
    response = _register(client, role="admin")

    assert response.status_code == 201
    user = db.scalar(select(User).where(User.email == "yeni@example.com"))
    assert user is not None and user.role is UserRole.SEEKER


def test_register_duplicate_email_409(client: TestClient) -> None:
    _register(client)
    response = _register(client, email="YENI@example.com")

    assert response.status_code == 409


def test_register_short_password_422(client: TestClient) -> None:
    response = client.post(
        "/api/auth/register",
        json={"email": "a@example.com", "full_name": "A", "password": "kisa"},
    )

    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["body", "password"]


def test_register_rate_limited_429(client: TestClient) -> None:
    for index in range(5):
        _register(client, email=f"aday{index}@example.com")

    response = _register(client, email="aday5@example.com")

    assert response.status_code == 429


def test_register_writes_audit_without_personal_data(client: TestClient, db: Session) -> None:
    _register(client)

    entry = db.scalar(select(AuditLog).where(AuditLog.action == "user.create"))
    assert entry is not None
    assert entry.payload == {"role": "seeker"}
