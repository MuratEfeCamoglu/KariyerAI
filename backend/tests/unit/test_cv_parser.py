from typing import Any

import pytest
from pydantic import ValidationError

from app.llm.fake_client import FakeLLMClient
from app.services import cv_parser
from app.services.cv_extract import FileKind, extract_text
from tests.conftest import FIXTURES


class _StubLLM:
    model_name = "stub"

    def __init__(self, output: dict[str, Any]) -> None:
        self.output = output
        self.received: str | None = None

    def parse_cv(self, cv_text: str) -> dict[str, Any]:
        self.received = cv_text
        return self.output


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
    llm = _StubLLM(
        {
            "full_name": "Test Kişi",
            "skills": ["SQL"],
            "age": 34,
            "gender": "kadın",
            "marital_status": "evli",
            "religion": "x",
            "nationality": "TR",
            "photo": "base64...",
            "birth_date": "1990-01-01",
        }
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


def test_invalid_llm_output_raises_validation_error() -> None:
    llm = _StubLLM({"skills": "bir liste değil", "experiences": [{"start": "2020-13"}]})

    with pytest.raises(ValidationError):
        cv_parser.parse_cv("metin", llm)


def test_cv_text_is_truncated_before_sending_to_llm() -> None:
    llm = _StubLLM({})

    cv_parser.parse_cv("x" * (cv_parser.MAX_LLM_CHARS + 500), llm)

    assert llm.received is not None
    assert len(llm.received) == cv_parser.MAX_LLM_CHARS
