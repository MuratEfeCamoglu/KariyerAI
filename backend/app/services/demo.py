"""Demo ve performans verisi (ISKELET §6 Aşama 7, F7c).

Tüm kişiler uydurmadır (V13); e-postalar example.com, telefonlar 555 000 aralığındadır.
LLM çağrısı yapılmaz: ayrıştırılmış CV veriden kurulur, puanlama FakeLLMClient + gerçek
formülle (scoring.evaluate) yapılır. Aynı tohumla her çalıştırma aynı veriyi üretir.
"""

import hashlib
import io
import random
from dataclasses import dataclass
from datetime import date

import docx
from sqlalchemy.orm import Session

from app.llm.fake_client import FakeLLMClient
from app.models import (
    Application,
    ApplicationStatus,
    Candidate,
    EducationLevel,
    Job,
    JobStatus,
    ProcessingStatus,
)
from app.schemas.parsed_cv import CvLanguage, Education, Experience, ParsedCV
from app.services import scoring
from app.services.experience import total_experience_years
from app.storage.files import FileStorage

DEMO_JOB = {
    "title": "Kıdemli Backend Geliştirici (Demo)",
    "department": "Teknoloji",
    "description": "Ödeme altyapısı ekibi için demo ilanı. Tüm adaylar sentetiktir.",
    "required_skills": ["Python", "FastAPI", "PostgreSQL", "Docker"],
    "preferred_skills": ["Kubernetes", "Redis", "AWS"],
    "min_experience_years": 3,
    "min_education": EducationLevel.BACHELOR,
    "languages": [{"language": "İngilizce", "level": "B2"}],
}

_FIRST_NAMES = [
    "Ada", "Bora", "Cansu", "Deniz", "Ece", "Emre", "Gizem", "Hakan", "İpek", "Kerem",
    "Lale", "Mert", "Nil", "Onur", "Pelin", "Rüzgar", "Selin", "Tolga", "Umut", "Yasemin",
]  # fmt: skip
_LAST_NAMES = [
    "Akın", "Bulut", "Çelik", "Demir", "Erdem", "Güneş", "Işık", "Kaya", "Kurt", "Özkan",
    "Polat", "Sarı", "Tekin", "Uslu", "Yalçın", "Yıldız",
]  # fmt: skip
_SKILLS = [
    "Python", "FastAPI", "PostgreSQL", "Docker", "Kubernetes", "Redis", "AWS", "Django",
    "Go", "Java", "React", "Terraform", "RabbitMQ", "MongoDB", "Linux", "Git",
]  # fmt: skip
_TITLES = ["Backend Developer", "Software Engineer", "Yazılım Geliştirici", "Platform Engineer"]
_COMPANIES = ["Örnek Teknoloji A.Ş.", "Deneme Yazılım Ltd.", "Sample Labs", "Placeholder Inc."]
_EDUCATION = [
    EducationLevel.HIGH_SCHOOL,
    EducationLevel.ASSOCIATE,
    EducationLevel.BACHELOR,
    EducationLevel.BACHELOR,
    EducationLevel.MASTER,
]
_LEVELS = ["A2", "B1", "B2", "C1", "C2"]
_STATUSES = [ApplicationStatus.NEW] * 6 + [
    ApplicationStatus.REVIEWING,
    ApplicationStatus.SHORTLISTED,
    ApplicationStatus.INTERVIEW,
    ApplicationStatus.REJECTED,
]
_EDUCATION_TR = {
    EducationLevel.HIGH_SCHOOL: "Lise",
    EducationLevel.ASSOCIATE: "Ön Lisans",
    EducationLevel.BACHELOR: "Lisans",
    EducationLevel.MASTER: "Yüksek Lisans",
}


@dataclass(frozen=True)
class SyntheticCv:
    filename: str
    text: str
    parsed: ParsedCV


@dataclass(frozen=True)
class SeedResult:
    job_id: int
    application_count: int


def _year_month(year: int, month: int) -> str:
    return f"{year:04d}-{month:02d}"


