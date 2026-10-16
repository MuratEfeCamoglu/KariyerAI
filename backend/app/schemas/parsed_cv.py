from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from app.models.job import EducationLevel
from app.schemas.job import LanguageLevel

YearMonth = Annotated[str, StringConstraints(pattern=r"^\d{4}-(0[1-9]|1[0-2])$")]


class _Strict(BaseModel):
    # Şemada olmayan alanlar (yaş, cinsiyet, medeni hal, din, uyruk, fotoğraf vb.) LLM döndürse
    # bile sessizce atılır; hiçbir zaman saklanmaz (F5b).
    model_config = ConfigDict(extra="ignore")


class Experience(_Strict):
    title: str
    company: str | None = None
    start: YearMonth | None = None
    end: YearMonth | Literal["present"] | None = None
    description: str | None = None


class Education(_Strict):
    level: EducationLevel
    field: str | None = None
    school: str | None = None
    end_year: int | None = None


class CvLanguage(_Strict):
    language: str
    level: LanguageLevel | None = None


class ParsedCV(_Strict):
    """ISKELET.md §3.4 ayrıştırma çıktısı."""

    full_name: str | None = None
    email: str | None = None
    phone: str | None = None
    summary: str | None = None
    skills: list[str] = Field(default_factory=list)
    experiences: list[Experience] = Field(default_factory=list)
    education: list[Education] = Field(default_factory=list)
    languages: list[CvLanguage] = Field(default_factory=list)
    # LLM'den alınmaz; deneyim tarihlerinden kodda hesaplanır (Aşama 4).
    total_experience_years: float = 0.0
