from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AuditLog, User

VALID_JOB: dict[str, Any] = {
    "title": "Kıdemli Backend Geliştirici",
    "department": "Teknoloji",
    "description": "Ödeme altyapısı ekibi için.",
    "required_skills": ["Python", "FastAPI", "SQL"],
    "preferred_skills": ["Docker"],
    "min_experience_years": 3,
    "min_education": "bachelor",
    "languages": [{"language": "İngilizce", "level": "B2"}],
    "status": "open",
}


def _create(client: TestClient, **overrides: Any) -> dict[str, Any]:
    response = client.post("/api/jobs", json={**VALID_JOB, **overrides})
    assert response.status_code == 201, response.text
    body: dict[str, Any] = response.json()
    return body


def _field_error(response: Any) -> tuple[list[Any], str]:
    assert response.status_code == 422, response.text
    first = response.json()["detail"][0]
    return first["loc"], first["msg"]


# --- Yetki ---


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("get", "/api/jobs"),
        ("post", "/api/jobs"),
        ("get", "/api/jobs/1"),
        ("patch", "/api/jobs/1"),
        ("delete", "/api/jobs/1"),
    ],
)
def test_jobs_endpoints_require_session(client: TestClient, method: str, path: str) -> None:
    assert client.request(method, path, json=VALID_JOB).status_code == 401


# --- Oluşturma ---


def test_recruiter_creates_job(recruiter_client: TestClient, recruiter: User, db: Session) -> None:
    created = _create(recruiter_client)

    assert created["title"] == VALID_JOB["title"]
    assert created["required_skills"] == ["Python", "FastAPI", "SQL"]
    assert created["languages"] == [{"language": "İngilizce", "level": "B2"}]
    assert created["min_education"] == "bachelor"
    assert created["created_by"] == recruiter.id
    assert created["created_at"].endswith("Z") or created["created_at"].endswith("+00:00")

    entry = db.scalars(select(AuditLog).where(AuditLog.action == "job.create")).one()
    assert entry.entity_id == created["id"]
    assert entry.payload == {"status": "open"}


def test_create_applies_defaults_for_optional_fields(recruiter_client: TestClient) -> None:
    response = recruiter_client.post(
        "/api/jobs", json={"title": "Stajyer", "required_skills": ["Excel"]}
    )

    assert response.status_code == 201
    body = response.json()
    assert body["department"] == ""
    assert body["preferred_skills"] == []
    assert body["min_experience_years"] == 0
    assert body["min_education"] == "none"
    assert body["languages"] == []
    assert body["status"] == "open"


def test_create_trims_whitespace(recruiter_client: TestClient) -> None:
    created = _create(recruiter_client, title="  Veri Analisti  ", required_skills=[" SQL "])

    assert created["title"] == "Veri Analisti"
    assert created["required_skills"] == ["SQL"]


@pytest.mark.parametrize(
    ("override", "field", "message"),
    [
        ({"title": "ab"}, "title", "En az 3 karakter olmalı"),
        ({"title": "x" * 121}, "title", "En fazla 120 karakter olabilir"),
        ({"description": "x" * 5001}, "description", "En fazla 5000 karakter olabilir"),
        ({"required_skills": []}, "required_skills", "En az 1 öğe eklenmeli"),
        (
            {"required_skills": [f"beceri{i}" for i in range(21)]},
            "required_skills",
            "En fazla 20 öğe eklenebilir",
        ),
        (
            {"preferred_skills": [f"beceri{i}" for i in range(21)]},
            "preferred_skills",
            "En fazla 20 öğe eklenebilir",
        ),
        ({"min_experience_years": -1}, "min_experience_years", "En az 0 olmalı"),
        ({"min_experience_years": 41}, "min_experience_years", "En fazla 40 olabilir"),
        ({"min_experience_years": 2.5}, "min_experience_years", "Tam sayı olmalı"),
        ({"min_education": "doktor"}, "min_education", "Geçersiz değer"),
        ({"status": "draft"}, "status", "Geçersiz değer"),
        (
            {"languages": [{"language": f"Dil{i}", "level": "B1"} for i in range(6)]},
            "languages",
            "En fazla 5 öğe eklenebilir",
        ),
    ],
)
def test_create_rejects_invalid_fields_with_turkish_field_errors(
    recruiter_client: TestClient, override: dict[str, Any], field: str, message: str
) -> None:
    loc, msg = _field_error(recruiter_client.post("/api/jobs", json={**VALID_JOB, **override}))

    assert loc[:2] == ["body", field]
    assert message in msg


def test_create_requires_title_and_required_skills(recruiter_client: TestClient) -> None:
    response = recruiter_client.post("/api/jobs", json={})

    assert response.status_code == 422
    errors = {tuple(e["loc"]): e["msg"] for e in response.json()["detail"]}
    assert errors[("body", "title")] == "Bu alan zorunlu"
    assert errors[("body", "required_skills")] == "Bu alan zorunlu"


def test_create_rejects_invalid_language_level(recruiter_client: TestClient) -> None:
    loc, msg = _field_error(
        recruiter_client.post(
            "/api/jobs", json={**VALID_JOB, "languages": [{"language": "Almanca", "level": "D1"}]}
        )
    )

    assert loc == ["body", "languages", 0, "level"]
    assert "A1" in msg and "C2" in msg


