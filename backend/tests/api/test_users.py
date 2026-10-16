import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AuditLog, User
from tests.conftest import RECRUITER_PASSWORD

NEW_USER = {
    "email": "Yeni@Example.com",
    "full_name": "Zeynep Yeni",
    "password": "gecici-sifre-1",
    "role": "recruiter",
}


@pytest.mark.parametrize(
    ("method", "path"),
    [("get", "/api/users"), ("post", "/api/users"), ("patch", "/api/users/1")],
)
def test_users_endpoints_return_403_for_recruiter(
    recruiter_client: TestClient, method: str, path: str
) -> None:
    response = recruiter_client.request(method, path, json=NEW_USER)

    assert response.status_code == 403
    assert response.json() == {"detail": "Bu işlem için yetkiniz yok"}


def test_users_endpoints_return_401_without_session(client: TestClient) -> None:
    assert client.get("/api/users").status_code == 401


def test_admin_lists_users(admin_client: TestClient, admin: User, recruiter: User) -> None:
    response = admin_client.get("/api/users")

    assert response.status_code == 200
    assert [u["id"] for u in response.json()] == [admin.id, recruiter.id]
    assert all("password_hash" not in u for u in response.json())


@pytest.mark.real_bcrypt
def test_admin_creates_user_who_can_login(admin_client: TestClient, db: Session) -> None:
    response = admin_client.post("/api/users", json=NEW_USER)

    assert response.status_code == 201
    created = response.json()
    assert created["email"] == "yeni@example.com"
    assert created["role"] == "recruiter"
    assert created["is_active"] is True

    stored = db.get(User, created["id"])
    assert stored is not None
    assert stored.password_hash.startswith("$2b$12$")
    assert NEW_USER["password"] not in stored.password_hash

    audit_entry = db.scalars(select(AuditLog).where(AuditLog.action == "user.create")).all()[-1]
    assert audit_entry.payload == {"role": "recruiter"}


def test_create_user_rejects_short_password(admin_client: TestClient) -> None:
    response = admin_client.post("/api/users", json={**NEW_USER, "password": "kisa12345"})

    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["body", "password"]
    assert "en az 10 karakter" in response.json()["detail"][0]["msg"]


def test_create_user_rejects_invalid_email(admin_client: TestClient) -> None:
    response = admin_client.post("/api/users", json={**NEW_USER, "email": "gecersiz"})

    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["body", "email"]


def test_create_user_rejects_duplicate_email(admin_client: TestClient, recruiter: User) -> None:
    response = admin_client.post("/api/users", json={**NEW_USER, "email": recruiter.email.upper()})

    assert response.status_code == 409


def test_admin_changes_role(admin_client: TestClient, recruiter: User) -> None:
    response = admin_client.patch(f"/api/users/{recruiter.id}", json={"role": "admin"})

    assert response.status_code == 200
    assert response.json()["role"] == "admin"


def test_deactivated_user_cannot_login(
    admin_client: TestClient, recruiter: User, client: TestClient
) -> None:
    response = admin_client.patch(f"/api/users/{recruiter.id}", json={"is_active": False})
    assert response.status_code == 200
    assert response.json()["is_active"] is False

    client.cookies.clear()
    login = client.post(
        "/api/auth/login", json={"email": recruiter.email, "password": RECRUITER_PASSWORD}
    )

    assert login.status_code == 401
    assert login.json() == {"detail": "E-posta veya şifre hatalı"}


def test_deactivation_invalidates_existing_session(
    recruiter_client: TestClient, recruiter: User, db: Session
) -> None:
    recruiter.is_active = False
    db.commit()

    assert recruiter_client.get("/api/auth/me").status_code == 401


def test_admin_cannot_deactivate_self(admin_client: TestClient, admin: User) -> None:
    response = admin_client.patch(f"/api/users/{admin.id}", json={"is_active": False})

    assert response.status_code == 400
    assert response.json() == {"detail": "Kendi hesabınızı pasifleştiremezsiniz"}


def test_admin_resets_password(
    admin_client: TestClient, recruiter: User, client: TestClient
) -> None:
    response = admin_client.patch(
        f"/api/users/{recruiter.id}", json={"password": "yeni-sifre-9876"}
    )
    assert response.status_code == 200

    client.cookies.clear()
    old = client.post(
        "/api/auth/login", json={"email": recruiter.email, "password": RECRUITER_PASSWORD}
    )
    new = client.post(
        "/api/auth/login", json={"email": recruiter.email, "password": "yeni-sifre-9876"}
    )
    assert old.status_code == 401
    assert new.status_code == 200


def test_update_unknown_user_returns_404(admin_client: TestClient) -> None:
    response = admin_client.patch("/api/users/9999", json={"role": "admin"})

    assert response.status_code == 404
