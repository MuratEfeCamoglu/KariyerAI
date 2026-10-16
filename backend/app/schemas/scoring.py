from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from app.models.job import EducationLevel
from app.schemas.job import LanguageLevel


class CriterionJudgment(BaseModel):
    """LLM'in tek bir kriter için cevabı. Sayı içermez (F6b)."""

    model_config = ConfigDict(extra="ignore")

    id: str
    met: bool
    evidence: str | None = None
    candidate_level: LanguageLevel | None = None


class ScoreLLMOutput(BaseModel):
    model_config = ConfigDict(extra="ignore")

    criteria: list[CriterionJudgment] = Field(default_factory=list)
    summary: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=2000)]


# ISKELET B3, §3.5 kalem durumları:
# verified: kanıt CV'de bulundu · no_evidence: "Kanıt bulunamadı"
# unverified: "Kanıt doğrulanamadı" · level_unknown: CV'de dil seviyesi yok
# level_insufficient: dil seviyesi istenenden düşük
EvidenceStatus = Literal[
    "verified", "no_evidence", "unverified", "level_unknown", "level_insufficient"
]


class CriterionResult(BaseModel):
    criterion: str
    met: bool
    status: EvidenceStatus
    evidence: str | None = None
    required_level: LanguageLevel | None = None
    candidate_level: LanguageLevel | None = None


class ListComponent(BaseModel):
    weight: int
    points: float
    met: int
    total: int
    items: list[CriterionResult]


class ExperienceRecord(BaseModel):
    title: str
    company: str | None = None
    start: str | None = None
    end: str | None = None


class ExperienceComponent(BaseModel):
    weight: int
    points: float
    required_years: int
    candidate_years: float
    records: list[ExperienceRecord]


class EducationRecord(BaseModel):
    level: EducationLevel
    field: str | None = None
    school: str | None = None
    end_year: int | None = None


class EducationComponent(BaseModel):
    weight: int
    points: float
    required: EducationLevel
    candidate: EducationLevel | None
    records: list[EducationRecord]


class ScoreBreakdown(BaseModel):
    """`applications.score_breakdown` içeriği; F8 kırılımı bu yapıdan çizilir."""

    required_skills: ListComponent
    experience: ExperienceComponent
    education: EducationComponent
    languages: ListComponent
    preferred_skills: ListComponent


ComponentKey = Literal[
    "required_skills", "experience", "education", "languages", "preferred_skills"
]
