from datetime import datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import JSON, Enum, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, UTCDateTime, utc_now


class ProcessingStatus(StrEnum):
    """Hem ayrıştırma (`parse_status`) hem puanlama (`score_status`) için ortak durumlar."""

    PENDING = "pending"
    PROCESSING = "processing"
    DONE = "done"
    FAILED = "failed"


def enum_values(enum_cls: type[StrEnum]) -> list[str]:
    return [member.value for member in enum_cls]


class Candidate(Base):
    __tablename__ = "candidates"

    id: Mapped[int] = mapped_column(primary_key=True)
    # Ad/e-posta/telefon ayrıştırma sonrası ParsedCV'den dolar; yalnızca gösterim içindir.
    full_name: Mapped[str | None] = mapped_column(String(200))
    email: Mapped[str | None] = mapped_column(String(254))
    phone: Mapped[str | None] = mapped_column(String(50))
    original_filename: Mapped[str] = mapped_column(String(255))
    stored_path: Mapped[str] = mapped_column(String(100))
    file_hash: Mapped[str] = mapped_column(String(64), index=True)
    cv_text: Mapped[str] = mapped_column(Text, default="")
    parsed_data: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    parse_status: Mapped[ProcessingStatus] = mapped_column(
        Enum(ProcessingStatus, native_enum=False, length=20, values_callable=enum_values),
        default=ProcessingStatus.PENDING,
    )
    parse_error: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utc_now)
