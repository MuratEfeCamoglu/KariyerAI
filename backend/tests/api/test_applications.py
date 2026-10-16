import time
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    Application,
    ApplicationStatus,
    AuditLog,
    Candidate,
    ProcessingStatus,
    User,
)
from app.services.candidates import NO_TEXT
from tests.conftest import FIXTURES

PDF_BYTES = (FIXTURES / "cv_deniz_arslan.pdf").read_bytes()
DOCX_BYTES = (FIXTURES / "cv_elif_kaya.docx").read_bytes()
BASE_TIME = datetime(2026, 10, 1, 9, 0, tzinfo=UTC)


@pytest.fixture
def job_id(recruiter_client: TestClient) -> int:
    response = recruiter_client.post(
        "/api/jobs",
        json={
            "title": "Backend Geliştirici",
            "required_skills": ["Python", "FastAPI"],
            "preferred_skills": ["Docker"],
            "languages": [{"language": "English", "level": "B2"}],
        },
    )
    return int(response.json()["id"])


def _insert(
    db: Session,
    job_id: int,
    *,
    score: int | None,
    minutes: int = 0,
    status: ApplicationStatus = ApplicationStatus.NEW,
    parse_status: ProcessingStatus = ProcessingStatus.DONE,
    score_status: ProcessingStatus | None = None,
    name: str | None = "Aday",
    parsed: dict[str, Any] | None = None,
    parse_error: str | None = None,
) -> Application:
    """LLM'e gitmeden liste/sıralama verisi üretir (ISKELET F7c: seed-demo gibi)."""
    candidate = Candidate(
        full_name=name,
        original_filename="cv.pdf",
        stored_path="a" * 32 + ".pdf",
        file_hash=f"{job_id}-{minutes}-{score}-{name}".ljust(64, "0")[:64],
        cv_text="Python ve FastAPI deneyimi.",
        parsed_data=parsed,
        parse_status=parse_status,
        parse_error=parse_error,
    )
    db.add(candidate)
    db.flush()
    breakdown = None
    if score is not None:
        breakdown = {
            key: {"points": float(score) / 5}
            for key in (
                "required_skills",
                "experience",
                "education",
                "languages",
                "preferred_skills",
            )
        }
    application = Application(
        job_id=job_id,
        candidate_id=candidate.id,
        status=status,
        score=score,
        score_breakdown=breakdown,
        score_status=score_status
        or (ProcessingStatus.DONE if score is not None else ProcessingStatus.PENDING),
        created_at=BASE_TIME + timedelta(minutes=minutes),
    )
    db.add(application)
    db.commit()
    return application


def _list(client: TestClient, job_id: int, **params: Any) -> dict[str, Any]:
    response = client.get(f"/api/jobs/{job_id}/applications", params=params)
    assert response.status_code == 200, response.text
    body: dict[str, Any] = response.json()
    return body


# --- F7a: sıralama ve sayfalama ---


def test_list_sorted_by_score_desc_nulls_last_ties_oldest_first(
    recruiter_client: TestClient, job_id: int, db: Session
) -> None:
    low = _insert(db, job_id, score=40, minutes=1)
    unscored = _insert(db, job_id, score=None, minutes=0)
    tie_newer = _insert(db, job_id, score=80, minutes=5)
    tie_older = _insert(db, job_id, score=80, minutes=2)
    top = _insert(db, job_id, score=95, minutes=9)

    items = _list(recruiter_client, job_id)["items"]

    assert [i["id"] for i in items] == [top.id, tie_older.id, tie_newer.id, low.id, unscored.id]


def test_pagination_is_50_per_page(recruiter_client: TestClient, job_id: int, db: Session) -> None:
    for minute in range(55):
        _insert(db, job_id, score=minute, minutes=minute)

    first = _list(recruiter_client, job_id)
    second = _list(recruiter_client, job_id, page=2)

    assert (first["total"], first["page_size"], len(first["items"])) == (55, 50, 50)
    assert first["items"][0]["score"] == 54
    assert [i["score"] for i in second["items"]] == [4, 3, 2, 1, 0]


