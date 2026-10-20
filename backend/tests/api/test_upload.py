import io
import time
from datetime import timedelta
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import utc_now
from app.models import Application, AuditLog, Candidate, ProcessingStatus
from app.storage.files import FileStorage
from tests.conftest import FIXTURES
from tests.fixtures.build_fixtures import PDF_CV_LINES, text_docx, text_pdf

PDF_BYTES = (FIXTURES / "cv_deniz_arslan.pdf").read_bytes()
DOCX_BYTES = (FIXTURES / "cv_elif_kaya.docx").read_bytes()
SCANNED_BYTES = (FIXTURES / "scanned_cv.pdf").read_bytes()

FileTuple = tuple[str, tuple[str, bytes, str]]


def _file(name: str, data: bytes, content_type: str = "application/octet-stream") -> FileTuple:
    return ("files", (name, data, content_type))


def _unique_pdf(index: int) -> bytes:
    return text_pdf([*PDF_CV_LINES, f"Reference number: {index}"])


@pytest.fixture
def job_id(recruiter_client: TestClient) -> int:
    response = recruiter_client.post(
        "/api/jobs", json={"title": "Backend Geliştirici", "required_skills": ["Python"]}
    )
    job: dict[str, Any] = response.json()
    return int(job["id"])


def _upload(client: TestClient, job_id: int, files: list[FileTuple]) -> Any:
    return client.post(f"/api/jobs/{job_id}/cvs", files=files)


# --- F4a / F4f: 1–20 dosya, 202 + başvuru id'leri ---


def test_upload_pdf_and_docx_returns_202_with_application_ids(
    recruiter_client: TestClient, job_id: int, db: Session
) -> None:
    response = _upload(
        recruiter_client,
        job_id,
        [_file("deniz.pdf", PDF_BYTES, "application/pdf"), _file("elif.docx", DOCX_BYTES)],
    )

    assert response.status_code == 202
    body = response.json()
    assert len(body["application_ids"]) == 2
    assert [f["status"] for f in body["files"]] == ["accepted", "accepted"]
    applications = db.scalars(select(Application).where(Application.job_id == job_id)).all()
    assert {a.id for a in applications} == set(body["application_ids"])


def test_twenty_files_are_accepted_within_time_budget(
    recruiter_client: TestClient, job_id: int
) -> None:
    files = [_file(f"cv{i}.pdf", _unique_pdf(i)) for i in range(20)]

    started = time.perf_counter()
    response = _upload(recruiter_client, job_id, files)
    elapsed = time.perf_counter() - started

    assert response.status_code == 202
    assert len(response.json()["application_ids"]) == 20
    # F4f: N dosya için ≤ N × 2 sn (TestClient arka plan işlerini de bu süreye katar).
    assert elapsed < 40


def test_more_than_twenty_files_returns_422(recruiter_client: TestClient, job_id: int) -> None:
    files = [_file(f"cv{i}.pdf", _unique_pdf(i)) for i in range(21)]

    response = _upload(recruiter_client, job_id, files)

    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["body", "files"]
    assert "en fazla 20" in response.json()["detail"][0]["msg"]


def test_request_without_files_returns_422(recruiter_client: TestClient, job_id: int) -> None:
    response = recruiter_client.post(f"/api/jobs/{job_id}/cvs", data={"x": "1"})

    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["body", "files"]


# --- F4b / F4c: tür ve boyut; reddedilen dosya diğerlerini engellemez ---


def test_invalid_file_is_rejected_while_others_are_processed(
    recruiter_client: TestClient, job_id: int
) -> None:
    response = _upload(
        recruiter_client,
        job_id,
        [
            _file("gercek.pdf", PDF_BYTES),
            _file("sahte.pdf", b"Bu aslinda duz metin, uzantisi pdf", "application/pdf"),
            _file("buyuk.pdf", PDF_BYTES + b"0" * (5 * 1024 * 1024)),
            _file("resim.docx", b"\x89PNG\r\n\x1a\n" + b"\x00" * 64),
        ],
    )

    assert response.status_code == 202
    files = response.json()["files"]
    assert files[0]["status"] == "accepted"
    assert [(f["status"], f["error_code"], f["detail"]) for f in files[1:]] == [
        ("rejected", 422, "Yalnızca PDF ve DOCX dosyaları kabul edilir"),
        ("rejected", 422, "Dosya 5 MB'tan büyük"),
        ("rejected", 422, "Yalnızca PDF ve DOCX dosyaları kabul edilir"),
    ]


