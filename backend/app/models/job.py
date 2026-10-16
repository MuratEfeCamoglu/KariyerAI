from datetime import datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import JSON, Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, UTCDateTime, utc_now


class EducationLevel(StrEnum):
    """Sıralama önemlidir: puanlamada (§3.5) seviyeler bu sırayla karşılaştırılır."""

    NONE = "none"
    HIGH_SCHOOL = "high_school"
    ASSOCIATE = "associate"
    BACHELOR = "bachelor"
    MASTER = "master"
    PHD = "phd"


class JobStatus(StrEnum):
    OPEN = "open"
    CLOSED = "closed"


def _enum_values(enum_cls: type[StrEnum]) -> list[str]:
    return [member.value for member in enum_cls]


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(120))
    department: Mapped[str] = mapped_column(String(100), default="")
    description: Mapped[str] = mapped_column(Text, default="")
    required_skills: Mapped[list[str]] = mapped_column(JSON, default=list)
    preferred_skills: Mapped[list[str]] = mapped_column(JSON, default=list)
    min_experience_years: Mapped[int] = mapped_column(default=0)
    min_education: Mapped[EducationLevel] = mapped_column(
        Enum(EducationLevel, native_enum=False, length=20, values_callable=_enum_values),
        default=EducationLevel.NONE,
    )
    languages: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    status: Mapped[JobStatus] = mapped_column(
        Enum(JobStatus, native_enum=False, length=10, values_callable=_enum_values),
        default=JobStatus.OPEN,
    )
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utc_now, onupdate=utc_now)