# --- F7b: filtreler ---


def test_filters_min_score_status_and_parse_status(
    recruiter_client: TestClient, job_id: int, db: Session
) -> None:
    hired = _insert(db, job_id, score=90, status=ApplicationStatus.HIRED)
    shortlisted = _insert(db, job_id, score=70, minutes=1, status=ApplicationStatus.SHORTLISTED)
    _insert(db, job_id, score=30, minutes=2, status=ApplicationStatus.REJECTED)
    failed = _insert(
        db,
        job_id,
        score=None,
        minutes=3,
        parse_status=ProcessingStatus.FAILED,
        score_status=ProcessingStatus.FAILED,
    )

    by_score = _list(recruiter_client, job_id, min_score=60)["items"]
    by_status = _list(recruiter_client, job_id, status=["hired", "shortlisted"])["items"]
    by_parse = _list(recruiter_client, job_id, parse_status="failed")["items"]

    assert [i["id"] for i in by_score] == [hired.id, shortlisted.id]
    assert [i["id"] for i in by_status] == [hired.id, shortlisted.id]
    assert [i["id"] for i in by_parse] == [failed.id]


@pytest.mark.parametrize(
    "params",
    [{"min_score": 101}, {"min_score": -1}, {"status": "arsiv"}, {"page": 0}],
)
def test_invalid_filters_return_422(
    recruiter_client: TestClient, job_id: int, params: dict[str, Any]
) -> None:
    response = recruiter_client.get(f"/api/jobs/{job_id}/applications", params=params)

    assert response.status_code == 422


def test_list_requires_session_and_existing_job(
    client: TestClient, recruiter_client: TestClient
) -> None:
    assert recruiter_client.get("/api/jobs/999/applications").status_code == 404
    recruiter_client.cookies.clear()
    assert client.get("/api/jobs/1/applications").status_code == 401


# --- Satır içeriği ---


def test_row_contains_items_last_position_and_experience(
    recruiter_client: TestClient, job_id: int, db: Session
) -> None:
    parsed = {
        "experiences": [
            {"title": "Junior Developer", "start": "2015-01", "end": "2018-12"},
            {"title": "Lead Developer", "start": "2021-01", "end": "present"},
            {"title": "Developer", "start": "2019-01", "end": "2020-12"},
        ],
        "total_experience_years": 9.9,
    }
    _insert(db, job_id, score=75, name="Deniz Arslan", parsed=parsed)

    [row] = _list(recruiter_client, job_id)["items"]

    assert row["candidate_name"] == "Deniz Arslan"
    assert row["last_position"] == "Lead Developer"
    assert row["total_experience_years"] == 9.9
    assert row["item_points"] == {
        "required_skills": 15.0,
        "experience": 15.0,
        "education": 15.0,
        "languages": 15.0,
        "preferred_skills": 15.0,
    }


def test_processing_count_drives_auto_refresh(
    recruiter_client: TestClient, job_id: int, db: Session
) -> None:
    _insert(db, job_id, score=50)
    _insert(db, job_id, score=None, minutes=1, parse_status=ProcessingStatus.PROCESSING)
    _insert(db, job_id, score=None, minutes=2, score_status=ProcessingStatus.PENDING)

    body = _list(recruiter_client, job_id, min_score=40)

    # Filtre yalnızca 1 satır gösterse de ilanda 2 kayıt hâlâ işleniyor.
    assert (body["total"], body["processing_count"]) == (1, 2)


# --- F7c: performans ---


