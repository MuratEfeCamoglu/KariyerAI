from functools import cache

import anthropic
from pydantic import SecretStr

from app.core.config import get_settings
from app.llm.anthropic_client import AnthropicClient
from app.llm.base import LLMClient, LLMError
from app.llm.fake_client import FakeLLMClient
from app.llm.gemini_client import GeminiClient
from app.llm.groq_client import GroqClient

PROVIDERS = ("anthropic", "gemini", "groq", "fake")


def _secret(value: SecretStr | None) -> str | None:
    # .env'de boş bırakılan anahtar (ANTHROPIC_API_KEY=) "yok" sayılır.
    return (value.get_secret_value() if value is not None else "") or None


# Bağlantı havuzu tüm arka plan işlerinde paylaşılsın; iki SDK istemcisi de thread-safe'tir.
@cache
def _anthropic_client(model: str, api_key: str | None) -> AnthropicClient:
    return AnthropicClient(model=model, api_key=api_key)


@cache
def _gemini_client(model: str, api_key: str | None) -> GeminiClient:
    return GeminiClient(model=model, api_key=api_key)


@cache
def _groq_client(model: str, api_key: str | None) -> GroqClient:
    return GroqClient(model=model, api_key=api_key)


def get_llm_client(provider: str | None = None) -> LLMClient:
    """Uygulamadaki tek LLM giriş noktası (CLAUDE.md). `provider` yalnızca eval içindir."""
    settings = get_settings()
    chosen = provider or settings.llm_provider
    if chosen == "fake":
        return FakeLLMClient()
    try:
        if chosen == "anthropic":
            return _anthropic_client(settings.llm_model, _secret(settings.anthropic_api_key))
        if chosen == "gemini":
            return _gemini_client(settings.gemini_model, _secret(settings.gemini_api_key))
        if chosen == "groq":
            return _groq_client(settings.groq_model, _secret(settings.groq_api_key))
    except (anthropic.AnthropicError, ValueError) as exc:
        # Örn. API anahtarı hiçbir kaynakta yok; ayrıştırma "failed" olur, süreç çökmez.
        raise LLMError(
            f"'{chosen}' istemcisi oluşturulamadı (API anahtarını kontrol edin)"
        ) from exc
    raise LLMError(f"'{chosen}' LLM sağlayıcısı desteklenmiyor")
