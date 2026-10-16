from collections.abc import Iterable
from datetime import date
from typing import Any

import pytest
from pydantic import ValidationError

from app.llm.base import LLMError, LLMOutputError
from app.llm.fake_client import FakeLLMClient
from app.services import cv_parser
from app.services.cv_extract import FileKind, extract_text
from tests.conftest import FIXTURES

VALID: dict[str, Any] = {
    "full_name": "Test Kişi",
    "skills": ["SQL"],
    "experiences": [{"title": "Analist", "start": "2020-01", "end": "2020-12"}],
}


class _ScriptedLLM:
    """Her çağrıda sıradaki çıktıyı döner; istisna ise fırlatır."""

    model_name = "scripted"

    def __init__(self, outputs: Iterable[dict[str, Any] | Exception]) -> None:
        self.outputs = list(outputs)
        self.calls: list[str] = []

    def parse_cv(self, cv_text: str) -> dict[str, Any]:
        self.calls.append(cv_text)
        output = self.outputs.pop(0)
        if isinstance(output, Exception):
            raise output
        return output


def test_fake_client_parses_labelled_synthetic_cv() -> None:
    text = extract_text((FIXTURES / "cv_elif_kaya.docx").read_bytes(), FileKind.DOCX)

    parsed = cv_parser.parse_cv(text, FakeLLMClient())

    assert parsed.full_name == "Elif Kaya"
    assert parsed.email == "elif.kaya@example.com"
    assert parsed.phone == "+90 555 000 33 44"
    assert parsed.skills == ["SQL", "Python", "Power BI", "Excel"]
    assert [(lang.language, lang.level) for lang in parsed.languages] == [
        ("İngilizce", "B2"),
        ("Türkçe", "C2"),
    ]


def test_protected_attributes_are_dropped_from_llm_output() -> None:
    llm = _ScriptedLLM(
        [
            {
                **VALID,
                "age": 34,
                "gender": "kadın",
                "marital_status": "evli",
                "religion": "x",
                "nationality": "TR",
                "photo": "base64...",
                "birth_date": "1990-01-01",
            }
        ]
    )

    dumped = cv_parser.parse_cv("metin", llm).model_dump()

    for key in (
        "age",
        "gender",
        "marital_status",
        "religion",
        "nationality",
        "photo",
        "birth_date",
    ):
        assert key not in dumped


def test_invalid_output_is_retried_once_then_succeeds() -> None:
    llm = _ScriptedLLM([{"skills": "liste değil"}, VALID])

    parsed = cv_parser.parse_cv("metin", llm)

    assert parsed.skills == ["SQL"]
    assert len(llm.calls) == 2


@pytest.mark.parametrize(
    ("first", "second", "error"),
    [
        ({"skills": "liste değil"}, {"experiences": [{"start": "2020-13"}]}, ValidationError),
        (LLMOutputError("kesik"), LLMOutputError("kesik"), LLMOutputError),
    ],
)
def test_second_invalid_output_raises(
    first: dict[str, Any] | Exception,
    second: dict[str, Any] | Exception,
    error: type[Exception],
) -> None:
    llm = _ScriptedLLM([first, second])

    with pytest.raises(error):
        cv_parser.parse_cv("metin", llm)
    assert len(llm.calls) == 2


def test_truncated_output_is_retried() -> None:
    llm = _ScriptedLLM([LLMOutputError("kesik"), VALID])

    assert cv_parser.parse_cv("metin", llm).full_name == "Test Kişi"


def test_provider_errors_are_not_retried_here() -> None:
    # Ağ/sağlayıcı hatasını SDK zaten yeniden dener; burada ikinci çağrı yapılmaz.
    llm = _ScriptedLLM([LLMError("bağlantı yok"), VALID])

    with pytest.raises(LLMError):
        cv_parser.parse_cv("metin", llm)
    assert len(llm.calls) == 1


def test_experience_years_are_computed_in_code_not_taken_from_llm() -> None:
    llm = _ScriptedLLM([{**VALID, "total_experience_years": 25}])

    parsed = cv_parser.parse_cv("metin", llm, today=date(2026, 10, 16))

    assert parsed.total_experience_years == 1.0


def test_cv_text_is_truncated_before_sending_to_llm() -> None:
    llm = _ScriptedLLM([VALID])

    cv_parser.parse_cv("x" * (cv_parser.MAX_LLM_CHARS + 500), llm)

    assert len(llm.calls[0]) == cv_parser.MAX_LLM_CHARS
