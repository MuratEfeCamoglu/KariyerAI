"""Eval betiğinin ve veri setinin çevrimdışı testleri; gerçek API çağrısı yapılmaz."""

import re
from typing import Any

import pytest

from app.llm.base import LLMError
from evals import run as evals_run


class _EchoLLM:
    """Beklenen becerileri aynen döndürür: recall'un %100 çıkması gerekir."""

    model_name = "echo"

    def __init__(self, skills_by_text: dict[str, list[str]]) -> None:
        self.skills_by_text = skills_by_text

    def parse_cv(self, cv_text: str) -> dict[str, Any]:
        return {"skills": self.skills_by_text[cv_text]}


class _BrokenLLM:
    model_name = "broken"

    def parse_cv(self, cv_text: str) -> dict[str, Any]:
        raise LLMError("bağlantı yok")


def test_dataset_has_ten_labelled_synthetic_cvs() -> None:
    cases = evals_run.load_cases()

    assert len(cases) == 10
    for case in cases:
        assert len(case.cv_text) >= 200, case.name
        assert case.expected_skills, case.name
        assert "@example.com" in case.cv_text, f"{case.name}: gerçek e-posta olmamalı"


def test_every_expected_skill_actually_appears_in_its_cv() -> None:
    # Etiket hatası (CV'de geçmeyen beceri) recall'u haksız yere düşürür.
    for case in evals_run.load_cases():
        missing = [s for s in case.expected_skills if not evals_run.skill_matches(s, case.cv_text)]
        assert not missing, f"{case.name}: {missing}"


@pytest.mark.parametrize(
    ("expected", "extracted", "matches"),
    [
        ("Python", "python", True),
        ("İngilizce", "INGILIZCE", True),
        ("A/B test", "A/B testleri", True),
        ("Spark", "Apache Spark", True),
        ("Java", "JavaScript", False),
        ("SQL", "PostgreSQL", False),
        ("React", "React Testing Library", True),
    ],
)
def test_skill_matching(expected: str, extracted: str, matches: bool) -> None:
    assert evals_run.skill_matches(expected, extracted) is matches


def test_perfect_extraction_scores_full_recall() -> None:
    cases = evals_run.load_cases()
    llm = _EchoLLM({case.cv_text: case.expected_skills for case in cases})

    report = evals_run.run(llm, cases)

    assert report.recall == 1.0
    assert not report.failures


def test_failed_parse_counts_all_skills_as_missed() -> None:
    cases = evals_run.load_cases()[:2]

    report = evals_run.run(_BrokenLLM(), cases)

    assert report.recall == 0.0
    assert len(report.failures) == 2


def test_p95_uses_nearest_rank() -> None:
    report = evals_run.EvalReport(
        cases=[
            evals_run.CaseResult(name=str(i), expected=1, seconds=float(i)) for i in range(1, 11)
        ]
    )

    assert report.p95_seconds == 10.0


def test_main_with_fake_provider_runs_offline_and_reports(
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code = evals_run.main(["--provider", "fake"])

    output = capsys.readouterr().out
    assert "Beceri recall'u" in output
    assert re.search(r"p95 süre\s+:", output)
    # Sahte istemci gerçek bir ayrıştırıcı değildir; hedefi tutturamaması beklenir.
    assert exit_code == 1
