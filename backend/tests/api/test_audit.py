from fastapi.testclient import TestClient

from app.models import User
from tests.conftest import ADMIN_PASSWORD, LoginFn


def test_admin_sees_only_account_events(
    recruiter_client: TestClient, admin: User, login: LoginFn
) -> None:
    recruiter_client.post(
        "/api/jobs", json={"title": "Backend Geliştirici", "required_skills": ["Python"]}
    )
    recruiter_client.post(
        "/api/auth/register",
        json={"full_name": "Can Aday", "email": "yeni@example.com", "password": "yeni-sifre-1234"},
    )
    admin_client = login(admin.email, ADMIN_PASSWORD)

    entries = admin_client.get("/api/audit").json()

    assert entries
    assert {e["entity_type"] for e in entries} == {"user"}
    actions = [e["action"] for e in entries]
    assert "job.create" not in actions
    assert "auth.login" in actions
