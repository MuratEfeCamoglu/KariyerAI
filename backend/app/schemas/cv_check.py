from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.models import EducationLevel, ProcessingStatus
from app.schemas.job import (
    Description,
    ExperienceYears,
    JobLanguage,
    Languages,
    PreferredSkills,
    RequiredSkills,
    Title,
)
from app.schemas.parsed_cv import ParsedCV
from app.schemas.scoring import ScoreBreakdown


class CVCheckCriteria(BaseModel):
    """İş arayanın girdiği hedef iş; alanlar ve sınırlar ilan formuyla (F3) aynı."""

    title: Title
    job_text: Description = ""
    required_skills: RequiredSkills
    preferred_skills: PreferredSkills = Field(default_factory=list)
    min_experience_years: ExperienceYears = 0
    min_education: EducationLevel = EducationLevel.NONE
    languages: Languages = Field(default_factory=list)


GapKind = Literal["required_skill", "experience", "education", "language", "preferred_skill"]


class Gap(BaseModel):
    kind: GapKind
    criterion: str
    status: str
    message: str


class CVCheckListItem(BaseModel):
    id: int
    title: str
    original_filename: str
    score: int | None
    parse_status: ProcessingStatus
    score_status: ProcessingStatus
    created_at: datetime


class CVCheckOut(CVCheckListItem):
    job_text: str
    required_skills: list[str]
    preferred_skills: list[str]
    min_experience_years: int
    min_education: EducationLevel
    languages: list[JobLanguage]
    parse_error: str | None
    score_error: str | None
    parsed: ParsedCV | None
    score_breakdown: ScoreBreakdown | None
    ai_summary: str | None
    llm_model: str | None
    prompt_version: str | None
    gaps: list[Gap]


class QueuedCVCheck(BaseModel):
    id: int
