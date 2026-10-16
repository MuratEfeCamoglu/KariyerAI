from datetime import datetime
from typing import Annotated, Any, Literal

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
)

from app.models.job import EducationLevel, JobStatus
from app.services.text import fold

LanguageLevel = Literal["A1", "A2", "B1", "B2", "C1", "C2"]


class JobLanguage(BaseModel):
    language: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=50)]
    level: LanguageLevel


def _reject_duplicate_skills(skills: list[str]) -> list[str]:
    seen: set[str] = set()
    for skill in skills:
        key = fold(skill)
        if key in seen:
            raise ValueError(f"'{skill}' birden fazla kez eklenmiş")
        seen.add(key)
    return skills


def _reject_duplicate_languages(languages: list[JobLanguage]) -> list[JobLanguage]:
    seen: set[str] = set()
    for item in languages:
        key = fold(item.language)
        if key in seen:
            raise ValueError(f"'{item.language}' dili birden fazla kez eklenmiş")
        seen.add(key)
    return languages


SkillName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=50)]
Title = Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=120)]
Department = Annotated[str, StringConstraints(strip_whitespace=True, max_length=100)]
Description = Annotated[str, StringConstraints(max_length=5000)]
RequiredSkills = Annotated[
    list[SkillName], Field(min_length=1, max_length=20), AfterValidator(_reject_duplicate_skills)
]
PreferredSkills = Annotated[
    list[SkillName], Field(max_length=20), AfterValidator(_reject_duplicate_skills)
]
ExperienceYears = Annotated[int, Field(ge=0, le=40)]
Languages = Annotated[
    list[JobLanguage], Field(max_length=5), AfterValidator(_reject_duplicate_languages)
]


class JobCreate(BaseModel):
    title: Title
    department: Department = ""
    description: Description = ""
    required_skills: RequiredSkills
    preferred_skills: PreferredSkills = Field(default_factory=list)
    min_experience_years: ExperienceYears = 0
    min_education: EducationLevel = EducationLevel.NONE
    languages: Languages = Field(default_factory=list)
    status: JobStatus = JobStatus.OPEN


class JobUpdate(BaseModel):
    """Kısmi güncelleme: yalnızca gönderilen alanlar değişir."""

    title: Title | None = None
    department: Department | None = None
    description: Description | None = None
    required_skills: RequiredSkills | None = None
    preferred_skills: PreferredSkills | None = None
    min_experience_years: ExperienceYears | None = None
    min_education: EducationLevel | None = None
    languages: Languages | None = None
    status: JobStatus | None = None

    @field_validator("*", mode="before")
    @classmethod
    def _reject_explicit_null(cls, value: Any) -> Any:
        # Alanı göndermemek "değiştirme" demektir; açıkça null göndermek geçersizdir.
        if value is None:
            raise ValueError("Bu alan boş olamaz")
        return value


class JobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    department: str
    description: str
    required_skills: list[str]
    preferred_skills: list[str]
    min_experience_years: int
    min_education: EducationLevel
    languages: list[JobLanguage]
    status: JobStatus
    created_by: int
    created_at: datetime
    updated_at: datetime


class JobListItem(JobOut):
    application_count: int
    top_score: int | None
    avg_score: float | None
