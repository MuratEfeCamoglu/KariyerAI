"""Uyum puanı — ISKELET §3.5. Puan sayısı yalnızca burada, deterministik formülle üretilir.

LLM yalnızca beceri/dil kriterleri için "karşılıyor mu + kanıt" döner; deneyim ve eğitim LLM'e
sorulmaz. Kanıt, LLM'e gönderilen anonim metinde aranır; bulunamazsa kalem karşılanmamış sayılır.
"""

import logging
import math
from dataclasses import dataclass
from fractions import Fraction
from typing import Any, Literal

from pydantic import ValidationError

from app.llm.base import SCORE_PROMPT_VERSION, LLMClient, LLMOutputError
from app.models.job import EducationLevel, Job
from app.schemas.parsed_cv import ParsedCV
from app.schemas.scoring import (
    CriterionJudgment,
    CriterionResult,
    EducationComponent,
    EducationRecord,
    ExperienceComponent,
    ExperienceRecord,
    ListComponent,
    ScoreBreakdown,
    ScoreLLMOutput,
)
from app.services.anonymizer import anonymize
from app.services.text import fold

logger = logging.getLogger(__name__)

WEIGHTS = {
    "required_skills": 40,
    "experience": 25,
    "education": 15,
    "languages": 10,
    "preferred_skills": 10,
}
EDUCATION_ORDER = list(EducationLevel)
CEFR_ORDER = ["A1", "A2", "B1", "B2", "C1", "C2"]
MAX_ATTEMPTS = 2  # Geçersiz çıktıda 1 yeniden deneme (ayrıştırmayla aynı kural, F5a).

CriterionKind = Literal["required_skill", "preferred_skill", "language"]


@dataclass(frozen=True)
class Criterion:
    id: str
    kind: CriterionKind
    label: str
    required_level: str | None = None

    def payload(self) -> dict[str, str]:
        data = {"id": self.id, "kind": self.kind, "label": self.label}
        if self.required_level is not None:
            data["required_level"] = self.required_level
        return data


@dataclass(frozen=True)
class ScoreOutcome:
    score: int
    breakdown: ScoreBreakdown


@dataclass(frozen=True)
class ScoreEvaluation:
    score: int
    breakdown: ScoreBreakdown
    summary: str
    model: str
    prompt_version: str


def build_criteria(job: Job) -> list[Criterion]:
    """Kriterlere kısa id'ler verilir; LLM cevabı ada değil id'ye göre eşlenir."""
    criteria = [
        Criterion(f"R{i}", "required_skill", skill)
        for i, skill in enumerate(job.required_skills, start=1)
    ]
    criteria += [
        Criterion(f"P{i}", "preferred_skill", skill)
        for i, skill in enumerate(job.preferred_skills, start=1)
    ]
    criteria += [
        Criterion(f"L{i}", "language", str(item["language"]), str(item["level"]))
        for i, item in enumerate(job.languages, start=1)
    ]
    return criteria


def _strip_quotes(text: str) -> str:
    return text.strip().strip("\"'“”‘’«»").strip()


def verify_evidence(evidence: str | None, anonymized_text: str) -> bool:
    """F6c: alıntı, büyük/küçük harf ve boşluklar normalize edilerek birebir aranır."""
    if evidence is None:
        return False
    quote = fold(_strip_quotes(evidence))
    return bool(quote) and quote in fold(anonymized_text)


def _parsed_level(parsed: ParsedCV, language: str) -> str | None:
    for item in parsed.languages:
        if fold(item.language) == fold(language):
            return item.level
    return None


def _judge(
    criterion: Criterion,
    judgment: CriterionJudgment | None,
    anonymized_text: str,
    parsed: ParsedCV,
) -> CriterionResult:
    base: dict[str, Any] = {
        "criterion": criterion.label,
        "required_level": criterion.required_level,
    }
    if judgment is None or not judgment.met or not judgment.evidence:
        return CriterionResult(**base, met=False, status="no_evidence")
    if not verify_evidence(judgment.evidence, anonymized_text):
        # Doğrulanamayan alıntı gösterilmez: CV'de olmayan bir metin kanıt gibi görünmesin.
        return CriterionResult(**base, met=False, status="unverified")
    evidence = _strip_quotes(judgment.evidence)
    if criterion.kind != "language":
        return CriterionResult(**base, met=True, status="verified", evidence=evidence)

    level = judgment.candidate_level or _parsed_level(parsed, criterion.label)
    if level is None:
        return CriterionResult(**base, met=False, status="level_unknown", evidence=evidence)
    assert criterion.required_level is not None
    if CEFR_ORDER.index(level) < CEFR_ORDER.index(criterion.required_level):
        return CriterionResult(
            **base,
            met=False,
            status="level_insufficient",
            evidence=evidence,
            candidate_level=level,
        )
    return CriterionResult(
        **base, met=True, status="verified", evidence=evidence, candidate_level=level
    )


