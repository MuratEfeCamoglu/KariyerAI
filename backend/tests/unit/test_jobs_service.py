from datetime import UTC
from typing import Any

import pytest
from sqlalchemy.orm import Session

from app.core.errors import FieldValidationError, NotFoundError
from app.models import EducationLevel, Job, JobStatus, User
from app.services import jobs as jobs_service


def _data(**overrides: Any) -> dict[str, Any]:
    return {
        "title": "Veri Analisti",
        "department": "",
        "description": "",
        "required_skills": ["SQL", "Python"],
        "preferred_skills": [],
        "min_experience_years": 2,
        "min_education": EducationLevel.BACHELOR,
        "languages": [{"language": "İngilizce", "level": "B2"}],
        "status": JobStatus.OPEN,
        **overrides,
    }


def test_create_job_persists_and_returns_utc_timestamps(db: Session, recruiter: User) -> None:
    job = jobs_service.create_job(db, data=_data(), actor_id=recruiter.id)
    db.expire_all()

    stored = db.get(Job, job.id)
    assert stored is not None
    assert stored.min_education == EducationLevel.BACHELOR
    assert stored.created_at.tzinfo == UTC
    assert stored.updated_at.tzinfo == UTC


def test_create_job_rejects_overlapping_skills(db: Session, recruiter: User) -> None:
    with pytest.raises(FieldValidationError) as exc_info:
        jobs_service.create_job(db, data=_data(preferred_skills=["sql"]), actor_id=recruiter.id)

    assert exc_info.value.field == "preferred_skills"


def test_update_job_bumps_updated_at(db: Session, recruiter: User) -> None:
    job = jobs_service.create_job(db, data=_data(), actor_id=recruiter.id)
    before = job.updated_at

    updated = jobs_service.update_job(
        db, job_id=job.id, changes={"title": "Kıdemli Veri Analisti"}, actor_id=recruiter.id
    )

    assert updated.title == "Kıdemli Veri Analisti"
    assert updated.updated_at >= before


def test_get_job_raises_not_found(db: Session) -> None:
    with pytest.raises(NotFoundError):
        jobs_service.get_job(db, 123)


def test_list_jobs_returns_empty_stats_until_applications_exist(
    db: Session, recruiter: User
) -> None:
    jobs_service.create_job(db, data=_data(), actor_id=recruiter.id)

    [(job, stats)] = jobs_service.list_jobs(db)

    assert job.title == "Veri Analisti"
    assert stats == jobs_service.EMPTY_STATS


def test_delete_job_removes_row(db: Session, recruiter: User) -> None:
    job = jobs_service.create_job(db, data=_data(), actor_id=recruiter.id)

    jobs_service.delete_job(db, job_id=job.id, actor_id=recruiter.id)

    assert db.get(Job, job.id) is None
