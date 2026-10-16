"""F5d: CV ayrıştırma değerlendirmesi (beceri recall'u ve ayrıştırma süresi).

Gerçek API çağrısı yapar ve ücretlidir; CI'da çalışmaz, çalıştırmadan önce onay gerekir (AGENT.md).

    uv run python -m evals.run                    # LLM_MODEL ile, ANTHROPIC_API_KEY gerekir
    uv run python -m evals.run --provider gemini  # GEMINI_API_KEY ile (yalnızca sentetik veri)
    uv run python -m evals.run --provider fake    # yalnızca betiğin kendisini denemek için

Çıkış kodu: recall eşiğin altındaysa veya ayrıştırma başarısız olan CV varsa 1.
"""

import argparse
import json
import math
import re
import sys
import time
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path

from pydantic import ValidationError

from app.llm.base import LLMClient, LLMError
from app.llm.factory import PROVIDERS, get_llm_client
from app.services import cv_parser
from app.services.text import fold

CVS_DIR = Path(__file__).parent / "cvs"
RECALL_TARGET = 0.80  # ISKELET B2 / F5d
LATENCY_TARGET_SECONDS = 30.0  # F5c: tek CV ayrıştırma p95
# Türkçe ek toleransı: "A/B test" → "A/B testleri" eşleşir, "Java" → "JavaScript" eşleşmez.
MAX_SUFFIX_LETTERS = 4


@dataclass(frozen=True)
class EvalCase:
    name: str
    cv_text: str
    expected_skills: list[str]


@dataclass
class CaseResult:
    name: str
    expected: int
    matched: list[str] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)
    seconds: float = 0.0
    error: str | None = None

    @property
    def recall(self) -> float:
        return len(self.matched) / self.expected if self.expected else 1.0


@dataclass
class EvalReport:
    cases: list[CaseResult]

    @property
    def recall(self) -> float:
        """Tüm beklenen becerilerin micro recall'u; başarısız CV'nin becerileri kaçmış sayılır."""
        expected = sum(case.expected for case in self.cases)
        matched = sum(len(case.matched) for case in self.cases)
        return matched / expected if expected else 1.0

    @property
    def p95_seconds(self) -> float:
        durations = sorted(case.seconds for case in self.cases)
        if not durations:
            return 0.0
        return durations[max(0, math.ceil(0.95 * len(durations)) - 1)]

    @property
    def failures(self) -> list[CaseResult]:
        return [case for case in self.cases if case.error is not None]


def load_cases(directory: Path = CVS_DIR) -> list[EvalCase]:
    cases: list[EvalCase] = []
    for text_path in sorted(directory.glob("*.txt")):
        expected_path = text_path.with_suffix(".json")
        if not expected_path.exists():
            raise FileNotFoundError(f"Beklenen sonuç dosyası yok: {expected_path.name}")
        expected = json.loads(expected_path.read_text(encoding="utf-8"))
        cases.append(
            EvalCase(
                name=text_path.stem,
                cv_text=text_path.read_text(encoding="utf-8"),
                expected_skills=list(expected["skills"]),
            )
        )
    return cases


def skill_matches(expected: str, extracted: str) -> bool:
    needle = re.escape(fold(expected))
    pattern = rf"(?<!\w){needle}(?:\w{{0,{MAX_SUFFIX_LETTERS}}})(?!\w)"
    return re.search(pattern, fold(extracted)) is not None


def evaluate_case(case: EvalCase, llm: LLMClient) -> CaseResult:
    result = CaseResult(name=case.name, expected=len(case.expected_skills))
    started = time.perf_counter()
    try:
        parsed = cv_parser.parse_cv(case.cv_text, llm)
    except (LLMError, ValidationError) as exc:
        result.seconds = time.perf_counter() - started
        result.error = type(exc).__name__
        result.missing = list(case.expected_skills)
        return result
    result.seconds = time.perf_counter() - started
    for skill in case.expected_skills:
        if any(skill_matches(skill, extracted) for extracted in parsed.skills):
            result.matched.append(skill)
        else:
            result.missing.append(skill)
    return result


def run(llm: LLMClient, cases: Sequence[EvalCase]) -> EvalReport:
    return EvalReport(cases=[evaluate_case(case, llm) for case in cases])


def format_report(report: EvalReport, model: str) -> str:
    lines = [f"Model: {model}", ""]
    for case in report.cases:
        status = f"HATA ({case.error})" if case.error else f"{case.recall:6.1%}"
        lines.append(f"{case.name:<26} {status:>16}  {case.seconds:5.1f} sn")
        if case.missing and not case.error:
            lines.append(f"{'':<26} eksik: {', '.join(case.missing)}")
    lines += [
        "",
        f"Beceri recall'u : {report.recall:.1%} (hedef ≥ {RECALL_TARGET:.0%})",
        f"p95 süre        : {report.p95_seconds:.1f} sn (hedef ≤ {LATENCY_TARGET_SECONDS:.0f} sn)",
        f"Başarısız CV    : {len(report.failures)}",
    ]
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m evals.run", description=__doc__)
    parser.add_argument("--provider", choices=PROVIDERS, default="anthropic")
    args = parser.parse_args(argv)

    llm = get_llm_client(args.provider)
    report = run(llm, load_cases())
    print(format_report(report, llm.model_name))
    passed = report.recall >= RECALL_TARGET and not report.failures
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