def test_create_rejects_duplicate_skills_case_insensitive(recruiter_client: TestClient) -> None:
    loc, msg = _field_error(
        recruiter_client.post(
            "/api/jobs", json={**VALID_JOB, "required_skills": ["Python", "python"]}
        )
    )

    assert loc[:2] == ["body", "required_skills"]
    assert "birden fazla" in msg


def test_create_rejects_duplicate_languages(recruiter_client: TestClient) -> None:
    languages = [{"language": "İngilizce", "level": "B2"}, {"language": "ingilizce", "level": "C1"}]
    loc, msg = _field_error(
        recruiter_client.post("/api/jobs", json={**VALID_JOB, "languages": languages})
    )

    assert loc[:2] == ["body", "languages"]
    assert "birden fazla" in msg


def test_create_rejects_skill_in_both_lists(recruiter_client: TestClient) -> None:
    loc, msg = _field_error(
        recruiter_client.post(
            "/api/jobs", json={**VALID_JOB, "preferred_skills": ["Docker", "SQL"]}
        )
    )

    assert loc == ["body", "preferred_skills"]
    assert "SQL" in msg


def test_validation_errors_do_not_echo_input(recruiter_client: TestClient) -> None:
    response = recruiter_client.post("/api/jobs", json={**VALID_JOB, "title": "ab"})

    assert "input" not in response.json()["detail"][0]


# --- Listeleme ve detay ---


def test_list_returns_newest_first_with_application_stats(recruiter_client: TestClient) -> None:
    first = _create(recruiter_client, title="Birinci ilan")
    second = _create(recruiter_client, title="İkinci ilan")

    response = recruiter_client.get("/api/jobs")

    assert response.status_code == 200
    items = response.json()
    assert [item["id"] for item in items] == [second["id"], first["id"]]
    assert items[0]["application_count"] == 0
    assert items[0]["top_score"] is None
    assert items[0]["avg_score"] is None


def test_get_job(recruiter_client: TestClient) -> None:
    created = _create(recruiter_client)

    response = recruiter_client.get(f"/api/jobs/{created['id']}")

    assert response.status_code == 200
    assert response.json() == {
        **created,
        "application_count": 0,
        "top_score": None,
        "avg_score": None,
    }


def test_get_unknown_job_returns_404(recruiter_client: TestClient) -> None:
    response = recruiter_client.get("/api/jobs/999")

    assert response.status_code == 404
    assert response.json() == {"detail": "İlan bulunamadı"}


# --- Güncelleme ---


def test_patch_updates_only_sent_fields_and_audits(
    recruiter_client: TestClient, db: Session
) -> None:
    created = _create(recruiter_client)

    response = recruiter_client.patch(
        f"/api/jobs/{created['id']}", json={"status": "closed", "min_experience_years": 5}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "closed"
    assert body["min_experience_years"] == 5
    assert body["title"] == created["title"]
    assert body["required_skills"] == created["required_skills"]

    entry = db.scalars(select(AuditLog).where(AuditLog.action == "job.update")).one()
    assert entry.payload == {"fields": ["min_experience_years", "status"], "status": "closed"}


def test_patch_without_changes_writes_no_audit(recruiter_client: TestClient, db: Session) -> None:
    created = _create(recruiter_client)

    recruiter_client.patch(f"/api/jobs/{created['id']}", json={"title": created["title"]})

    assert db.scalars(select(AuditLog).where(AuditLog.action == "job.update")).all() == []


def test_patch_validates_fields(recruiter_client: TestClient) -> None:
    created = _create(recruiter_client)

    loc, msg = _field_error(
        recruiter_client.patch(f"/api/jobs/{created['id']}", json={"required_skills": []})
    )

    assert loc[:2] == ["body", "required_skills"]
    assert "En az 1" in msg


def test_patch_rejects_explicit_null(recruiter_client: TestClient) -> None:
    created = _create(recruiter_client)

    loc, msg = _field_error(
        recruiter_client.patch(f"/api/jobs/{created['id']}", json={"title": None})
    )

    assert loc == ["body", "title"]
    assert msg == "Bu alan boş olamaz"


def test_patch_checks_overlap_against_stored_required_skills(recruiter_client: TestClient) -> None:
    created = _create(recruiter_client)

    loc, msg = _field_error(
        recruiter_client.patch(f"/api/jobs/{created['id']}", json={"preferred_skills": ["python"]})
    )

    assert loc == ["body", "preferred_skills"]
    assert "python" in msg


def test_patch_unknown_job_returns_404(recruiter_client: TestClient) -> None:
    assert recruiter_client.patch("/api/jobs/999", json={"title": "Yeni başlık"}).status_code == 404


# --- Silme ---


def test_delete_job(recruiter_client: TestClient, db: Session) -> None:
    created = _create(recruiter_client)

    response = recruiter_client.delete(f"/api/jobs/{created['id']}")

    assert response.status_code == 204
    assert recruiter_client.get(f"/api/jobs/{created['id']}").status_code == 404
    entry = db.scalars(select(AuditLog).where(AuditLog.action == "job.delete")).one()
    assert entry.entity_id == created["id"]


def test_delete_unknown_job_returns_404(recruiter_client: TestClient) -> None:
    assert recruiter_client.delete("/api/jobs/999").status_code == 404