def synthetic_cv(rng: random.Random, index: int, today: date) -> SyntheticCv:
    name = f"{rng.choice(_FIRST_NAMES)} {rng.choice(_LAST_NAMES)}"
    email = f"aday{index:04d}@example.com"
    phone = f"+90 555 000 {index // 100 % 100:02d} {index % 100:02d}"
    skills = rng.sample(_SKILLS, rng.randint(3, 9))

    experiences: list[Experience] = []
    year = today.year - rng.randint(0, 2)
    for position in range(rng.randint(1, 3)):
        start_year = year - rng.randint(1, 4)
        experiences.append(
            Experience(
                title=rng.choice(_TITLES),
                company=rng.choice(_COMPANIES),
                start=_year_month(start_year, rng.randint(1, 12)),
                end="present" if position == 0 and rng.random() < 0.6 else _year_month(year, 6),
                description=f"{', '.join(rng.sample(skills, 3))} ile servisler geliştirdi.",
            )
        )
        year = start_year - rng.randint(0, 1)

    education_level = rng.choice(_EDUCATION)
    language_level = rng.choice(_LEVELS)
    parsed = ParsedCV(
        full_name=name,
        email=email,
        phone=phone,
        summary="Sentetik demo adayı.",
        skills=skills,
        experiences=experiences,
        education=[
            Education(
                level=education_level, field="Bilgisayar Mühendisliği", school="Örnek Üniversitesi"
            )
        ],
        languages=[CvLanguage.model_validate({"language": "İngilizce", "level": language_level})],
    )
    parsed.total_experience_years = total_experience_years(experiences, today)

    lines = [name, f"{email} · {phone}", "", "Deneyim"]
    for item in experiences:
        end = "halen" if item.end == "present" else item.end
        lines.append(f"{item.title}, {item.company} ({item.start} – {end})")
        lines.append(item.description or "")
    lines += [
        "",
        f"Eğitim: Bilgisayar Mühendisliği {_EDUCATION_TR[education_level]}, Örnek Üniversitesi",
        f"Beceriler: {', '.join(skills)}",
        f"Diller: İngilizce ({language_level})",
    ]
    return SyntheticCv(filename=f"demo_cv_{index:04d}.docx", text="\n".join(lines), parsed=parsed)


def docx_bytes(text: str) -> bytes:
    document = docx.Document()
    for line in text.splitlines():
        document.add_paragraph(line)
    buffer = io.BytesIO()
    document.save(buffer)
    return buffer.getvalue()


def seed_demo(
    db: Session,
    storage: FileStorage,
    *,
    owner_id: int,
    applications: int,
    seed: int = 42,
    today: date | None = None,
) -> SeedResult:
    rng = random.Random(seed)
    today = today or date.today()
    job = Job(**DEMO_JOB, status=JobStatus.OPEN, created_by=owner_id)
    db.add(job)
    db.flush()

    llm = FakeLLMClient()
    for index in range(1, applications + 1):
        cv = synthetic_cv(rng, index, today)
        data = docx_bytes(cv.text)
        evaluation = scoring.evaluate(job, cv.parsed, cv.text, llm)
        candidate = Candidate(
            full_name=cv.parsed.full_name,
            email=cv.parsed.email,
            phone=cv.parsed.phone,
            original_filename=cv.filename,
            stored_path=storage.save(data, "docx"),
            file_hash=hashlib.sha256(data).hexdigest(),
            cv_text=cv.text,
            parsed_data=cv.parsed.model_dump(mode="json"),
            parse_status=ProcessingStatus.DONE,
        )
        db.add(candidate)
        db.flush()
        db.add(
            Application(
                job_id=job.id,
                candidate_id=candidate.id,
                status=rng.choice(_STATUSES),
                score=evaluation.score,
                score_breakdown=evaluation.breakdown.model_dump(mode="json"),
                ai_summary=evaluation.summary,
                llm_model=evaluation.model,
                prompt_version=evaluation.prompt_version,
                score_status=ProcessingStatus.DONE,
            )
        )
        if index % 100 == 0:
            db.flush()
    db.commit()
    return SeedResult(job_id=job.id, application_count=applications)
