from datetime import datetime

from pydantic import BaseModel

from app.models import ApplicationStatus, ProcessingStatus


class ItemPoints(BaseModel):
    """Liste satırındaki 5 kalem puanı (mini çubuklar); kırılımın özeti."""

    required_skills: float
    experience: float
    education: float
    languages: float
    preferred_skills: float


class ApplicationRowOut(BaseModel):
    id: int
    candidate_id: int
    candidate_name: str | None
    score: int | None
    item_points: ItemPoints | None
    last_position: str | None
    total_experience_years: float | None
    status: ApplicationStatus
    parse_status: ProcessingStatus
    parse_error: str | None
    score_status: ProcessingStatus
    score_error: str | None
    created_at: datetime


class ApplicationListOut(BaseModel):
    items: list[ApplicationRowOut]
    total: int
    page: int
    page_size: int
    # İlanda ayrıştırılan/puanlanan kayıt sayısı; 0 olunca arayüz otomatik yenilemeyi durdurur.
    processing_count: int


class QueuedApplications(BaseModel):
    application_ids: list[int]
