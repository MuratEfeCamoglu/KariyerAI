from typing import Annotated, Any

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, UploadFile
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
from sqlalchemy.orm import Session, sessionmaker

from app.core.db import get_session_factory
from app.core.deps import DbSession, SeekerUser
from app.models import CVCheck
from app.schemas.cv_check import CVCheckCriteria, CVCheckListItem, CVCheckOut, QueuedCVCheck
from app.schemas.job import JobLanguage
from app.schemas.parsed_cv import ParsedCV
from app.schemas.scoring import ScoreBreakdown
from app.services import cv_checks as cv_checks_service
from app.services import pipeline
from app.services.candidates import IncomingFile
from app.services.cv_extract import MAX_FILE_BYTES
from app.services.cv_gaps import build_gaps
from app.storage.files import FileStorage, get_storage

router = APIRouter(prefix="/cv-checks", tags=["cv-checks"])

SessionFactoryDep = Annotated[sessionmaker[Session], Depends(get_session_factory)]
StorageDep = Annotated[FileStorage, Depends(get_storage)]


def _parse_criteria(raw: str) -> CVCheckCriteria:
    """Multipart istekte kriterler JSON metni olarak gelir; hatalar alan adlarıyla döner."""
    try:
        return CVCheckCriteria.model_validate_json(raw)
    except ValidationError as exc:
        errors: list[dict[str, Any]] = [
            {**error, "loc": ("body", *(error["loc"] or ("criteria",)))}
            for error in exc.errors(include_url=False, include_input=False)
        ]
        raise RequestValidationError(errors) from None


def _list_item(check: CVCheck) -> CVCheckListItem:
    return CVCheckListItem(
        id=check.id,
        title=check.title,
        original_filename=check.original_filename,
        score=check.score,
        parse_status=check.parse_status,
        score_status=check.score_status,
        created_at=check.created_at,
    )


def _detail(check: CVCheck) -> CVCheckOut:
    breakdown = (
        ScoreBreakdown.model_validate(check.score_breakdown) if check.score_breakdown else None
    )
    return CVCheckOut(
        **_list_item(check).model_dump(),
        job_text=check.job_text,
        required_skills=check.required_skills,
        preferred_skills=check.preferred_skills,
        min_experience_years=check.min_experience_years,
        min_education=check.min_education,
        languages=[JobLanguage.model_validate(item) for item in check.languages],
        parse_error=check.parse_error,
        score_error=check.score_error,
        parsed=ParsedCV.model_validate(check.parsed_data) if check.parsed_data else None,
        score_breakdown=breakdown,
        ai_summary=check.ai_summary,
        llm_model=check.llm_model,
        prompt_version=check.prompt_version,
        gaps=build_gaps(breakdown) if breakdown else [],
    )


@router.get("")
def list_checks(user: SeekerUser, db: DbSession) -> list[CVCheckListItem]:
    return [_list_item(check) for check in cv_checks_service.list_checks(db, user.id)]


@router.post("", status_code=202)
def create_check(
    criteria: Annotated[str, Form(description="Hedef iş kriterleri (JSON)")],
    file: Annotated[UploadFile, File(description="PDF/DOCX, ≤ 5 MB")],
    background_tasks: BackgroundTasks,
    user: SeekerUser,
    db: DbSession,
    storage: StorageDep,
    session_factory: SessionFactoryDep,
) -> CVCheckListItem:
    # Kriterler dosyadan önce doğrulanır: geçersiz istekte dosya diske hiç yazılmaz.
    parsed_criteria = _parse_criteria(criteria)
    incoming = IncomingFile(filename=file.filename or "", data=file.file.read(MAX_FILE_BYTES + 1))
    check = cv_checks_service.create_check(
        db, storage, owner_id=user.id, criteria=parsed_criteria, file=incoming
    )
    background_tasks.add_task(pipeline.process_cv_check, check.id, session_factory)
    return _list_item(check)


@router.get("/{check_id}")
def get_check(check_id: int, user: SeekerUser, db: DbSession) -> CVCheckOut:
    return _detail(cv_checks_service.get_check(db, check_id=check_id, owner_id=user.id))


@router.post("/{check_id}/retry", status_code=202)
def retry_check(
    check_id: int,
    background_tasks: BackgroundTasks,
    user: SeekerUser,
    db: DbSession,
    session_factory: SessionFactoryDep,
) -> QueuedCVCheck:
    cv_checks_service.retry_check(db, check_id=check_id, owner_id=user.id)
    background_tasks.add_task(pipeline.process_cv_check, check_id, session_factory)
    return QueuedCVCheck(id=check_id)


@router.delete("/{check_id}", status_code=204)
def delete_check(check_id: int, user: SeekerUser, db: DbSession, storage: StorageDep) -> None:
    cv_checks_service.delete_check(db, storage, check_id=check_id, owner_id=user.id)
