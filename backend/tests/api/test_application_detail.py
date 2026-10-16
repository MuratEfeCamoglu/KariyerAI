from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AuditLog, Candidate, User
from app.services import audit
from app.storage.files import FileStorage
from tests.conftest import ADMIN_PASSWORD, FIXTURES, LoginFn

PDF_BYTES = (FIXTURES / "cv_deniz_arslan.pdf").read_bytes()
DOCX_BYTES = (FIXTURES / "cv_elif_kaya.docx").read_bytes()


@pytest.fixture
def job_id(recruiter_client: TestClient) -> int:
    response = recruiter_client.post(
        "/api/jobs",
        json={"title": "Backend Geliştirici", "required_skills": ["Python", "Go"]},
    )
    return int(response.json()["id"])


@pytest.fixture
def application_id(recruiter_client: TestClient, job_id: int) -> int:
    response = recruiter_client.post(
        f"/api/jobs/{job_id}/cvs",
        files=[("files", ("Deniz Arslan Özgeçmiş.pdf", PDF_BYTES, "application/pdf"))],
    )
    assert response.status_code == 202, response.text
    return int(response.json()["application_ids"][0])


def _detail(client: TestClient, application_id: int) -> dict[str, Any]:
    response = client.get(f"/api/applications/{application_id}")
    assert response.status_code == 200, response.text
    body: dict[str, Any] = response.json()
    return body


# --- F8: detay ---


def test_detail_contains_score_breakdown_summary_and_parsed_cv(
    recruiter_client: TestClient, job_id: int, application_id: int
) -> None:
    detail = _detail(recruiter_client, application_id)

    assert detail["job"] == {"id": job_id, "title": "Backend Geliştirici", "status": "open"}
    assert detail["candidate"]["full_name"] == "Deniz Arslan"
    assert detail["candidate"]["email"] == "deniz.arslan@example.com"
    assert detail["candidate"]["original_filename"] == "Deniz Arslan Özgeçmiş.pdf"
    assert detail["candidate"]["parsed"]["skills"] == ["Python", "FastAPI", "PostgreSQL", "Docker"]
    # Python var, Go yok → 20 + 25 + 15 + 10 + 10 = 80
    assert detail["score"] == 80
    items = detail["score_breakdown"]["required_skills"]["items"]
    assert [(i["criterion"], i["status"]) for i in items] == [
        ("Python", "verified"),
        ("Go", "no_evidence"),
    ]
    assert items[0]["evidence"]
    assert detail["ai_summary"]
    assert (detail["llm_model"], detail["prompt_version"]) == ("fake", "score_v1")
    assert detail["status"] == "new"
    assert detail["notes"] == [] and detail["status_history"] == []


def test_detail_not_found_and_requires_session(
    client: TestClient, recruiter_client: TestClient
) -> None:
    assert recruiter_client.get("/api/applications/999").status_code == 404
    recruiter_client.cookies.clear()
    assert client.get("/api/applications/1").status_code == 401


# --- F9: durum akışı ---


def test_status_change_is_audited_and_shown_in_history(
    recruiter_client: TestClient, recruiter: User, application_id: int, db: Session
) -> None:
    for status in ("reviewing", "shortlisted"):
        response = recruiter_client.patch(
            f"/api/applications/{application_id}/status", json={"status": status}
        )
        assert response.status_code == 200

    detail = response.json()
    assert detail["status"] == "shortlisted"
    assert [(h["from_status"], h["to_status"]) for h in detail["status_history"]] == [
        ("reviewing", "shortlisted"),
        ("new", "reviewing"),
    ]
    assert detail["status_history"][0]["actor_name"] == recruiter.full_name
    entries = db.scalars(select(AuditLog).where(AuditLog.action == "application.status")).all()
    assert [e.payload for e in entries] == [
        {"from": "new", "to": "reviewing"},
        {"from": "reviewing", "to": "shortlisted"},
    ]
    assert all(e.actor_id == recruiter.id for e in entries)


@pytest.mark.parametrize(
    ("start", "target"),
    [("hired", "new"), ("rejected", "interview"), ("new", "hired"), ("interview", "rejected")],
)
def test_any_status_can_move_to_any_other(
    recruiter_client: TestClient, application_id: int, start: str, target: str
) -> None:
    recruiter_client.patch(f"/api/applications/{application_id}/status", json={"status": start})

    response = recruiter_client.patch(
        f"/api/applications/{application_id}/status", json={"status": target}
    )

    assert response.json()["status"] == target


def test_same_status_is_not_audited(
    recruiter_client: TestClient, application_id: int, db: Session
) -> None:
    recruiter_client.patch(f"/api/applications/{application_id}/status", json={"status": "new"})

    assert db.scalars(select(AuditLog).where(AuditLog.action == "application.status")).all() == []


def test_invalid_status_returns_422(recruiter_client: TestClient, application_id: int) -> None:
    response = recruiter_client.patch(
        f"/api/applications/{application_id}/status", json={"status": "elendi"}
    )

    assert response.status_code == 422


def test_system_never_changes_status(
    recruiter_client: TestClient, job_id: int, application_id: int
) -> None:
    recruiter_client.patch(
        f"/api/applications/{application_id}/status", json={"status": "shortlisted"}
    )

    # Yeniden puanlama ve puan düşüşü durumu etkilemez (V1: otomatik eleme yok).
    recruiter_client.patch(f"/api/jobs/{job_id}", json={"required_skills": ["Rust", "Haskell"]})
    recruiter_client.post(f"/api/jobs/{job_id}/rescore")

    detail = _detail(recruiter_client, application_id)
    assert detail["score"] < 80
    assert detail["status"] == "shortlisted"


