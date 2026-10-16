import pytest
from pydantic import ValidationError

from app.core.config import EXAMPLE_JWT_SECRET, Settings


def test_example_secret_is_allowed_in_development() -> None:
    settings = Settings.model_validate({"jwt_secret": EXAMPLE_JWT_SECRET})

    assert settings.cookie_secure is False


def test_example_secret_is_rejected_when_cookie_secure() -> None:
    with pytest.raises(ValidationError, match="örnek JWT_SECRET"):
        Settings.model_validate({"jwt_secret": EXAMPLE_JWT_SECRET, "cookie_secure": True})


def test_custom_secret_works_with_cookie_secure() -> None:
    settings = Settings.model_validate({"jwt_secret": "x" * 48, "cookie_secure": True})

    assert settings.cookie_secure is True


def test_example_file_secret_matches_guard() -> None:
    from pathlib import Path

    example = (Path(__file__).resolve().parents[2] / ".env.example").read_text(encoding="utf-8")

    assert f"JWT_SECRET={EXAMPLE_JWT_SECRET}" in example


@pytest.mark.parametrize(
    ("value", "expected"),
    [("groq", ["groq"]), ("gemini, groq", ["gemini", "groq"]), ("fake", ["fake"])],
)
def test_llm_provider_accepts_ordered_list(value: str, expected: list[str]) -> None:
    settings = Settings.model_validate({"jwt_secret": "x" * 32, "llm_provider": value})

    assert settings.llm_providers == expected


@pytest.mark.parametrize("value", ["anthropic", "gemini,anthropic", "groq,groq", "gemini,", ""])
def test_llm_provider_rejects_unknown_or_duplicate(value: str) -> None:
    with pytest.raises(ValidationError, match="LLM_PROVIDER"):
        Settings.model_validate({"jwt_secret": "x" * 32, "llm_provider": value})
