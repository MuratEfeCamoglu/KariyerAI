from fractions import Fraction
from typing import Any

import pytest

from app.models import EducationLevel, Job, JobStatus
from app.schemas.parsed_cv import CvLanguage, Education, ParsedCV
from app.schemas.scoring import CriterionJudgment
from app.services import scoring

CV_TEXT = """Deniz Arslan
deniz@example.com
Senior developer building Python and FastAPI services.
Maintained   PostgreSQL databases.
Languages: English (C1), German (A2)
"""


def _job(**overrides: Any) -> Job:
    values: dict[str, Any] = {
        "title": "Backend",
        "required_skills": ["Python"],
        "preferred_skills": [],
        "min_experience_years": 0,
        "min_education": EducationLevel.NONE,
        "languages": [],
        "status": JobStatus.OPEN,
        "created_by": 1,
        **overrides,
    }
    return Job(**values)


def _parsed(**overrides: Any) -> ParsedCV:
    return ParsedCV.model_validate({"full_name": "Deniz Arslan", **overrides})


def _met(criterion_id: str, evidence: str, level: str | None = None) -> CriterionJudgment:
    return CriterionJudgment(id=criterion_id, met=True, evidence=evidence, candidate_level=level)


def _score(job: Job, judgments: list[CriterionJudgment], parsed: ParsedCV | None = None) -> Any:
    return scoring.compute_score(job, parsed or _parsed(), judgments, CV_TEXT)


# --- Zorunlu beceriler (40) ---


@pytest.mark.parametrize(
    ("judgments", "points", "met"),
    [
        ([], 0.0, 0),
        ([_met("R1", "building Python and FastAPI services")], 13.3, 1),
        (
            [
                _met("R1", "building Python and FastAPI services"),
                _met("R2", "Python and FastAPI"),
                _met("R3", "Maintained PostgreSQL databases."),
            ],
            40.0,
            3,
        ),
    ],
)
def test_required_skills_boundaries(
    judgments: list[CriterionJudgment], points: float, met: int
) -> None:
    job = _job(required_skills=["Python", "FastAPI", "PostgreSQL"])

    component = _score(job, judgments).breakdown.required_skills

    assert (component.points, component.met, component.total) == (points, met, 3)


# --- Deneyim (25) ---


@pytest.mark.parametrize(
    ("min_years", "candidate_years", "expected"),
    [
        (0, 0.0, Fraction(25)),  # kriter yok → tam puan
        (4, 0.0, Fraction(0)),
        (4, 2.0, Fraction(25, 2)),
        (4, 4.0, Fraction(25)),
        (4, 9.5, Fraction(25)),  # üst sınır 25
    ],
)
def test_experience_points(min_years: int, candidate_years: float, expected: Fraction) -> None:
    assert scoring.experience_points(min_years, candidate_years) == expected


# --- Eğitim (15) ---


@pytest.mark.parametrize(
    ("required", "candidate", "expected"),
    [
        (EducationLevel.NONE, None, 15),
        (EducationLevel.BACHELOR, EducationLevel.BACHELOR, 15),
        (EducationLevel.BACHELOR, EducationLevel.PHD, 15),
        (EducationLevel.BACHELOR, EducationLevel.ASSOCIATE, 7),
        (EducationLevel.BACHELOR, EducationLevel.HIGH_SCHOOL, 0),
        (EducationLevel.BACHELOR, None, 0),
        (EducationLevel.HIGH_SCHOOL, None, 7),
    ],
)
def test_education_points(
    required: EducationLevel, candidate: EducationLevel | None, expected: int
) -> None:
    assert scoring.education_points(required, candidate) == expected


def test_candidate_education_is_highest_degree() -> None:
    parsed = _parsed(
        education=[
            Education(level=EducationLevel.MASTER).model_dump(),
            Education(level=EducationLevel.BACHELOR).model_dump(),
        ]
    )

    assert scoring.candidate_education(parsed) is EducationLevel.MASTER


# --- Diller (10) ---


def test_no_language_criteria_gives_full_points() -> None:
    assert _score(_job(), []).breakdown.languages.points == 10.0


@pytest.mark.parametrize(
    ("judgment", "met", "status"),
    [
        (_met("L1", "English (C1)", "C1"), True, "verified"),
        (_met("L1", "English (C1)", "C2"), True, "verified"),
        (_met("L1", "German (A2)", "A2"), False, "level_insufficient"),
        (_met("L1", "Languages: English", None), False, "level_unknown"),
        (CriterionJudgment(id="L1", met=False, evidence=None), False, "no_evidence"),
    ],
)
def test_language_level_rules(judgment: CriterionJudgment, met: bool, status: str) -> None:
    job = _job(languages=[{"language": "English", "level": "B2"}])

    [item] = _score(job, [judgment]).breakdown.languages.items

    assert (item.met, item.status) == (met, status)


def test_language_level_falls_back_to_parsed_cv() -> None:
    job = _job(languages=[{"language": "İngilizce", "level": "B2"}])
    parsed = _parsed(languages=[CvLanguage(language="ingilizce", level="C1").model_dump()])

    [item] = _score(job, [_met("L1", "English (C1)", None)], parsed).breakdown.languages.items

    assert item.met and item.candidate_level == "C1"


def test_partial_language_points() -> None:
    job = _job(
        languages=[{"language": "English", "level": "B2"}, {"language": "German", "level": "B1"}]
    )
    judgments = [_met("L1", "English (C1)", "C1"), _met("L2", "German (A2)", "A2")]

    assert _score(job, judgments).breakdown.languages.points == 5.0


