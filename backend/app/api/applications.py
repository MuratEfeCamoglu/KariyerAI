from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy.orm import Session, sessionmaker

from app.core.db import get_session_factory
from app.core.deps import DbSession, RecruiterUser
from app.schemas.application import (
    ApplicationDetailOut,
    CandidateOut,
    JobSummary,
    NoteCreate,
    NoteOut,
    QueuedApplications,
    StatusChange,
    StatusUpdate,
)
from app.schemas.parsed_cv import ParsedCV
from app.schemas.scoring import ScoreBreakdown
from app.services import applications as applications_service
from app.services import notes as notes_service
from app.services import pipeline

router = APIRouter(prefix="/applications", tags=["applications"])
notes_router = APIRouter(prefix="/notes", tags=["notes"])

SessionFactoryDep = Annotated[sessionmaker[Session], Depends(get_session_factory)]


def _detail(db: Session, application_id: int, owner_id: int) -> ApplicationDetailOut:
    detail = applications_service.get_detail(db, application_id, owner_id=owner_id)
    application, candidate, job = detail.application, detail.candidate, detail.job
    return ApplicationDetailOut(
        id=application.id,
        job=JobSummary(id=job.id, title=job.title, status=job.status),
        candidate=CandidateOut(
            id=candidate.id,
            full_name=candidate.full_name,
            email=candidate.email,
            phone=candidate.phone,
            original_filename=candidate.original_filename,
            parse_status=candidate.parse_status,
            parse_error=candidate.parse_error,
            parsed=ParsedCV.model_validate(candidate.parsed_data)
            if candidate.parsed_data
            else None,
        ),
        status=application.status,
        score=application.score,
        score_breakdown=ScoreBreakdown.model_validate(application.score_breakdown)
        if application.score_breakdown
        else None,
        ai_summary=application.ai_summary,
        llm_model=application.llm_model,
        prompt_version=application.prompt_version,
        score_status=application.score_status,
        score_error=application.score_error,
        created_at=application.created_at,
        updated_at=application.updated_at,
        notes=[
            NoteOut(
                id=view.note.id,
                body=view.note.body,
                author_id=view.note.author_id,
                author_name=view.author_name,
                created_at=view.note.created_at,
            )
            for view in detail.notes
        ],
        status_history=[
            StatusChange(
                from_status=change.from_status,
                to_status=change.to_status,
                actor_id=change.actor_id,
                actor_name=change.actor_name,
                created_at=change.created_at,
            )
            for change in detail.status_history
        ],
    )


@router.get("/{application_id}")
def get_application(
    application_id: int, user: RecruiterUser, db: DbSession
) -> ApplicationDetailOut:
    return _detail(db, application_id, user.id)


@router.patch("/{application_id}/status")
def change_status(
    application_id: int, body: StatusUpdate, user: RecruiterUser, db: DbSession
) -> ApplicationDetailOut:
    applications_service.change_status(
        db, application_id=application_id, status=body.status, actor_id=user.id, owner_id=user.id
    )
    return _detail(db, application_id, user.id)


@router.post("/{application_id}/notes", status_code=201)
def add_note(application_id: int, body: NoteCreate, user: RecruiterUser, db: DbSession) -> NoteOut:
    note = notes_service.add_note(
        db, application_id=application_id, author_id=user.id, body=body.body, owner_id=user.id
    )
    return NoteOut(
        id=note.id,
        body=note.body,
        author_id=note.author_id,
        author_name=user.full_name,
        created_at=note.created_at,
    )


@router.post("/{application_id}/retry", status_code=202)
def retry_application(
    application_id: int,
    background_tasks: BackgroundTasks,
    user: RecruiterUser,
    db: DbSession,
    session_factory: SessionFactoryDep,
) -> QueuedApplications:
    applications_service.retry_application(
        db, application_id=application_id, actor_id=user.id, owner_id=user.id
    )
    background_tasks.add_task(pipeline.process_application, application_id, session_factory)
    return QueuedApplications(application_ids=[application_id])


@notes_router.delete("/{note_id}", status_code=204)
def delete_note(note_id: int, user: RecruiterUser, db: DbSession) -> None:
    notes_service.delete_note(db, note_id=note_id, actor_id=user.id, owner_id=user.id)
