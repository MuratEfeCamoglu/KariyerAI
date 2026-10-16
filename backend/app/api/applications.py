from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy.orm import Session, sessionmaker

from app.core.db import get_session_factory
from app.core.deps import CurrentUser, DbSession
from app.schemas.application import QueuedApplications
from app.services import applications as applications_service
from app.services import pipeline

router = APIRouter(prefix="/applications", tags=["applications"])

SessionFactoryDep = Annotated[sessionmaker[Session], Depends(get_session_factory)]


@router.post("/{application_id}/retry", status_code=202)
def retry_application(
    application_id: int,
    background_tasks: BackgroundTasks,
    user: CurrentUser,
    db: DbSession,
    session_factory: SessionFactoryDep,
) -> QueuedApplications:
    applications_service.retry_application(db, application_id=application_id, actor_id=user.id)
    background_tasks.add_task(pipeline.process_application, application_id, session_factory)
    return QueuedApplications(application_ids=[application_id])
