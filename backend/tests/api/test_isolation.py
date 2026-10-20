from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Application, AuditLog, Candidate, Job, Note, User
from app.storage.files import FileStorage
from tests.conftest import FIXTURES

PDF_BYTES = (FIXTURES / "cv_deniz_arslan.pdf").read_bytes()

# (metot, yol şablonu, istek gövdesi); {job} {app} {cand} {note} yabancı kaynak id'leriyle dolar.
FOREIGN_REQUESTS: list[tuple[str, str, dict[str, Any]]] = [
    ("GET", "/api/jobs/{job}", {}),
    ("PATCH", "/api/jobs/{job}", {"json": {"title": "Ele geçirildi"}}),
    ("DELETE", "/api/jobs/{job}", {}),
    ("GET", "/api/jobs/{job}/applications", {}),
    ("POST", "/api/jobs/{job}/rescore", {}),
    ("POST", "/api/jobs/{job}/cvs", {"files": [("files", ("cv.pdf", PDF_BYTES))]}),
    ("GET", "/api/applications/{app}", {}),
    ("PATCH", "/api/applications/{app}/status", {"json": {"status": "reviewing"}}),
    ("POST", "/api/applications/{app}/notes", {"json": {"body": "x"}}),
    ("POST", "/api/applications/{app}/retry", {}),
    ("DELETE", "/api/notes/{note}", {}),
    ("GET", "/api/candidates/{cand}/cv", {}),
    ("DELETE", "/api/candidates/{cand}", {}),
]


def _ids(application: Application, db: Session) -> dict[str, int]:
    note = db.scalars(select(Note).where(Note.application_id == application.id)).one()
    return {
        "job": application.job_id,
        "app": application.id,
        "cand": application.candidate_id,
        "note": note.id,
    }


def _missing() -> dict[str, int]:
    return {"job": 999999, "app": 999999, "cand": 999999, "note": 999999}


@pytest.mark.parametrize(("method", "path", "kwargs"), FOREIGN_REQUESTS)
def test_foreign_resources_return_404(
    recruiter_client: TestClient,
    foreign_application: Application,
    db: Session,
    method: str,
    path: str,
    kwargs: dict[str, Any],
) -> None:
    foreign = recruiter_client.request(
        method, path.format(**_ids(foreign_application, db)), **kwargs
    )
    missing = recruiter_client.request(method, path.format(**_missing()), **kwargs)

    assert foreign.status_code == 404, foreign.text
    assert foreign.json() == missing.json()


def test_list_jobs_only_own(
    recruiter_client: TestClient, recruiter: User, foreign_application: Application
) -> None:
    own_id = recruiter_client.post(
        "/api/jobs", json={"title": "Benim ilanım", "required_skills": ["SQL"]}
    ).json()["id"]

    jobs = recruiter_client.get("/api/jobs").json()

    assert [job["id"] for job in jobs] == [own_id]


def test_foreign_rows_unchanged(
    recruiter_client: TestClient,
    foreign_application: Application,
    db: Session,
    storage: FileStorage,
) -> None:
    ids = _ids(foreign_application, db)
    candidate = db.get(Candidate, ids["cand"])
    assert candidate is not None
    stored_path = candidate.stored_path
    for method, path, kwargs in FOREIGN_REQUESTS:
        recruiter_client.request(method, path.format(**ids), **kwargs)

    db.expire_all()
    job = db.get(Job, ids["job"])
    assert job is not None and job.title == "Başkasının ilanı"
    assert db.get(Candidate, ids["cand"]) is not None
    application = db.get(Application, ids["app"])
    assert application is not None and application.status.value == "new"
    notes = db.scalars(select(Note).where(Note.application_id == ids["app"])).all()
    assert [n.body for n in notes] == ["Gizli not"]
    assert db.scalar(select(func.count(Application.id))) == 1
    assert storage.path_for(stored_path).exists()


def test_recruiter_can_delete_own_candidate(
    recruiter_client: TestClient, db: Session, storage: FileStorage
) -> None:
    job_id = recruiter_client.post(
        "/api/jobs", json={"title": "Backend Geliştirici", "required_skills": ["Python"]}
    ).json()["id"]
    [application_id] = recruiter_client.post(
        f"/api/jobs/{job_id}/cvs", files=[("files", ("cv.pdf", PDF_BYTES))]
    ).json()["application_ids"]
    candidate_id = recruiter_client.get(f"/api/applications/{application_id}").json()["candidate"][
        "id"
    ]
    candidate = db.get(Candidate, candidate_id)
    assert candidate is not None
    stored_path = candidate.stored_path
    assert storage.path_for(stored_path).exists()

    response = recruiter_client.delete(f"/api/candidates/{candidate_id}")

    assert response.status_code == 204
    assert not storage.path_for(stored_path).exists()
    assert db.scalars(select(AuditLog).where(AuditLog.action == "candidate.delete")).one()
