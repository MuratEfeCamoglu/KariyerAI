from typing import Literal

from pydantic import BaseModel


class UploadFileResult(BaseModel):
    filename: str
    status: Literal["accepted", "rejected"]
    application_id: int | None = None
    # Reddedilen dosyanın kendi HTTP kodu (422 geçersiz, 409 tekrar) ve Türkçe nedeni.
    error_code: int | None = None
    detail: str | None = None


class UploadResponse(BaseModel):
    application_ids: list[int]
    files: list[UploadFileResult]