def test_status_change_on_unknown_application_returns_404(recruiter_client: TestClient) -> None:
    response = recruiter_client.patch("/api/applications/999/status", json={"status": "new"})

    assert response.status_code == 404


# --- F10: notlar ---


def test_add_note_shows_author_and_time(
    recruiter_client: TestClient, recruiter: User, application_id: int
) -> None:
    response = recruiter_client.post(
        f"/api/applications/{application_id}/notes", json={"body": "  Teknik mülakata çağrılsın.  "}
    )

    assert response.status_code == 201
    note = response.json()
    assert note["body"] == "Teknik mülakata çağrılsın."
    assert (note["author_id"], note["author_name"]) == (recruiter.id, recruiter.full_name)
    assert note["created_at"]
    assert [n["id"] for n in _detail(recruiter_client, application_id)["notes"]] == [note["id"]]


@pytest.mark.parametrize(
    ("body", "status"), [("", 422), ("   ", 422), ("x" * 2001, 422), ("x" * 2000, 201)]
)
def test_note_length_limits(
    recruiter_client: TestClient, application_id: int, body: str, status: int
) -> None:
    response = recruiter_client.post(
        f"/api/applications/{application_id}/notes", json={"body": body}
    )

    assert response.status_code == status


def test_note_on_unknown_application_returns_404(recruiter_client: TestClient) -> None:
    assert (
        recruiter_client.post("/api/applications/999/notes", json={"body": "x"}).status_code == 404
    )


def test_only_author_can_delete_note(
    recruiter_client: TestClient,
    application_id: int,
    admin: User,
    login: LoginFn,
) -> None:
    note_id = recruiter_client.post(
        f"/api/applications/{application_id}/notes", json={"body": "Not"}
    ).json()["id"]
    recruiter_cookies = dict(recruiter_client.cookies)

    admin_client = login(admin.email, ADMIN_PASSWORD)
    forbidden = admin_client.delete(f"/api/notes/{note_id}")
    assert forbidden.status_code == 403
    assert forbidden.json() == {"detail": "Yalnızca kendi notunuzu silebilirsiniz"}

    admin_client.cookies.clear()
    for key, value in recruiter_cookies.items():
        admin_client.cookies.set(key, value)
    assert admin_client.delete(f"/api/notes/{note_id}").status_code == 204
    assert admin_client.delete(f"/api/notes/{note_id}").status_code == 404


# --- CV indirme ---


def test_cv_download_is_attachment_with_original_name(
    recruiter_client: TestClient, application_id: int
) -> None:
    candidate_id = _detail(recruiter_client, application_id)["candidate"]["id"]

    response = recruiter_client.get(f"/api/candidates/{candidate_id}/cv")

    assert response.status_code == 200
    assert response.content == PDF_BYTES
    assert response.headers["content-type"] == "application/pdf"
    disposition = response.headers["content-disposition"]
    assert disposition.startswith("attachment")
    assert "filename*=utf-8''Deniz%20Arslan%20%C3%96zge%C3%A7mi%C5%9F.pdf" in disposition


def test_cv_download_errors(
    client: TestClient,
    recruiter_client: TestClient,
    application_id: int,
    db: Session,
    storage: FileStorage,
) -> None:
    assert recruiter_client.get("/api/candidates/999/cv").status_code == 404

    candidate = db.scalars(select(Candidate)).one()
    storage.delete(candidate.stored_path)
    assert recruiter_client.get(f"/api/candidates/{candidate.id}/cv").status_code == 404

    recruiter_client.cookies.clear()
    assert client.get(f"/api/candidates/{candidate.id}/cv").status_code == 401


# --- F12: denetim kaydı ---


def test_audit_lists_newest_first_for_admin_only(
    recruiter_client: TestClient,
    application_id: int,
    admin: User,
    login: LoginFn,
) -> None:
    recruiter_client.patch(
        f"/api/applications/{application_id}/status", json={"status": "interview"}
    )
    assert recruiter_client.get("/api/audit").status_code == 403

    admin_client = login(admin.email, ADMIN_PASSWORD)
    entries = admin_client.get("/api/audit").json()

    assert entries[0]["action"] == "auth.login"
    assert entries[0]["actor_name"] == admin.full_name
    actions = [e["action"] for e in entries]
    for expected in ("cv.upload", "cv.parse", "score.result", "application.status", "job.create"):
        assert expected in actions
    timestamps = [e["created_at"] for e in entries]
    assert timestamps == sorted(timestamps, reverse=True)


def test_audit_returns_at_most_500(admin_client: TestClient, db: Session) -> None:
    for i in range(510):
        audit.record(db, actor_id=None, action="test.event", entity_type="test", entity_id=i)
    db.commit()

    entries = admin_client.get("/api/audit").json()

    assert len(entries) == 500
    assert entries[0]["entity_id"] == 509


def test_audit_payloads_never_contain_personal_data(
    recruiter_client: TestClient, job_id: int, application_id: int, db: Session
) -> None:
    recruiter_client.post(
        f"/api/jobs/{job_id}/cvs", files=[("files", ("Elif Kaya CV.docx", DOCX_BYTES))]
    )
    recruiter_client.patch(f"/api/applications/{application_id}/status", json={"status": "hired"})
    recruiter_client.post(f"/api/applications/{application_id}/notes", json={"body": "Gizli not"})
    recruiter_client.post(f"/api/jobs/{job_id}/rescore")

    payloads = " ".join(str(e.payload) for e in db.scalars(select(AuditLog)))
    for personal in (
        "Deniz",
        "Arslan",
        "Elif",
        "Kaya",
        "@example.com",
        "555",
        ".pdf",
        ".docx",
        "Gizli",
    ):
        assert personal not in payloads, personal
