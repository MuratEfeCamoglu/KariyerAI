from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Application, AuditLog, Candidate, Note, User
from app.storage.files import FileStorage
from tests.conftest import ADMIN_PASSWORD, FIXTURES, LoginFn

PDF_BYTES = (FIXTURES / "cv_deniz_arslan.pdf").read_bytes()
DOCX_BYTES = (FIXTURES / "cv_elif_kaya.docx").read_bytes()


def _setup(client: TestClient) -> tuple[int, int]:
    """İlan + iki aday; ilkine durum değişikliği ve not eklenir. (aday_id, başvuru_id) döner."""
    job_id = client.post(
        "/api/jobs", json={"title": "Backend Geliştirici", "required_skills": ["Python"]}
    ).json()["id"]
    ids = client.post(
        f"/api/jobs/{job_id}/cvs",
        files=[
            ("files", ("Deniz Arslan.pdf", PDF_BYTES)),
            ("files", ("Elif Kaya.docx", DOCX_BYTES)),
        ],
    ).json()["application_ids"]
    client.patch(f"/api/applications/{ids[0]}/status", json={"status": "interview"})
    client.post(f"/api/applications/{ids[0]}/notes", json={"body": "Güçlü backend deneyimi"})
    candidate_id = client.get(f"/api/applications/{ids[0]}").json()["candidate"]["id"]
    return int(candidate_id), int(ids[0])


def test_admin_permanently_deletes_candidate_data_and_file(
    admin_client: TestClient, admin: User, db: Session, storage: FileStorage
) -> None:
    candidate_id, application_id = _setup(admin_client)
    stored_path = db.get(Candidate, candidate_id).stored_path  # type: ignore[union-attr]
    assert storage.path_for(stored_path).exists()

    response = admin_client.delete(f"/api/candidates/{candidate_id}")

    assert response.status_code == 204
    db.expire_all()
    assert db.get(Candidate, candidate_id) is None
    assert db.get(Application, application_id) is None
    assert db.scalar(select(func.count(Note.id)).where(Note.application_id == application_id)) == 0
    # F11: işlem sonrası dosya diskte bulunmaz.
    assert not storage.path_for(stored_path).exists()
    # Diğer aday etkilenmez.
    assert db.scalar(select(func.count(Candidate.id))) == 1

    entry = db.scalars(select(AuditLog).where(AuditLog.action == "candidate.delete")).one()
    assert (entry.actor_id, entry.entity_type, entry.entity_id, entry.payload) == (
        admin.id,
        "candidate",
        candidate_id,
        {},
    )


def test_deleted_candidate_is_gone_from_api(admin_client: TestClient) -> None:
    candidate_id, application_id = _setup(admin_client)

    admin_client.delete(f"/api/candidates/{candidate_id}")

    assert admin_client.get(f"/api/applications/{application_id}").status_code == 404
    assert admin_client.get(f"/api/candidates/{candidate_id}/cv").status_code == 404
    assert admin_client.delete(f"/api/candidates/{candidate_id}").status_code == 404


def test_audit_after_delete_contains_no_personal_data(
    admin_client: TestClient, db: Session
) -> None:
    candidate_id, _ = _setup(admin_client)

    admin_client.delete(f"/api/candidates/{candidate_id}")

    payloads = " ".join(str(e.payload) for e in db.scalars(select(AuditLog)))
    for personal in ("Deniz", "Arslan", "@example.com", ".pdf", "Güçlü"):
        assert personal not in payloads, personal


def test_recruiter_cannot_delete_candidate(
    recruiter_client: TestClient, db: Session, storage: FileStorage
) -> None:
    candidate_id, _ = _setup(recruiter_client)

    response = recruiter_client.delete(f"/api/candidates/{candidate_id}")

    assert response.status_code == 403
    candidate = db.get(Candidate, candidate_id)
    assert candidate is not None
    assert storage.path_for(candidate.stored_path).exists()


def test_delete_requires_session(client: TestClient, admin: User, login: LoginFn) -> None:
    assert client.delete("/api/candidates/1").status_code == 401
    assert login(admin.email, ADMIN_PASSWORD).delete("/api/candidates/999").status_code == 404


def test_job_can_be_deleted_after_its_only_candidate_is_removed(
    admin_client: TestClient, db: Session
) -> None:
    job_id = admin_client.post(
        "/api/jobs", json={"title": "Tek adaylı ilan", "required_skills": ["SQL"]}
    ).json()["id"]
    [application_id] = admin_client.post(
        f"/api/jobs/{job_id}/cvs", files=[("files", ("cv.pdf", PDF_BYTES))]
    ).json()["application_ids"]
    candidate_id = admin_client.get(f"/api/applications/{application_id}").json()["candidate"]["id"]
    assert admin_client.delete(f"/api/jobs/{job_id}").status_code == 409

    admin_client.delete(f"/api/candidates/{candidate_id}")

    assert admin_client.delete(f"/api/jobs/{job_id}").status_code == 204
