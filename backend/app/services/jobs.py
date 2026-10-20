from dataclasses import dataclass
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import ConflictError, FieldValidationError, NotFoundError
from app.models.application import Application
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


def _stats_by_job(db: Session, job_ids: list[int]) -> dict[int, JobStats]:
    if not job_ids:
        return {}
    # max/avg puanı olmayan (henüz puanlanmamış) başvuruları yok sayar; sayıma hepsi girer.
    rows = db.execute(
        select(
            Application.job_id,
            func.count(Application.id),
            func.max(Application.score),
            func.avg(Application.score),
        )
        .where(Application.job_id.in_(job_ids))
        .group_by(Application.job_id)
    ).all()
    return {
        job_id: JobStats(
            application_count=count,
            top_score=top,
            avg_score=round(float(avg), 1) if avg is not None else None,
        )
        for job_id, count, top, avg in rows
    }


def list_jobs(db: Session, *, owner_id: int) -> list[tuple[Job, JobStats]]:
    jobs = db.scalars(
        select(Job).where(Job.created_by == owner_id).order_by(Job.created_at.desc(), Job.id.desc())
    ).all()
    stats = _stats_by_job(db, [job.id for job in jobs])
    return [(job, stats.get(job.id, EMPTY_STATS)) for job in jobs]


def get_job_with_stats(db: Session, job_id: int, *, owner_id: int) -> tuple[Job, JobStats]:
    job = get_job(db, job_id, owner_id=owner_id)
    return job, _stats_by_job(db, [job_id]).get(job_id, EMPTY_STATS)


def get_job(db: Session, job_id: int, *, owner_id: int) -> Job:
    # Başkasının ilanı ile olmayan ilan aynı 404'ü verir: varlığı sızdırılmaz.
    job = db.scalar(select(Job).where(Job.id == job_id, Job.created_by == owner_id))
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


@dataclass(frozen=True)
class JobUpdateResult:
    job: Job
    # F6f: yalnızca kriter alanları değiştiyse başvurular yeniden puanlanır (başlık/açıklama değil).
    criteria_changed: bool


def update_job(
    db: Session, *, job_id: int, changes: dict[str, Any], actor_id: int, owner_id: int
) -> JobUpdateResult:
    job = get_job(db, job_id, owner_id=owner_id)
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
    return JobUpdateResult(job=job, criteria_changed=bool(CRITERIA_FIELDS & set(changed_fields)))


def delete_job(db: Session, *, job_id: int, actor_id: int, owner_id: int) -> None:
    job = get_job(db, job_id, owner_id=owner_id)
    if db.scalar(select(Application.id).where(Application.job_id == job_id).limit(1)) is not None:
        raise ConflictError("Başvurusu olan ilan silinemez; bunun yerine ilanı kapatabilirsiniz")
    db.delete(job)
    audit.record(db, actor_id=actor_id, action="job.delete", entity_type="job", entity_id=job_id)
    db.commit()
