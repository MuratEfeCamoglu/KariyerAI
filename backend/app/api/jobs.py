from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, File, UploadFile
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session, sessionmaker

from app.core.db import get_session_factory
from app.core.deps import CurrentUser, DbSession
from app.models.job import Job
from app.schemas.job import JobCreate, JobListItem, JobOut, JobUpdate
from app.schemas.upload import UploadFileResult, UploadResponse
from app.services import candidates as candidates_service
from app.services import jobs as jobs_service
from app.services import pipeline
from app.services.cv_extract import MAX_FILE_BYTES
from app.services.jobs import JobStats
from app.storage.files import FileStorage, get_storage

router = APIRouter(prefix="/jobs", tags=["jobs"])


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
def list_jobs(_user: CurrentUser, db: DbSession) -> list[JobListItem]:
    return [_with_stats(job, stats) for job, stats in jobs_service.list_jobs(db)]


@router.post("", status_code=201)
def create_job(body: JobCreate, user: CurrentUser, db: DbSession) -> JobOut:
    job = jobs_service.create_job(db, data=body.model_dump(), actor_id=user.id)
    return JobOut.model_validate(job)


@router.get("/{job_id}")
def get_job(job_id: int, _user: CurrentUser, db: DbSession) -> JobListItem:
    return _with_stats(*jobs_service.get_job_with_stats(db, job_id))


@router.patch("/{job_id}")
def update_job(job_id: int, body: JobUpdate, user: CurrentUser, db: DbSession) -> JobOut:
    job = jobs_service.update_job(
        db, job_id=job_id, changes=body.model_dump(exclude_unset=True), actor_id=user.id
    )
    return JobOut.model_validate(job)


@router.delete("/{job_id}", status_code=204)
def delete_job(job_id: int, user: CurrentUser, db: DbSession) -> None:
    jobs_service.delete_job(db, job_id=job_id, actor_id=user.id)


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
    user: CurrentUser,
    db: DbSession,
    storage: Annotated[FileStorage, Depends(get_storage)],
    session_factory: Annotated[sessionmaker[Session], Depends(get_session_factory)],
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
        db, storage, job_id=job_id, files=incoming, actor_id=user.id
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
