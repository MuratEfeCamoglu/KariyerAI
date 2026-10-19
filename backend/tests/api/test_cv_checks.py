import json
from datetime import timedelta
from pathlib import Path
from typing import Any

import httpx
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.db import utc_now
from app.models import Candidate, CVCheck, ProcessingStatus, User
from app.services.candidates import NO_TEXT
from app.storage.files import FileStorage
from tests.conftest import FIXTURES, SEEKER_PASSWORD, LoginFn

PDF_BYTES = (FIXTURES / "cv_deniz_arslan.pdf").read_bytes()
SCANNED_BYTES = (FIXTURES / "scanned_cv.pdf").read_bytes()

CRITERIA: dict[str, Any] = {
    "title": "Backend Geliştirici",
    "required_skills": ["Python", "Kubernetes"],
    "preferred_skills": ["Docker"],
    "min_experience_years": 3,
    "min_education": "bachelor",
    "languages": [{"language": "English", "level": "B2"}],
}


def _create(
    client: TestClient,
    criteria: dict[str, Any] | str = CRITERIA,
    data: bytes = PDF_BYTES,
    filename: str = "cv.pdf",
) -> httpx.Response:
    raw = criteria if isinstance(criteria, str) else json.dumps(criteria)
    return client.post(
        "/api/cv-checks",
        data={"criteria": raw},
        files={"file": (filename, data, "application/pdf")},
    )


def _uploads(storage: FileStorage) -> list[Path]:
    return list(storage.base_dir.glob("*")) if storage.base_dir.exists() else []


def _old_check(owner: User, **overrides: Any) -> CVCheck:
    return CVCheck(
        owner_id=owner.id,
        title="Eski",
        required_skills=["Python"],
        original_filename="cv.pdf",
        stored_path="a" * 32 + ".pdf",
        file_hash="0" * 64,
        **overrides,
    )


def test_create_check_returns_202_and_processes(seeker_client: TestClient) -> None:
    response = _create(seeker_client)

    assert response.status_code == 202, response.text
    check_id = response.json()["id"]
    detail = seeker_client.get(f"/api/cv-checks/{check_id}").json()
    assert detail["parse_status"] == "done"
    assert detail["score_status"] == "done"
    assert isinstance(detail["score"], int)
    assert detail["title"] == "Backend Geliştirici"
    assert detail["required_skills"] == ["Python", "Kubernetes"]
    assert detail["parsed"] is not None
    assert detail["gaps"][0]["kind"] == "required_skill"
    assert detail["gaps"][0]["criterion"] == "Kubernetes"


def test_create_check_invalid_criteria_422(seeker_client: TestClient, storage: FileStorage) -> None:
    response = _create(seeker_client, {**CRITERIA, "required_skills": []})

    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["body", "required_skills"]
    assert _uploads(storage) == []


def test_create_check_bad_json_422(seeker_client: TestClient) -> None:
    response = _create(seeker_client, "{bozuk")

    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["body", "criteria"]


def test_create_check_missing_file_422(seeker_client: TestClient) -> None:
    response = seeker_client.post("/api/cv-checks", data={"criteria": json.dumps(CRITERIA)})

    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["body", "file"]


def test_create_check_unsupported_file_422(seeker_client: TestClient) -> None:
    response = _create(seeker_client, data=b"duz metin dosyasi", filename="cv.txt")

    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["body", "file"]


def test_create_check_scanned_pdf_marks_failed(seeker_client: TestClient) -> None:
    check_id = _create(seeker_client, data=SCANNED_BYTES).json()["id"]

    detail = seeker_client.get(f"/api/cv-checks/{check_id}").json()
    assert detail["parse_status"] == "failed"
    assert detail["parse_error"] == NO_TEXT
    assert detail["score_status"] == "failed"
    assert detail["gaps"] == []


def test_daily_limit_429(seeker_client: TestClient, seeker: User, db: Session) -> None:
    db.add_all([_old_check(seeker) for _ in range(10)])
    db.commit()

    assert _create(seeker_client).status_code == 429


def test_daily_limit_counts_only_last_24_hours(
    seeker_client: TestClient, seeker: User, db: Session
) -> None:
    db.add_all([_old_check(seeker, created_at=utc_now() - timedelta(hours=25)) for _ in range(10)])
    db.commit()

    assert _create(seeker_client).status_code == 202


def _switch_to_second_seeker(client: TestClient) -> None:
    response = client.post(
        "/api/auth/register",
        json={"email": "ikinci@example.com", "full_name": "İkinci", "password": SEEKER_PASSWORD},
    )
    assert response.status_code == 201


def test_list_returns_only_own_checks(seeker_client: TestClient, login: LoginFn) -> None:
    own_id = _create(seeker_client).json()["id"]
    _switch_to_second_seeker(seeker_client)
    _create(seeker_client)

    assert len(seeker_client.get("/api/cv-checks").json()) == 1
    login("aday@example.com", SEEKER_PASSWORD)
    items = seeker_client.get("/api/cv-checks").json()
    assert [item["id"] for item in items] == [own_id]


def test_other_users_check_is_404(seeker_client: TestClient) -> None:
    check_id = _create(seeker_client).json()["id"]
    _switch_to_second_seeker(seeker_client)

    assert seeker_client.get(f"/api/cv-checks/{check_id}").status_code == 404
    assert seeker_client.delete(f"/api/cv-checks/{check_id}").status_code == 404
    assert seeker_client.post(f"/api/cv-checks/{check_id}/retry").status_code == 404


def test_delete_removes_file_and_row(
    seeker_client: TestClient, storage: FileStorage, db: Session
) -> None:
    check_id = _create(seeker_client).json()["id"]
    assert len(_uploads(storage)) == 1

    response = seeker_client.delete(f"/api/cv-checks/{check_id}")

    assert response.status_code == 204
    assert _uploads(storage) == []
    assert db.get(CVCheck, check_id) is None


def test_retry_failed_score(seeker_client: TestClient, db: Session) -> None:
    check_id = _create(seeker_client).json()["id"]
    check = db.get(CVCheck, check_id)
    assert check is not None
    check.score_status = ProcessingStatus.FAILED
    check.score_error = "Puanlama servisine ulaşılamadı"
    db.commit()

    response = seeker_client.post(f"/api/cv-checks/{check_id}/retry")

    assert response.status_code == 202
    assert seeker_client.get(f"/api/cv-checks/{check_id}").json()["score_status"] == "done"


def test_retry_extraction_error_409(seeker_client: TestClient) -> None:
    check_id = _create(seeker_client, data=SCANNED_BYTES).json()["id"]

    assert seeker_client.post(f"/api/cv-checks/{check_id}/retry").status_code == 409


def test_retry_without_error_409(seeker_client: TestClient) -> None:
    check_id = _create(seeker_client).json()["id"]

    assert seeker_client.post(f"/api/cv-checks/{check_id}/retry").status_code == 409


def test_staff_cannot_use_cv_checks_403(recruiter_client: TestClient) -> None:
    assert recruiter_client.get("/api/cv-checks").status_code == 403
    assert _create(recruiter_client).status_code == 403


def test_unauthenticated_401(client: TestClient) -> None:
    assert client.get("/api/cv-checks").status_code == 401


def test_seeker_check_not_in_staff_tables(seeker_client: TestClient, db: Session) -> None:
    _create(seeker_client)

    assert db.scalar(select(func.count()).select_from(Candidate)) == 0