def test_single_invalid_file_returns_422(recruiter_client: TestClient, job_id: int) -> None:
    response = _upload(recruiter_client, job_id, [_file("not.txt", b"duz metin")])

    assert response.status_code == 422
    assert response.json()["detail"] == "Yalnızca PDF ve DOCX dosyaları kabul edilir"


def test_type_is_detected_from_content_not_extension(
    recruiter_client: TestClient, job_id: int, db: Session
) -> None:
    response = _upload(recruiter_client, job_id, [_file("yanlis-uzanti.docx", PDF_BYTES)])

    assert response.status_code == 202
    candidate = db.scalars(select(Candidate)).one()
    assert candidate.stored_path.endswith(".pdf")
    assert candidate.original_filename == "yanlis-uzanti.docx"


def test_file_of_exactly_five_megabytes_is_accepted(
    recruiter_client: TestClient, job_id: int
) -> None:
    padded = PDF_BYTES + b"\n%" + b"0" * (5 * 1024 * 1024 - len(PDF_BYTES) - 2)
    assert len(padded) == 5 * 1024 * 1024

    response = _upload(recruiter_client, job_id, [_file("tam5mb.pdf", padded)])

    assert response.status_code == 202


# --- F4d: tekrar yükleme ---


def test_same_file_twice_to_same_job_returns_409(recruiter_client: TestClient, job_id: int) -> None:
    assert _upload(recruiter_client, job_id, [_file("a.pdf", PDF_BYTES)]).status_code == 202

    response = _upload(recruiter_client, job_id, [_file("baska-ad.pdf", PDF_BYTES)])

    assert response.status_code == 409
    assert response.json()["detail"] == "Bu CV bu ilana zaten yüklendi"


def test_duplicate_within_same_batch_is_rejected(recruiter_client: TestClient, job_id: int) -> None:
    response = _upload(
        recruiter_client, job_id, [_file("a.pdf", PDF_BYTES), _file("b.pdf", PDF_BYTES)]
    )

    assert response.status_code == 202
    assert [f["error_code"] for f in response.json()["files"]] == [None, 409]


def test_same_file_can_be_uploaded_to_another_job(
    recruiter_client: TestClient, job_id: int
) -> None:
    other = recruiter_client.post(
        "/api/jobs", json={"title": "Diğer ilan", "required_skills": ["SQL"]}
    ).json()
    _upload(recruiter_client, job_id, [_file("a.pdf", PDF_BYTES)])

    assert _upload(recruiter_client, other["id"], [_file("a.pdf", PDF_BYTES)]).status_code == 202


# --- F4e: metin çıkarılamayan dosya ---


def test_image_only_pdf_creates_failed_candidate(
    recruiter_client: TestClient, job_id: int, db: Session
) -> None:
    response = _upload(recruiter_client, job_id, [_file("taranmis.pdf", SCANNED_BYTES)])

    assert response.status_code == 202
    candidate = db.scalars(select(Candidate)).one()
    application = db.scalars(select(Application)).one()
    assert candidate.parse_status is ProcessingStatus.FAILED
    assert candidate.parse_error == "Metin çıkarılamadı (taranmış/görsel PDF olabilir)"
    assert application.score_status is ProcessingStatus.FAILED
    assert application.score_error == "Ayrıştırma başarısız"


def test_text_shorter_than_200_characters_fails(
    recruiter_client: TestClient, job_id: int, db: Session
) -> None:
    short = text_docx(["Kısa CV", "Beceriler: SQL"])

    _upload(recruiter_client, job_id, [_file("kisa.docx", short)])

    candidate = db.scalars(select(Candidate)).one()
    assert candidate.parse_status is ProcessingStatus.FAILED
    assert candidate.parse_error is not None and "Metin çıkarılamadı" in candidate.parse_error


# --- Pipeline, depolama, audit ---


def test_background_parse_runs_after_upload(
    recruiter_client: TestClient, job_id: int, db: Session
) -> None:
    _upload(recruiter_client, job_id, [_file("elif.docx", DOCX_BYTES)])

    db.expire_all()
    candidate = db.scalars(select(Candidate)).one()
    assert candidate.parse_status is ProcessingStatus.DONE
    assert candidate.full_name == "Elif Kaya"
    assert candidate.parsed_data is not None
    assert "Power BI" in candidate.parsed_data["skills"]


