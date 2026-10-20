from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, UTCDateTime, utc_now
from app.models.candidate import ProcessingStatus, enum_values
from app.models.job import EducationLevel, Job


class CVCheck(Base):
    """İş arayanın kendi CV'sini kendi girdiği iş kriterlerine göre değerlendirmesi.

    İşveren tablolarından (candidates/applications) bilinçli olarak ayrıdır: iş arayan verisi
    hiçbir işveren ekranında görünmemeli.
    """

    __tablename__ = "cv_checks"

    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(120))
    job_text: Mapped[str] = mapped_column(Text, default="")
    required_skills: Mapped[list[str]] = mapped_column(JSON, default=list)
    preferred_skills: Mapped[list[str]] = mapped_column(JSON, default=list)
    min_experience_years: Mapped[int] = mapped_column(default=0)
    min_education: Mapped[EducationLevel] = mapped_column(
        Enum(EducationLevel, native_enum=False, length=20, values_callable=enum_values),
        default=EducationLevel.NONE,
    )
    languages: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    original_filename: Mapped[str] = mapped_column(String(255))
    stored_path: Mapped[str] = mapped_column(String(100))
    file_hash: Mapped[str] = mapped_column(String(64))
    cv_text: Mapped[str] = mapped_column(Text, default="")
    parsed_data: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    parse_status: Mapped[ProcessingStatus] = mapped_column(
        Enum(ProcessingStatus, native_enum=False, length=20, values_callable=enum_values),
        default=ProcessingStatus.PENDING,
    )
    parse_error: Mapped[str | None] = mapped_column(String(255))
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
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utc_now, index=True)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utc_now, onupdate=utc_now)

    def criteria_job(self) -> Job:
        """Puanlama `Job` bekler; kriterler kaydedilmeyen bir ilan nesnesine kopyalanır."""
        return Job(
            title=self.title,
            required_skills=list(self.required_skills),
            preferred_skills=list(self.preferred_skills),
            min_experience_years=self.min_experience_years,
            min_education=self.min_education,
            languages=list(self.languages),
        )