def test_list_with_500_applications_p95_under_500ms(
    recruiter_client: TestClient, job_id: int, db: Session
) -> None:
    for i in range(500):
        candidate = Candidate(
            full_name=f"Aday {i}",
            original_filename="cv.pdf",
            stored_path="a" * 32 + ".pdf",
            file_hash=f"{i:064d}",
            cv_text="",
            parsed_data={"experiences": [{"title": "Dev", "start": "2020-01", "end": "present"}]},
            parse_status=ProcessingStatus.DONE,
        )
        db.add(candidate)
        db.flush()
        db.add(
            Application(
                job_id=job_id,
                candidate_id=candidate.id,
                score=i % 101,
                score_breakdown={
                    k: {"points": 1.0}
                    for k in (
                        "required_skills",
                        "experience",
                        "education",
                        "languages",
                        "preferred_skills",
                    )
                },
                score_status=ProcessingStatus.DONE,
            )
        )
    db.commit()

    durations = []
    for page in (1, 5, 10) * 7:
        started = time.perf_counter()
        _list(recruiter_client, job_id, page=page, min_score=10)
        durations.append(time.perf_counter() - started)
    durations.sort()

    assert durations[int(len(durations) * 0.95) - 1] < 0.5


# --- F6: uçtan uca puanlama (FakeLLMClient) ---


def _upload(client: TestClient, job_id: int, name: str, data: bytes) -> int:
    response = client.post(f"/api/jobs/{job_id}/cvs", files=[("files", (name, data))])
    assert response.status_code == 202, response.text
    return int(response.json()["application_ids"][0])


def test_upload_is_scored_with_breakdown_summary_and_audit(
    recruiter_client: TestClient, job_id: int, db: Session
) -> None:
    application_id = _upload(recruiter_client, job_id, "deniz.pdf", PDF_BYTES)

    db.expire_all()
    application = db.get(Application, application_id)
    assert application is not None
    assert application.score_status is ProcessingStatus.DONE
    # Deniz CV'si: Python ve FastAPI var (40), Docker var (10), English C1 ≥ B2 (10),
    # deneyim ve eğitim kriteri yok (25 + 15) → 100.
    assert application.score == 100
    assert application.score_breakdown is not None
    assert application.score_breakdown["required_skills"]["met"] == 2
    item = application.score_breakdown["languages"]["items"][0]
    assert (item["status"], item["candidate_level"]) == ("verified", "C1")
    assert application.ai_summary
    assert (application.llm_model, application.prompt_version) == ("fake", "score_v1")

    entry = db.scalars(select(AuditLog).where(AuditLog.action == "score.result")).one()
    assert entry.payload == {"status": "done", "score": 100, "model": "fake", "prompt": "score_v1"}


def test_criteria_change_rescores_without_reparsing(
    recruiter_client: TestClient, job_id: int, db: Session
) -> None:
    application_id = _upload(recruiter_client, job_id, "elif.docx", DOCX_BYTES)
    db.expire_all()
    before = db.get(Application, application_id)
    assert before is not None and before.score is not None
    # Kimlik haritası aynı nesneyi döndürür; eski değer önceden kopyalanmalı.
    score_before = before.score
    parse_audits = len(db.scalars(select(AuditLog).where(AuditLog.action == "cv.parse")).all())

    response = recruiter_client.patch(
        f"/api/jobs/{job_id}", json={"required_skills": ["SQL", "Power BI"]}
    )

    assert response.status_code == 200
    db.expire_all()
    after = db.get(Application, application_id)
    assert after is not None
    assert after.score_breakdown is not None
    assert after.score_breakdown["required_skills"]["met"] == 2
    assert after.score != score_before
    # Ayrıştırma tekrarlanmadı (F6f).
    assert len(db.scalars(select(AuditLog).where(AuditLog.action == "cv.parse")).all()) == (
        parse_audits
    )


def test_title_change_does_not_rescore(
    recruiter_client: TestClient, job_id: int, db: Session
) -> None:
    _upload(recruiter_client, job_id, "deniz.pdf", PDF_BYTES)

    recruiter_client.patch(
        f"/api/jobs/{job_id}", json={"title": "Kıdemli Backend", "description": "Yeni açıklama"}
    )

    assert db.scalars(select(AuditLog).where(AuditLog.action == "job.rescore")).all() == []


