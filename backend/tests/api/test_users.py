import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AuditLog, User
from tests.conftest import RECRUITER_PASSWORD, LoginFn

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


# --- Onay akışı ---


def test_list_users_includes_is_approved(
    admin_client: TestClient, recruiter: User, pending_recruiter: User
) -> None:
    by_id = {u["id"]: u for u in admin_client.get("/api/users").json()}

    assert by_id[recruiter.id]["is_approved"] is True
    assert by_id[pending_recruiter.id]["is_approved"] is False


def test_approve_pending_user(
    admin_client: TestClient, pending_recruiter: User, db: Session, login: LoginFn
) -> None:
    response = admin_client.post(f"/api/users/{pending_recruiter.id}/approve")

    assert response.status_code == 200
    assert response.json()["is_approved"] is True
    entry = db.scalars(select(AuditLog).where(AuditLog.action == "user.approve")).one()
    assert entry.entity_id == pending_recruiter.id
    assert entry.payload == {}
    assert login(pending_recruiter.email, RECRUITER_PASSWORD) is not None


def test_approve_already_approved_409(admin_client: TestClient, recruiter: User) -> None:
    response = admin_client.post(f"/api/users/{recruiter.id}/approve")

    assert response.status_code == 409
    assert response.json() == {"detail": "Hesap zaten onaylı"}


def test_reject_pending_user(
    admin_client: TestClient, pending_recruiter: User, db: Session
) -> None:
    user_id = pending_recruiter.id
    email = pending_recruiter.email

    response = admin_client.post(f"/api/users/{user_id}/reject")

    assert response.status_code == 204
    db.expire_all()
    assert db.get(User, user_id) is None
    entry = db.scalars(select(AuditLog).where(AuditLog.action == "user.reject")).one()
    assert entry.entity_id == user_id
    assert entry.payload == {}
    again = admin_client.post(
        "/api/auth/register",
        json={
            "email": email,
            "full_name": "Deniz Bekler",
            "password": "bekleyen-sifre-123",
            "account_type": "recruiter",
        },
    )
    assert again.status_code == 202


def test_reject_approved_user_409(admin_client: TestClient, recruiter: User) -> None:
    response = admin_client.post(f"/api/users/{recruiter.id}/reject")

    assert response.status_code == 409
    assert response.json() == {"detail": "Yalnızca onay bekleyen hesaplar reddedilebilir"}


@pytest.mark.parametrize("action", ["approve", "reject"])
def test_approve_reject_require_admin(
    recruiter_client: TestClient, pending_recruiter: User, action: str
) -> None:
    response = recruiter_client.post(f"/api/users/{pending_recruiter.id}/{action}")

    assert response.status_code == 403


@pytest.mark.parametrize("action", ["approve", "reject"])
def test_approve_reject_unknown_user_404(admin_client: TestClient, action: str) -> None:
    response = admin_client.post(f"/api/users/9999/{action}")

    assert response.status_code == 404
    assert response.json() == {"detail": "Kullanıcı bulunamadı"}


# --- Son aktif yöneticinin korunması ---


def test_last_admin_cannot_demote_self(admin_client: TestClient, admin: User) -> None:
    response = admin_client.patch(f"/api/users/{admin.id}", json={"role": "recruiter"})

    assert response.status_code == 409
    assert response.json() == {"detail": "Sistemde en az bir aktif yönetici kalmalı"}


def test_admin_can_be_demoted_when_another_active_admin_exists(
    admin_client: TestClient, admin: User, recruiter: User
) -> None:
    admin_client.patch(f"/api/users/{recruiter.id}", json={"role": "admin"})

    response = admin_client.patch(f"/api/users/{admin.id}", json={"role": "recruiter"})

    assert response.status_code == 200
    assert response.json()["role"] == "recruiter"


def test_inactive_admins_do_not_count_as_remaining_admins(
    admin_client: TestClient, admin: User, recruiter: User
) -> None:
    # İkinci admin pasif olduğu sürece son aktif admin yine korunur.
    admin_client.patch(f"/api/users/{recruiter.id}", json={"role": "admin"})
    admin_client.patch(f"/api/users/{recruiter.id}", json={"is_active": False})

    response = admin_client.patch(f"/api/users/{admin.id}", json={"role": "recruiter"})

    assert response.status_code == 409


def test_other_admin_cannot_deactivate_last_active_admin(
    admin_client: TestClient, admin: User, recruiter: User, login: LoginFn, db: Session
) -> None:
    admin_client.patch(f"/api/users/{recruiter.id}", json={"role": "admin"})
    second = login(recruiter.email, RECRUITER_PASSWORD)
    # İlk admin pasifleştirilince ikinci admin son aktif admin olur.
    assert second.patch(f"/api/users/{admin.id}", json={"is_active": False}).status_code == 200

    db.expire_all()
    assert second.patch(f"/api/users/{recruiter.id}", json={"role": "recruiter"}).status_code == 409
