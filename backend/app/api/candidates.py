from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse

from app.core.deps import DbSession, RecruiterUser
from app.core.errors import NotFoundError
from app.services import candidates as candidates_service
from app.storage.files import FileStorage, get_storage

router = APIRouter(prefix="/candidates", tags=["candidates"])

_MEDIA_TYPES = {
    "pdf": "application/pdf",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}


@router.get("/{candidate_id}/cv")
def download_cv(
    candidate_id: int,
    user: RecruiterUser,
    db: DbSession,
    storage: Annotated[FileStorage, Depends(get_storage)],
) -> FileResponse:
    candidate = candidates_service.get_owned_candidate(db, candidate_id, owner_id=user.id)
    path = storage.path_for(candidate.stored_path)
    if not path.exists():
        raise NotFoundError("CV dosyası bulunamadı")
    extension = candidate.stored_path.rsplit(".", 1)[-1]
    # ISKELET §5: yalnızca oturumlu kullanıcıya, tarayıcıda açılmadan indirme olarak.
    return FileResponse(
        path,
        media_type=_MEDIA_TYPES[extension],
        filename=candidate.original_filename,
        content_disposition_type="attachment",
        headers={"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"},
    )


@router.delete("/{candidate_id}", status_code=204)
def delete_candidate(
    candidate_id: int,
    user: RecruiterUser,
    db: DbSession,
    storage: Annotated[FileStorage, Depends(get_storage)],
) -> None:
    candidates_service.delete_candidate(
        db, storage, candidate_id=candidate_id, actor_id=user.id, owner_id=user.id
    )