def test_rescore_endpoint_queues_parsed_applications(
    recruiter_client: TestClient, job_id: int, db: Session
) -> None:
    scored = _upload(recruiter_client, job_id, "deniz.pdf", PDF_BYTES)
    _insert(
        db,
        job_id,
        score=None,
        parse_status=ProcessingStatus.FAILED,
        score_status=ProcessingStatus.FAILED,
    )

    response = recruiter_client.post(f"/api/jobs/{job_id}/rescore")

    assert response.status_code == 202
    assert response.json() == {"application_ids": [scored]}


def test_rescore_unknown_job_returns_404(recruiter_client: TestClient) -> None:
    assert recruiter_client.post("/api/jobs/999/rescore").status_code == 404


# --- F7e: yeniden dene ---


def test_retry_after_score_failure_rescores(
    recruiter_client: TestClient, job_id: int, db: Session
) -> None:
    application_id = _upload(recruiter_client, job_id, "deniz.pdf", PDF_BYTES)
    db.expire_all()
    application = db.get(Application, application_id)
    assert application is not None
    application.score_status = ProcessingStatus.FAILED
    application.score_error = "Puanlama servisine ulaşılamadı"
    db.commit()

    response = recruiter_client.post(f"/api/applications/{application_id}/retry")

    assert response.status_code == 202
    db.expire_all()
    refreshed = db.get(Application, application_id)
    assert refreshed is not None
    assert (refreshed.score_status, refreshed.score_error) == (ProcessingStatus.DONE, None)
    entry = db.scalars(select(AuditLog).where(AuditLog.action == "application.retry")).one()
    assert entry.payload == {"step": "score"}


def test_retry_after_parse_failure_reparses_and_scores(
    recruiter_client: TestClient, job_id: int, db: Session
) -> None:
    application_id = _upload(recruiter_client, job_id, "deniz.pdf", PDF_BYTES)
    db.expire_all()
    application = db.get(Application, application_id)
    assert application is not None
    candidate = db.get(Candidate, application.candidate_id)
    assert candidate is not None
    candidate.parse_status = ProcessingStatus.FAILED
    candidate.parse_error = "Ayrıştırma servisine ulaşılamadı"
    application.score_status = ProcessingStatus.FAILED
    application.score = None
    db.commit()

    assert recruiter_client.post(f"/api/applications/{application_id}/retry").status_code == 202

    db.expire_all()
    assert db.get(Candidate, candidate.id).parse_status is ProcessingStatus.DONE  # type: ignore[union-attr]
    assert db.get(Application, application_id).score == 100  # type: ignore[union-attr]


def test_retry_of_unreadable_file_returns_409(
    recruiter_client: TestClient, job_id: int, db: Session
) -> None:
    application = _insert(
        db,
        job_id,
        score=None,
        parse_status=ProcessingStatus.FAILED,
        score_status=ProcessingStatus.FAILED,
        parse_error=NO_TEXT,
    )

    response = recruiter_client.post(f"/api/applications/{application.id}/retry")

    assert response.status_code == 409
    assert "metin çıkarılamadı" in response.json()["detail"]


def test_retry_without_failure_returns_409(
    recruiter_client: TestClient, job_id: int, db: Session
) -> None:
    application = _insert(db, job_id, score=60)

    response = recruiter_client.post(f"/api/applications/{application.id}/retry")

    assert response.status_code == 409


def test_retry_unknown_application_returns_404(recruiter_client: TestClient) -> None:
    assert recruiter_client.post("/api/applications/999/retry").status_code == 404


def test_retry_requires_session(client: TestClient, recruiter: User) -> None:
    assert client.post("/api/applications/1/retry").status_code == 401
