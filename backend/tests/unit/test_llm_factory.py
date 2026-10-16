from collections.abc import Iterator

import pytest
from pydantic import SecretStr

from app.core.config import Settings
from app.llm import factory
from app.llm.anthropic_client import AnthropicClient
from app.llm.base import LLMError
from app.llm.fake_client import FakeLLMClient
from app.llm.gemini_client import GeminiClient
from app.llm.groq_client import GroqClient


@pytest.fixture(autouse=True)
def _clear_client_cache() -> Iterator[None]:
    factory._anthropic_client.cache_clear()
    factory._gemini_client.cache_clear()
    factory._groq_client.cache_clear()
    yield
    factory._anthropic_client.cache_clear()
    factory._gemini_client.cache_clear()
    factory._groq_client.cache_clear()


def _settings(**overrides: object) -> Settings:
    return Settings.model_validate({"jwt_secret": "x" * 32, **overrides})


def test_tests_always_use_fake_client() -> None:
    assert isinstance(factory.get_llm_client(), FakeLLMClient)


def test_anthropic_provider_uses_configured_model(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = _settings(
        llm_provider="anthropic", anthropic_api_key=SecretStr("sk-test"), llm_model="m-1"
    )
    monkeypatch.setattr(factory, "get_settings", lambda: settings)

    client = factory.get_llm_client()

    assert isinstance(client, AnthropicClient)
    assert client.model_name == "m-1"
    # Bağlantı havuzu paylaşılsın diye aynı istemci tekrar kullanılır.
    assert factory.get_llm_client() is client


def test_provider_override_is_for_evals(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = _settings(anthropic_api_key=SecretStr("sk-test"))
    monkeypatch.setattr(factory, "get_settings", lambda: settings)

    assert isinstance(factory.get_llm_client("anthropic"), AnthropicClient)
    assert isinstance(factory.get_llm_client("fake"), FakeLLMClient)


def test_gemini_provider_uses_gemini_model(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = _settings(
        llm_provider="gemini", gemini_api_key=SecretStr("test-key"), gemini_model="g-1"
    )
    monkeypatch.setattr(factory, "get_settings", lambda: settings)

    client = factory.get_llm_client()

    assert isinstance(client, GeminiClient)
    assert client.model_name == "g-1"


def test_missing_gemini_key_raises_llm_error(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = _settings(llm_provider="gemini", gemini_api_key=SecretStr(""))
    monkeypatch.setattr(factory, "get_settings", lambda: settings)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)

    with pytest.raises(LLMError, match="API anahtarını"):
        factory.get_llm_client()


def test_groq_provider_uses_groq_model(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = _settings(llm_provider="groq", groq_api_key=SecretStr("gsk_test"))
    monkeypatch.setattr(factory, "get_settings", lambda: settings)

    client = factory.get_llm_client()

    assert isinstance(client, GroqClient)
    assert client.model_name == "openai/gpt-oss-120b"


def test_missing_groq_key_raises_llm_error(monkeypatch: pytest.MonkeyPatch) -> None:
    # .env'deki gerçek anahtar sızmasın diye açıkça boş verilir.
    settings = _settings(llm_provider="groq", groq_api_key=SecretStr(""))
    monkeypatch.setattr(factory, "get_settings", lambda: settings)

    with pytest.raises(LLMError, match="API anahtarını"):
        factory.get_llm_client()


def test_unknown_provider_raises_llm_error() -> None:
    with pytest.raises(LLMError):
        factory.get_llm_client("openai")
