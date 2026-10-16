from fastapi import APIRouter

from app.core.deps import CurrentUser, DbSession
from app.schemas.job import JobCreate, JobListItem, JobOut, JobUpdate
from app.services import jobs as jobs_service

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("")
def list_jobs(_user: CurrentUser, db: DbSession) -> list[JobListItem]:
    return [
        JobListItem.model_validate(
            {
                **JobOut.model_validate(job).model_dump(),
                "application_count": stats.application_count,
                "top_score": stats.top_score,
                "avg_score": stats.avg_score,
            }
        )
        for job, stats in jobs_service.list_jobs(db)
    ]


@router.post("", status_code=201)
def create_job(body: JobCreate, user: CurrentUser, db: DbSession) -> JobOut:
    job = jobs_service.create_job(db, data=body.model_dump(), actor_id=user.id)
    return JobOut.model_validate(job)


@router.get("/{job_id}")
def get_job(job_id: int, _user: CurrentUser, db: DbSession) -> JobOut:
    return JobOut.model_validate(jobs_service.get_job(db, job_id))


@router.patch("/{job_id}")
def update_job(job_id: int, body: JobUpdate, user: CurrentUser, db: DbSession) -> JobOut:
    job = jobs_service.update_job(
        db, job_id=job_id, changes=body.model_dump(exclude_unset=True), actor_id=user.id
    )
    return JobOut.model_validate(job)


@router.delete("/{job_id}", status_code=204)
def delete_job(job_id: int, user: CurrentUser, db: DbSession) -> None:
    jobs_service.delete_job(db, job_id=job_id, actor_id=user.id)
