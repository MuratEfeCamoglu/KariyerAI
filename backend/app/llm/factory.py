from functools import cache

from pydantic import SecretStr

from app.core.config import LLM_PROVIDERS, Settings, get_settings
from app.llm.base import LLMClient, LLMError
from app.llm.fake_client import FakeLLMClient
from app.llm.fallback_client import FallbackLLMClient
from app.llm.gemini_client import GeminiClient
from app.llm.groq_client import GroqClient

PROVIDERS = LLM_PROVIDERS


def _secret(value: SecretStr | None) -> str | None:
    # .env'de boş bırakılan anahtar (GROQ_API_KEY=) "yok" sayılır.
    return (value.get_secret_value() if value is not None else "") or None


# Bağlantı havuzu tüm arka plan işlerinde paylaşılsın; iki SDK istemcisi de thread-safe'tir.
@cache
def _gemini_client(model: str, api_key: str | None) -> GeminiClient:
    return GeminiClient(model=model, api_key=api_key)


@cache
def _groq_client(model: str, api_key: str | None) -> GroqClient:
    return GroqClient(model=model, api_key=api_key)


# Sağlayıcı bekleme durumu (kota doldu) tüm arka plan işlerinde ortak olmalı.
@cache
def _fallback_client(chain: tuple[str, ...]) -> FallbackLLMClient:
    settings = get_settings()
    return FallbackLLMClient([_single_client(name, settings) for name in chain])


def get_llm_client(provider: str | None = None) -> LLMClient:
    """Uygulamadaki tek LLM giriş noktası (CLAUDE.md). `provider` yalnızca eval içindir.

    Virgülle ayrılmış liste ("gemini,groq") verilirse sağlayıcılar sırayla denenir.
    """
    settings = get_settings()
    chain = tuple(item.strip() for item in (provider or settings.llm_provider).split(","))
    if len(chain) == 1:
        return _single_client(chain[0], settings)
    unknown = [name for name in chain if name not in PROVIDERS]
    if unknown:
        raise LLMError(f"'{unknown[0]}' LLM sağlayıcısı desteklenmiyor")
    return _fallback_client(chain)


def _single_client(chosen: str, settings: Settings) -> LLMClient:
    if chosen == "fake":
        return FakeLLMClient()
    try:
        if chosen == "gemini":
            return _gemini_client(settings.gemini_model, _secret(settings.gemini_api_key))
        if chosen == "groq":
            return _groq_client(settings.groq_model, _secret(settings.groq_api_key))
    except ValueError as exc:
        # Örn. API anahtarı hiçbir kaynakta yok; ayrıştırma "failed" olur, süreç çökmez.
        raise LLMError(
            f"'{chosen}' istemcisi oluşturulamadı (API anahtarını kontrol edin)"
        ) from exc
    raise LLMError(f"'{chosen}' LLM sağlayıcısı desteklenmiyor")
