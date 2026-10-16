from datetime import datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import JSON, Enum, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, UTCDateTime, utc_now
from app.models.candidate import ProcessingStatus, enum_values


class ApplicationStatus(StrEnum):
    NEW = "new"
    REVIEWING = "reviewing"
    SHORTLISTED = "shortlisted"
    INTERVIEW = "interview"
    HIRED = "hired"
    REJECTED = "rejected"


class Application(Base):
    __tablename__ = "applications"
    __table_args__ = (UniqueConstraint("job_id", "candidate_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id"), index=True)
    candidate_id: Mapped[int] = mapped_column(ForeignKey("candidates.id", ondelete="CASCADE"))
    status: Mapped[ApplicationStatus] = mapped_column(
        Enum(ApplicationStatus, native_enum=False, length=20, values_callable=enum_values),
        default=ApplicationStatus.NEW,
    )
    score: Mapped[int | None]
    score_breakdown: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    ai_summary: Mapped[str | None] = mapped_column(Text)
    score_status: Mapped[ProcessingStatus] = mapped_column(
        Enum(ProcessingStatus, native_enum=False, length=20, values_callable=enum_values),
        default=ProcessingStatus.PENDING,
    )
    score_error: Mapped[str | None] = mapped_column(String(255))
    llm_model: Mapped[str | None] = mapped_column(String(100))
    prompt_version: Mapped[str | None] = mapped_column(String(50))
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utc_now, onupdate=utc_now)