def test_file_is_stored_under_random_name_and_audit_has_no_personal_data(
    recruiter_client: TestClient, job_id: int, db: Session, storage: FileStorage
) -> None:
    _upload(recruiter_client, job_id, [_file("Deniz_Arslan_CV.pdf", PDF_BYTES)])

    candidate = db.scalars(select(Candidate)).one()
    assert "Deniz" not in candidate.stored_path
    assert storage.path_for(candidate.stored_path).read_bytes() == PDF_BYTES
    entries = db.scalars(select(AuditLog).where(AuditLog.action.in_(["cv.upload", "cv.parse"])))
    for entry in entries:
        serialized = str(entry.payload)
        assert "Deniz" not in serialized and ".pdf" not in serialized and "@" not in serialized


def test_browser_supplied_path_is_reduced_to_file_name(
    recruiter_client: TestClient, job_id: int, db: Session
) -> None:
    _upload(recruiter_client, job_id, [_file("C:\\Users\\ik\\Desktop\\cv.pdf", PDF_BYTES)])

    assert db.scalars(select(Candidate)).one().original_filename == "cv.pdf"


# --- İlan kuralları ve yetki ---


def test_upload_to_closed_job_returns_409(recruiter_client: TestClient, job_id: int) -> None:
    recruiter_client.patch(f"/api/jobs/{job_id}", json={"status": "closed"})

    response = _upload(recruiter_client, job_id, [_file("a.pdf", PDF_BYTES)])

    assert response.status_code == 409
    assert response.json() == {"detail": "Kapalı ilana CV yüklenemez"}


def test_upload_to_unknown_job_returns_404(recruiter_client: TestClient) -> None:
    assert _upload(recruiter_client, 999, [_file("a.pdf", PDF_BYTES)]).status_code == 404


def test_upload_requires_session(client: TestClient) -> None:
    response = client.post("/api/jobs/1/cvs", files=[_file("a.pdf", io.BytesIO(PDF_BYTES).read())])

    assert response.status_code == 401


def test_job_stats_and_delete_conflict_after_upload(
    recruiter_client: TestClient, job_id: int
) -> None:
    _upload(recruiter_client, job_id, [_file("a.pdf", PDF_BYTES), _file("b.docx", DOCX_BYTES)])

    listed = recruiter_client.get("/api/jobs").json()[0]
    detail = recruiter_client.get(f"/api/jobs/{job_id}").json()
    assert listed["application_count"] == detail["application_count"] == 2
    # İlan "Python" istiyor; iki fixture CV de Python içeriyor ve arka planda puanlanmış olmalı.
    assert listed["top_score"] == detail["top_score"] == 100

    response = recruiter_client.delete(f"/api/jobs/{job_id}")
    assert response.status_code == 409
    assert "kapatabilirsiniz" in response.json()["detail"]


# --- Günlük CV sınırı (çoklu işveren) ---


def _bulk_candidates(db: Session, job_id: int, count: int, *, age_hours: float = 0) -> None:
    created = utc_now() - timedelta(hours=age_hours)
    for i in range(count):
        candidate = Candidate(
            original_filename="x.pdf",
            stored_path="yok.pdf",
            file_hash=f"{job_id:04d}{i:060d}",
            cv_text="",
            parse_status=ProcessingStatus.DONE,
            created_at=created,
        )
        db.add(candidate)
        db.flush()
        db.add(Application(job_id=job_id, candidate_id=candidate.id))
    db.commit()


def _distinct_pdfs(n: int) -> list[FileTuple]:
    return [_file(f"cv{i}.pdf", _unique_pdf(1000 + i)) for i in range(n)]


def test_daily_cv_limit(
    recruiter_client: TestClient, job_id: int, db: Session, storage: FileStorage
) -> None:
    _bulk_candidates(db, job_id, 95)
    before = sorted(storage.base_dir.glob("*")) if storage.base_dir.exists() else []

    response = _upload(recruiter_client, job_id, _distinct_pdfs(6))

    assert response.status_code == 429
    assert "Kalan hakkınız: 5." in response.json()["detail"]
    after = sorted(storage.base_dir.glob("*")) if storage.base_dir.exists() else []
    assert after == before
    assert _upload(recruiter_client, job_id, _distinct_pdfs(5)).status_code == 202


def test_daily_cv_limit_window(recruiter_client: TestClient, job_id: int, db: Session) -> None:
    _bulk_candidates(db, job_id, 100, age_hours=25)

    assert _upload(recruiter_client, job_id, _distinct_pdfs(1)).status_code == 202


def test_daily_cv_limit_per_owner(
    recruiter_client: TestClient, job_id: int, db: Session, foreign_application: Application
) -> None:
    _bulk_candidates(db, foreign_application.job_id, 100)

    assert _upload(recruiter_client, job_id, _distinct_pdfs(1)).status_code == 202
