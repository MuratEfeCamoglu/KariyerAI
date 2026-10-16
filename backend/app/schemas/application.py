from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, StringConstraints

from app.models import ApplicationStatus, JobStatus, ProcessingStatus
from app.schemas.parsed_cv import ParsedCV
from app.schemas.scoring import ScoreBreakdown


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


class JobSummary(BaseModel):
    id: int
    title: str
    status: JobStatus


class CandidateOut(BaseModel):
    id: int
    full_name: str | None
    email: str | None
    phone: str | None
    original_filename: str
    parse_status: ProcessingStatus
    parse_error: str | None
    parsed: ParsedCV | None


class NoteOut(BaseModel):
    id: int
    body: str
    author_id: int
    author_name: str
    created_at: datetime


class NoteCreate(BaseModel):
    body: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=2000)]


class StatusUpdate(BaseModel):
    status: ApplicationStatus


class StatusChange(BaseModel):
    """F9 durum geçmişi; audit_logs'tan okunur (kim, ne zaman, eski → yeni)."""

    from_status: ApplicationStatus
    to_status: ApplicationStatus
    actor_id: int | None
    actor_name: str | None
    created_at: datetime


class ApplicationDetailOut(BaseModel):
    id: int
    job: JobSummary
    candidate: CandidateOut
    status: ApplicationStatus
    score: int | None
    score_breakdown: ScoreBreakdown | None
    ai_summary: str | None
    llm_model: str | None
    prompt_version: str | None
    score_status: ProcessingStatus
    score_error: str | None
    created_at: datetime
    updated_at: datetime
    notes: list[NoteOut]
    status_history: list[StatusChange]
