from functools import cache

import anthropic

from app.core.config import get_settings
from app.llm.anthropic_client import AnthropicClient
from app.llm.base import LLMClient, LLMError
from app.llm.fake_client import FakeLLMClient


@cache
def _anthropic_client(model: str, api_key: str | None) -> AnthropicClient:
    # Bağlantı havuzu tüm arka plan işlerinde paylaşılsın; SDK istemcisi thread-safe'tir.
    return AnthropicClient(model=model, api_key=api_key)


def get_llm_client(provider: str | None = None) -> LLMClient:
    """Uygulamadaki tek LLM giriş noktası (CLAUDE.md). `provider` yalnızca eval içindir."""
    settings = get_settings()
    chosen = provider or settings.llm_provider
    if chosen == "fake":
        return FakeLLMClient()
    if chosen == "anthropic":
        secret = settings.anthropic_api_key
        api_key = secret.get_secret_value() if secret is not None else ""
        try:
            return _anthropic_client(settings.llm_model, api_key or None)
        except anthropic.AnthropicError as exc:
            # Örn. hiçbir kaynakta API anahtarı yok; ayrıştırma "failed" olur, süreç çökmez.
            raise LLMError("Anthropic istemcisi oluşturulamadı") from exc
    raise LLMError(f"'{chosen}' LLM sağlayıcısı desteklenmiyor")
