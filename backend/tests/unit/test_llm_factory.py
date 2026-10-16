from collections.abc import Iterator

import pytest
from pydantic import SecretStr

from app.core.config import Settings
from app.llm import factory
from app.llm.anthropic_client import AnthropicClient
from app.llm.base import LLMError
from app.llm.fake_client import FakeLLMClient


@pytest.fixture(autouse=True)
def _clear_client_cache() -> Iterator[None]:
    factory._anthropic_client.cache_clear()
    yield
    factory._anthropic_client.cache_clear()


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


def test_unknown_provider_raises_llm_error() -> None:
    with pytest.raises(LLMError):
        factory.get_llm_client("openai")
