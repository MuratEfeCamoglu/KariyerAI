from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse

from app.core.deps import CurrentUser, DbSession
from app.core.errors import NotFoundError
from app.models import Candidate
from app.storage.files import FileStorage, get_storage

router = APIRouter(prefix="/candidates", tags=["candidates"])

_MEDIA_TYPES = {
    "pdf": "application/pdf",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}


@router.get("/{candidate_id}/cv")
def download_cv(
    candidate_id: int,
    _user: CurrentUser,
    db: DbSession,
    storage: Annotated[FileStorage, Depends(get_storage)],
) -> FileResponse:
    candidate = db.get(Candidate, candidate_id)
    if candidate is None:
        raise NotFoundError("Aday bulunamadı")
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
