from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import FieldValidationError, NotFoundError
from app.models.job import Job
from app.services import audit
from app.services.text import fold

# İlanın puanlamayı etkileyen alanları; değişirse Aşama 5'te yeniden puanlama tetiklenecek (F6f).
CRITERIA_FIELDS = frozenset(
    {"required_skills", "preferred_skills", "min_experience_years", "min_education", "languages"}
)


@dataclass(frozen=True)
class JobStats:
    application_count: int
    top_score: int | None
    avg_score: float | None


EMPTY_STATS = JobStats(application_count=0, top_score=None, avg_score=None)


def _check_skill_overlap(required: list[str], preferred: list[str]) -> None:
    # Aynı beceri iki listede olursa puanlamada iki kez sayılır (§3.5).
    required_keys = {fold(skill) for skill in required}
    overlap = [skill for skill in preferred if fold(skill) in required_keys]
    if overlap:
        raise FieldValidationError(
            "preferred_skills", f"Zorunlu becerilerde de var: {', '.join(overlap)}"
        )


def list_jobs(db: Session) -> list[tuple[Job, JobStats]]:
    jobs = db.scalars(select(Job).order_by(Job.created_at.desc(), Job.id.desc())).all()
    # Başvuru tablosu Aşama 3'te eklenir; o zamana kadar her ilanın istatistiği boştur.
    return [(job, EMPTY_STATS) for job in jobs]


def get_job(db: Session, job_id: int) -> Job:
    job = db.get(Job, job_id)
    if job is None:
        raise NotFoundError("İlan bulunamadı")
    return job


def create_job(db: Session, *, data: dict[str, Any], actor_id: int) -> Job:
    _check_skill_overlap(data["required_skills"], data.get("preferred_skills", []))
    job = Job(**data, created_by=actor_id)
    db.add(job)
    db.flush()
    audit.record(
        db,
        actor_id=actor_id,
        action="job.create",
        entity_type="job",
        entity_id=job.id,
        payload={"status": job.status.value},
    )
    db.commit()
    return job


def update_job(db: Session, *, job_id: int, changes: dict[str, Any], actor_id: int) -> Job:
    job = get_job(db, job_id)
    _check_skill_overlap(
        changes.get("required_skills", job.required_skills),
        changes.get("preferred_skills", job.preferred_skills),
    )

    changed_fields = sorted(
        field for field, value in changes.items() if getattr(job, field) != value
    )
    for field in changed_fields:
        setattr(job, field, changes[field])

    if changed_fields:
        audit.record(
            db,
            actor_id=actor_id,
            action="job.update",
            entity_type="job",
            entity_id=job.id,
            payload={"fields": changed_fields, "status": job.status.value},
        )
    db.commit()
    return job


def delete_job(db: Session, *, job_id: int, actor_id: int) -> None:
    job = get_job(db, job_id)
    # Başvurusu olan ilanın silinmesini engelleme (409) Aşama 3'te başvurularla birlikte eklenir.
    db.delete(job)
    audit.record(db, actor_id=actor_id, action="job.delete", entity_type="job", entity_id=job_id)
    db.commit()