def _ratio_points(weight: int, results: list[CriterionResult]) -> Fraction:
    # Kriter yoksa kalemin tamamı verilir (§3.5).
    if not results:
        return Fraction(weight)
    return Fraction(weight) * Fraction(sum(r.met for r in results), len(results))


def experience_points(min_years: int, candidate_years: float) -> Fraction:
    weight = WEIGHTS["experience"]
    if min_years == 0:
        return Fraction(weight)
    ratio = min(Fraction(1), Fraction(str(candidate_years)) / min_years)
    return Fraction(weight) * ratio


def candidate_education(parsed: ParsedCV) -> EducationLevel | None:
    if not parsed.education:
        return None
    return max((item.level for item in parsed.education), key=EDUCATION_ORDER.index)


def education_points(required: EducationLevel, candidate: EducationLevel | None) -> Fraction:
    if required is EducationLevel.NONE:
        return Fraction(WEIGHTS["education"])
    gap = EDUCATION_ORDER.index(required) - EDUCATION_ORDER.index(candidate or EducationLevel.NONE)
    if gap <= 0:
        return Fraction(WEIGHTS["education"])
    if gap == 1:
        return Fraction(7)
    return Fraction(0)


def round_half_up(value: Fraction) -> int:
    # round() bankacı yuvarlaması yapar (74.5 → 74); puan için 0.5 her zaman yukarı yuvarlanır.
    return math.floor(value + Fraction(1, 2))


def _display(points: Fraction) -> float:
    return round(float(points), 1)


def _list_component(key: str, results: list[CriterionResult]) -> tuple[Fraction, ListComponent]:
    points = _ratio_points(WEIGHTS[key], results)
    component = ListComponent(
        weight=WEIGHTS[key],
        points=_display(points),
        met=sum(r.met for r in results),
        total=len(results),
        items=results,
    )
    return points, component


def compute_score(
    job: Job,
    parsed: ParsedCV,
    judgments: list[CriterionJudgment],
    anonymized_text: str,
) -> ScoreOutcome:
    criteria = build_criteria(job)
    by_id = {judgment.id: judgment for judgment in judgments}
    results = {
        criterion.id: _judge(criterion, by_id.get(criterion.id), anonymized_text, parsed)
        for criterion in criteria
    }

    def results_of(kind: CriterionKind) -> list[CriterionResult]:
        return [results[c.id] for c in criteria if c.kind == kind]

    required_pts, required = _list_component("required_skills", results_of("required_skill"))
    preferred_pts, preferred = _list_component("preferred_skills", results_of("preferred_skill"))
    language_pts, languages = _list_component("languages", results_of("language"))

    experience_pts = experience_points(job.min_experience_years, parsed.total_experience_years)
    experience = ExperienceComponent(
        weight=WEIGHTS["experience"],
        points=_display(experience_pts),
        required_years=job.min_experience_years,
        candidate_years=parsed.total_experience_years,
        records=[
            ExperienceRecord(title=e.title, company=e.company, start=e.start, end=e.end)
            for e in parsed.experiences
        ],
    )

    candidate_level = candidate_education(parsed)
    education_pts = education_points(job.min_education, candidate_level)
    education = EducationComponent(
        weight=WEIGHTS["education"],
        points=_display(education_pts),
        required=job.min_education,
        candidate=candidate_level,
        records=[
            EducationRecord(level=e.level, field=e.field, school=e.school, end_year=e.end_year)
            for e in parsed.education
        ],
    )

    total = required_pts + experience_pts + education_pts + language_pts + preferred_pts
    return ScoreOutcome(
        score=round_half_up(total),
        breakdown=ScoreBreakdown(
            required_skills=required,
            experience=experience,
            education=education,
            languages=languages,
            preferred_skills=preferred,
        ),
    )


def evaluate(job: Job, parsed: ParsedCV, cv_text: str, llm: LLMClient) -> ScoreEvaluation:
    """Anonimleştirir, LLM'den kriter cevaplarını alır ve puanı formülle hesaplar."""
    anonymized = anonymize(cv_text, parsed.full_name)
    criteria = build_criteria(job)
    profile = {
        "skills": parsed.skills,
        "languages": [item.model_dump() for item in parsed.languages],
    }
    output: ScoreLLMOutput | None = None
    last_error: ValidationError | LLMOutputError | None = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            raw = llm.score_cv(anonymized, [c.payload() for c in criteria], profile)
            output = ScoreLLMOutput.model_validate(raw)
            break
        except (ValidationError, LLMOutputError) as exc:
            last_error = exc
            logger.info("Puanlama çıktısı geçersiz (deneme %s): %s", attempt, type(exc).__name__)
    if output is None:
        assert last_error is not None
        raise last_error

    outcome = compute_score(job, parsed, output.criteria, anonymized)
    return ScoreEvaluation(
        score=outcome.score,
        breakdown=outcome.breakdown,
        summary=output.summary,
        model=llm.model_name,
        prompt_version=SCORE_PROMPT_VERSION,
    )
