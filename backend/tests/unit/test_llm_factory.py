from collections.abc import Iterator

import pytest
from pydantic import SecretStr

from app.core.config import Settings
from app.llm import factory
from app.llm.base import LLMError
from app.llm.fake_client import FakeLLMClient
from app.llm.gemini_client import GeminiClient
from app.llm.groq_client import GroqClient


@pytest.fixture(autouse=True)
def _clear_client_cache() -> Iterator[None]:
    factory._gemini_client.cache_clear()
    factory._groq_client.cache_clear()
    yield
    factory._gemini_client.cache_clear()
    factory._groq_client.cache_clear()


def _settings(**overrides: object) -> Settings:
    # .env'deki gerçek anahtarlar sızmasın diye anahtarlar varsayılan olarak boş verilir.
    defaults: dict[str, object] = {
        "jwt_secret": "x" * 32,
        "groq_api_key": SecretStr(""),
        "gemini_api_key": SecretStr(""),
    }
    return Settings.model_validate({**defaults, **overrides})


def test_tests_always_use_fake_client() -> None:
    assert isinstance(factory.get_llm_client(), FakeLLMClient)


def test_providers_do_not_include_anthropic() -> None:
    assert set(factory.PROVIDERS) == {"groq", "gemini", "fake"}


def test_groq_provider_uses_configured_model(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = _settings(llm_provider="groq", groq_api_key=SecretStr("gsk_test"), groq_model="g-1")
    monkeypatch.setattr(factory, "get_settings", lambda: settings)

    client = factory.get_llm_client()

    assert isinstance(client, GroqClient)
    assert client.model_name == "g-1"
    # Bağlantı havuzu paylaşılsın diye aynı istemci tekrar kullanılır.
    assert factory.get_llm_client() is client


def test_gemini_provider_uses_configured_model(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = _settings(
        llm_provider="gemini", gemini_api_key=SecretStr("test-key"), gemini_model="m-1"
    )
    monkeypatch.setattr(factory, "get_settings", lambda: settings)

    client = factory.get_llm_client()

    assert isinstance(client, GeminiClient)
    assert client.model_name == "m-1"


def test_provider_override_is_for_evals(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = _settings(groq_api_key=SecretStr("gsk_test"))
    monkeypatch.setattr(factory, "get_settings", lambda: settings)

    assert isinstance(factory.get_llm_client("groq"), GroqClient)
    assert isinstance(factory.get_llm_client("fake"), FakeLLMClient)


@pytest.mark.parametrize("provider", ["groq", "gemini"])
def test_missing_key_raises_llm_error(monkeypatch: pytest.MonkeyPatch, provider: str) -> None:
    settings = _settings(llm_provider=provider)
    monkeypatch.setattr(factory, "get_settings", lambda: settings)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)

    with pytest.raises(LLMError, match="API anahtarını"):
        factory.get_llm_client()


@pytest.mark.parametrize("provider", ["anthropic", "openai"])
def test_unsupported_provider_raises_llm_error(provider: str) -> None:
    with pytest.raises(LLMError):
        factory.get_llm_client(provider)
