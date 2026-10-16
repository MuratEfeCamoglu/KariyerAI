import threading
from typing import Any

import pytest

from app.llm.base import LLMError, LLMOutputError, LLMRateLimitError, LLMRefusalError
from app.llm.fallback_client import (
    DEFAULT_RATE_LIMIT_COOLDOWN_SECONDS,
    ERROR_COOLDOWN_SECONDS,
    MAX_COOLDOWN_SECONDS,
    FallbackLLMClient,
)

PARSED = {"skills": ["Python"]}


class _Clock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


class _StubLLM:
    def __init__(self, name: str, errors: list[Exception] | None = None) -> None:
        self.model_name = name
        self.errors = list(errors or [])
        self.calls = 0

    def parse_cv(self, cv_text: str) -> dict[str, Any]:
        self.calls += 1
        if self.errors:
            raise self.errors.pop(0)
        return {**PARSED, "by": self.model_name}

    def score_cv(
        self, anonymized_cv: str, criteria: list[dict[str, str]], profile: dict[str, Any]
    ) -> dict[str, Any]:
        return self.parse_cv(anonymized_cv)


def _fallback(primary: _StubLLM, secondary: _StubLLM) -> tuple[FallbackLLMClient, _Clock]:
    clock = _Clock()
    return FallbackLLMClient([primary, secondary], clock=clock), clock


def test_primary_serves_while_it_works() -> None:
    gemini, groq = _StubLLM("gemini"), _StubLLM("groq")
    client, _ = _fallback(gemini, groq)

    assert client.parse_cv("cv")["by"] == "gemini"
    assert client.model_name == "gemini"
    assert groq.calls == 0


def test_rate_limit_switches_to_secondary_and_reports_its_model() -> None:
    gemini = _StubLLM("gemini", [LLMRateLimitError("kota", retry_after=120)])
    groq = _StubLLM("groq")
    client, _ = _fallback(gemini, groq)

    assert client.score_cv("cv", [], {})["by"] == "groq"
    # Pipeline ve puanlama audit'e çağrıya hizmet eden modeli yazar.
    assert client.model_name == "groq"


def test_primary_is_skipped_during_cooldown_then_used_again() -> None:
    gemini = _StubLLM("gemini", [LLMRateLimitError("kota", retry_after=120)])
    groq = _StubLLM("groq")
    client, clock = _fallback(gemini, groq)

    client.parse_cv("cv")
    clock.now += 119
    assert client.parse_cv("cv")["by"] == "groq"
    assert gemini.calls == 1  # Beklemedeyken boşuna istek atılmaz.

    clock.now += 1
    assert client.parse_cv("cv")["by"] == "gemini"


def test_rate_limit_without_delay_uses_default_cooldown() -> None:
    gemini = _StubLLM("gemini", [LLMRateLimitError("kota")])
    client, clock = _fallback(gemini, _StubLLM("groq"))

    client.parse_cv("cv")
    clock.now += DEFAULT_RATE_LIMIT_COOLDOWN_SECONDS - 1
    assert client.parse_cv("cv")["by"] == "groq"
    clock.now += 1
    assert client.parse_cv("cv")["by"] == "gemini"


def test_cooldown_is_capped_at_one_day() -> None:
    gemini = _StubLLM("gemini", [LLMRateLimitError("kota", retry_after=10 * MAX_COOLDOWN_SECONDS)])
    client, clock = _fallback(gemini, _StubLLM("groq"))

    client.parse_cv("cv")
    clock.now += MAX_COOLDOWN_SECONDS
    assert client.parse_cv("cv")["by"] == "gemini"


def test_server_error_falls_back_with_short_cooldown() -> None:
    gemini = _StubLLM("gemini", [LLMError("503")])
    client, clock = _fallback(gemini, _StubLLM("groq"))

    assert client.parse_cv("cv")["by"] == "groq"
    clock.now += ERROR_COOLDOWN_SECONDS
    assert client.parse_cv("cv")["by"] == "gemini"


def test_refusal_falls_back_without_cooldown() -> None:
    gemini = _StubLLM("gemini", [LLMRefusalError("red")])
    client, _ = _fallback(gemini, _StubLLM("groq"))

    assert client.parse_cv("cv")["by"] == "groq"
    assert client.parse_cv("cv")["by"] == "gemini"


def test_output_error_is_not_masked_by_fallback() -> None:
    # Bozuk çıktıyı çağıran taraf (cv_parser/scoring) kendisi bir kez yeniden dener.
    gemini = _StubLLM("gemini", [LLMOutputError("kesik")])
    groq = _StubLLM("groq")
    client, _ = _fallback(gemini, groq)

    with pytest.raises(LLMOutputError):
        client.parse_cv("cv")
    assert groq.calls == 0


def test_all_providers_failing_raises_last_error() -> None:
    gemini = _StubLLM("gemini", [LLMRateLimitError("gemini kota", retry_after=600)])
    groq = _StubLLM("groq", [LLMRateLimitError("groq kota", retry_after=60)])
    client, _ = _fallback(gemini, groq)

    with pytest.raises(LLMRateLimitError, match="groq kota"):
        client.parse_cv("cv")


def test_when_all_cool_down_the_earliest_available_is_tried() -> None:
    gemini = _StubLLM("gemini", [LLMRateLimitError("kota", retry_after=600)])
    groq = _StubLLM("groq", [LLMRateLimitError("kota", retry_after=60)])
    client, _ = _fallback(gemini, groq)
    with pytest.raises(LLMRateLimitError):
        client.parse_cv("cv")

    # İş bekletilmeden başarısız sayılmasın: en erken açılacak olan yine de denenir.
    assert client.parse_cv("cv")["by"] == "groq"
    assert gemini.calls == 1


def test_model_name_is_tracked_per_thread() -> None:
    gemini = _StubLLM("gemini", [LLMRateLimitError("kota", retry_after=60)])
    client, _ = _fallback(gemini, _StubLLM("groq"))
    client.parse_cv("cv")
    seen: list[str] = []

    # Başka bir thread henüz çağrı yapmadı: birincil sağlayıcının adını görür.
    thread = threading.Thread(target=lambda: seen.append(client.model_name))
    thread.start()
    thread.join()

    assert client.model_name == "groq"
    assert seen == ["gemini"]


def test_requires_at_least_one_client() -> None:
    with pytest.raises(ValueError):
        FallbackLLMClient([])