# --- Tercih edilen beceriler (10) ---


@pytest.mark.parametrize(
    ("preferred", "judgments", "points"),
    [
        ([], [], 10.0),
        (["Docker", "Kubernetes"], [], 0.0),
        (["PostgreSQL", "FastAPI"], [_met("P1", "PostgreSQL"), _met("P2", "FastAPI")], 10.0),
    ],
)
def test_preferred_skills_boundaries(
    preferred: list[str], judgments: list[CriterionJudgment], points: float
) -> None:
    assert _score(
        _job(preferred_skills=preferred), judgments
    ).breakdown.preferred_skills.points == (points)


# --- Kanıt doğrulama (F6c, R1) ---


def test_evidence_matching_ignores_case_whitespace_and_quotes() -> None:
    assert scoring.verify_evidence('"maintained postgresql DATABASES."', CV_TEXT)
    assert scoring.verify_evidence("“Python and FastAPI”", CV_TEXT)


@pytest.mark.parametrize("evidence", ["Expert in Kubernetes", "", "   ", None])
def test_evidence_not_in_cv_is_not_verified(evidence: str | None) -> None:
    assert not scoring.verify_evidence(evidence, CV_TEXT)


def test_unverifiable_evidence_counts_as_not_met_and_is_not_shown() -> None:
    job = _job(required_skills=["Kubernetes"])

    [item] = _score(job, [_met("R1", "10 years of Kubernetes")]).breakdown.required_skills.items

    assert (item.met, item.status, item.evidence) == (False, "unverified", None)


def test_missing_llm_answer_counts_as_no_evidence() -> None:
    job = _job(required_skills=["Python", "Go"])

    breakdown = _score(job, [_met("R1", "Python")]).breakdown

    assert [i.status for i in breakdown.required_skills.items] == ["verified", "no_evidence"]


def test_met_without_evidence_counts_as_not_met() -> None:
    job = _job(required_skills=["Python"])

    [item] = _score(
        job, [CriterionJudgment(id="R1", met=True, evidence=None)]
    ).breakdown.required_skills.items

    assert (item.met, item.status) == (False, "no_evidence")


# --- Toplam ---


def test_total_is_rounded_half_up() -> None:
    # 20 (1/2 zorunlu) + 25 + 15 + 10 + 2.5 (1/4 tercih edilen) = 72.5 → 73
    job = _job(required_skills=["Python", "Go"], preferred_skills=["FastAPI", "A", "B", "C"])

    outcome = _score(job, [_met("R1", "Python"), _met("P1", "FastAPI")])

    assert outcome.score == 73


def test_all_criteria_met_gives_100_and_none_met_gives_minimum() -> None:
    job = _job(
        required_skills=["Python"],
        preferred_skills=["FastAPI"],
        min_experience_years=3,
        min_education=EducationLevel.BACHELOR,
        languages=[{"language": "English", "level": "B2"}],
    )
    strong = _parsed(
        total_experience_years=6.0,
        education=[Education(level=EducationLevel.MASTER).model_dump()],
    )
    judgments = [_met("R1", "Python"), _met("P1", "FastAPI"), _met("L1", "English (C1)", "C1")]

    assert _score(job, judgments, strong).score == 100
    assert _score(job, [], _parsed()).score == 0


def test_breakdown_keeps_records_used_for_experience_and_education() -> None:
    parsed = _parsed(
        experiences=[
            {"title": "Developer", "company": "Örnek", "start": "2020-01", "end": "present"}
        ],
        education=[{"level": "bachelor", "school": "Örnek Üniversitesi", "field": "Bilgisayar"}],
        total_experience_years=2.0,
    )

    breakdown = _score(_job(min_experience_years=4), [], parsed).breakdown

    assert breakdown.experience.records[0].title == "Developer"
    assert breakdown.experience.points == 12.5
    assert breakdown.education.records[0].school == "Örnek Üniversitesi"


# --- evaluate: anonimleştirme, yeniden deneme, LLM sayısı yok sayılır ---


class _ScriptedLLM:
    model_name = "scripted"

    def __init__(self, outputs: list[dict[str, Any]]) -> None:
        self.outputs = outputs
        self.received: list[str] = []

    def parse_cv(self, cv_text: str) -> dict[str, Any]:
        raise AssertionError("kullanılmaz")

    def score_cv(
        self, anonymized_cv: str, criteria: list[dict[str, str]], profile: dict[str, Any]
    ) -> dict[str, Any]:
        self.received.append(anonymized_cv)
        return self.outputs.pop(0)


def test_evaluate_sends_anonymized_text_and_ignores_llm_numbers() -> None:
    llm = _ScriptedLLM(
        [
            {
                "criteria": [{"id": "R1", "met": True, "evidence": "Python and FastAPI"}],
                "summary": "Python kanıtı var.",
                "score": 3,
            }
        ]
    )

    evaluation = scoring.evaluate(_job(), _parsed(), CV_TEXT, llm)

    assert evaluation.score == 100
    assert "Deniz" not in llm.received[0] and "deniz@example.com" not in llm.received[0]
    assert (evaluation.model, evaluation.prompt_version) == ("scripted", "score_v1")


def test_evaluate_retries_invalid_output_once() -> None:
    llm = _ScriptedLLM(
        [
            {"criteria": "liste değil", "summary": "x"},
            {"criteria": [], "summary": "Kanıt yok."},
        ]
    )

    evaluation = scoring.evaluate(_job(), _parsed(), CV_TEXT, llm)

    assert len(llm.received) == 2
    assert evaluation.summary == "Kanıt yok."
