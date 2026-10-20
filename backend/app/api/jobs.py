from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, File, Query, UploadFile
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session, sessionmaker

from app.core.db import get_session_factory
from app.core.deps import DbSession, RecruiterUser
from app.models import ApplicationStatus, ProcessingStatus
from app.models.job import Job
from app.schemas.application import (
    ApplicationListOut,
    ApplicationRowOut,
    ItemPoints,
    QueuedApplications,
)
from app.schemas.job import JobCreate, JobListItem, JobOut, JobUpdate
from app.schemas.upload import UploadFileResult, UploadResponse
from app.services import applications as applications_service
from app.services import candidates as candidates_service
from app.services import jobs as jobs_service
from app.services import pipeline
from app.services.cv_extract import MAX_FILE_BYTES
from app.services.jobs import JobStats
from app.storage.files import FileStorage, get_storage

router = APIRouter(prefix="/jobs", tags=["jobs"])

SessionFactoryDep = Annotated[sessionmaker[Session], Depends(get_session_factory)]


def _with_stats(job: Job, stats: JobStats) -> JobListItem:
    return JobListItem.model_validate(
        {
            **JobOut.model_validate(job).model_dump(),
            "application_count": stats.application_count,
            "top_score": stats.top_score,
            "avg_score": stats.avg_score,
        }
    )


@router.get("")
def list_jobs(user: RecruiterUser, db: DbSession) -> list[JobListItem]:
    return [_with_stats(job, stats) for job, stats in jobs_service.list_jobs(db, owner_id=user.id)]


@router.post("", status_code=201)
def create_job(body: JobCreate, user: RecruiterUser, db: DbSession) -> JobOut:
    job = jobs_service.create_job(db, data=body.model_dump(), actor_id=user.id)
    return JobOut.model_validate(job)


@router.get("/{job_id}")
def get_job(job_id: int, user: RecruiterUser, db: DbSession) -> JobListItem:
    return _with_stats(*jobs_service.get_job_with_stats(db, job_id, owner_id=user.id))


def _queue_rescore(
    db: Session,
    job_id: int,
    actor_id: int,
    background_tasks: BackgroundTasks,
    session_factory: sessionmaker[Session],
) -> list[int]:
    ids = applications_service.mark_job_for_rescore(
        db, job_id, actor_id=actor_id, owner_id=actor_id
    )
    for application_id in ids:
        background_tasks.add_task(pipeline.process_application, application_id, session_factory)
    return ids


@router.patch("/{job_id}")
def update_job(
    job_id: int,
    body: JobUpdate,
    background_tasks: BackgroundTasks,
    user: RecruiterUser,
    db: DbSession,
    session_factory: SessionFactoryDep,
) -> JobOut:
    result = jobs_service.update_job(
        db,
        job_id=job_id,
        changes=body.model_dump(exclude_unset=True),
        actor_id=user.id,
        owner_id=user.id,
    )
    if result.criteria_changed:
        _queue_rescore(db, job_id, user.id, background_tasks, session_factory)
    return JobOut.model_validate(result.job)


@router.post("/{job_id}/rescore", status_code=202)
def rescore_job(
    job_id: int,
    background_tasks: BackgroundTasks,
    user: RecruiterUser,
    db: DbSession,
    session_factory: SessionFactoryDep,
) -> QueuedApplications:
    jobs_service.get_job(db, job_id, owner_id=user.id)
    ids = _queue_rescore(db, job_id, user.id, background_tasks, session_factory)
    return QueuedApplications(application_ids=ids)


@router.get("/{job_id}/applications")
def list_applications(
    job_id: int,
    user: RecruiterUser,
    db: DbSession,
    min_score: Annotated[int | None, Query(ge=0, le=100)] = None,
    status: Annotated[list[ApplicationStatus] | None, Query()] = None,
    parse_status: ProcessingStatus | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
) -> ApplicationListOut:
    result = applications_service.list_applications(
        db,
        job_id=job_id,
        filters=applications_service.ApplicationFilters(
            min_score=min_score, statuses=tuple(status or ()), parse_status=parse_status
        ),
        page=page,
        owner_id=user.id,
    )
    items = []
    for row in result.rows:
        application, candidate = row.application, row.candidate
        breakdown = application.score_breakdown
        parsed = candidate.parsed_data
        items.append(
            ApplicationRowOut(
                id=application.id,
                candidate_id=candidate.id,
                candidate_name=candidate.full_name,
                score=application.score,
                item_points=ItemPoints(
                    **{key: breakdown[key]["points"] for key in ItemPoints.model_fields}
                )
                if breakdown
                else None,
                last_position=applications_service.last_position(parsed),
                total_experience_years=parsed.get("total_experience_years") if parsed else None,
                status=application.status,
                parse_status=candidate.parse_status,
                parse_error=candidate.parse_error,
                score_status=application.score_status,
                score_error=application.score_error,
                created_at=application.created_at,
            )
        )
    return ApplicationListOut(
        items=items,
        total=result.total,
        page=result.page,
        page_size=result.page_size,
        processing_count=result.processing_count,
    )


@router.delete("/{job_id}", status_code=204)
def delete_job(job_id: int, user: RecruiterUser, db: DbSession) -> None:
    jobs_service.delete_job(db, job_id=job_id, actor_id=user.id, owner_id=user.id)


@router.post(
    "/{job_id}/cvs",
    status_code=202,
    response_model=UploadResponse,
    responses={409: {"description": "Tüm dosyalar tekrar"}, 422: {"description": "Hepsi geçersiz"}},
)
def upload_cvs(
    job_id: int,
    files: Annotated[list[UploadFile], File(description="1–20 adet PDF/DOCX, her biri ≤ 5 MB")],
    background_tasks: BackgroundTasks,
    user: RecruiterUser,
    db: DbSession,
    storage: Annotated[FileStorage, Depends(get_storage)],
    session_factory: SessionFactoryDep,
) -> UploadResponse | JSONResponse:
    # Senkron uç: metin çıkarma CPU işidir, thread havuzunda çalışıp event loop'u bloklamasın.
    # Sınırı aşan dosyanın tamamı belleğe alınmaz; 1 bayt fazlası "büyük" demek için yeterli.
    incoming = [
        candidates_service.IncomingFile(
            filename=file.filename or "", data=file.file.read(MAX_FILE_BYTES + 1)
        )
        for file in files
    ]
    results = candidates_service.upload_cvs(
        db, storage, job_id=job_id, files=incoming, actor_id=user.id, owner_id=user.id
    )
    payload = UploadResponse(
        application_ids=[r.application_id for r in results if r.application_id is not None],
        files=[
            UploadFileResult(
                filename=r.filename,
                status="accepted" if r.accepted else "rejected",
                application_id=r.application_id,
                error_code=r.status_code,
                detail=r.detail,
            )
            for r in results
        ],
    )

    if not payload.application_ids:
        # Hiçbir dosya kabul edilmediyse istek başarısızdır: hepsi tekrar ise 409, değilse 422.
        codes = {r.status_code for r in results}
        status_code = 409 if codes == {409} else 422
        detail = results[0].detail if len(results) == 1 else "Hiçbir dosya kabul edilmedi"
        return JSONResponse(
            status_code=status_code,
            content={"detail": detail, **payload.model_dump(mode="json")},
        )

    for application_id in payload.application_ids:
        background_tasks.add_task(pipeline.process_application, application_id, session_factory)
    return payload
