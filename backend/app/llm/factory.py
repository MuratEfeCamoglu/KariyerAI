from functools import cache

from pydantic import SecretStr

from app.core.config import LLM_PROVIDERS, get_settings
from app.llm.base import LLMClient, LLMError
from app.llm.fake_client import FakeLLMClient
from app.llm.fallback_client import CooldownBoard, FallbackLLMClient
from app.llm.gemini_client import GeminiClient
from app.llm.groq_client import GroqClient
from app.llm.task_router import TaskRoutedLLMClient

PROVIDERS = LLM_PROVIDERS

Chain = tuple[str, ...]


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


# Kota bekleme durumu tüm zincirlerde ve arka plan işlerinde ortak olmalı.
@cache
def _cooldowns() -> CooldownBoard:
    return CooldownBoard()


def _provider_clients(name: str) -> list[LLMClient]:
    settings = get_settings()
    if name == "fake":
        return [FakeLLMClient()]
    try:
        if name == "gemini":
            key = _secret(settings.gemini_api_key)
            return [_gemini_client(model, key) for model in settings.gemini_models]
        if name == "groq":
            return [_groq_client(settings.groq_model, _secret(settings.groq_api_key))]
    except ValueError as exc:
        # Örn. API anahtarı hiçbir kaynakta yok; ayrıştırma "failed" olur, süreç çökmez.
        raise LLMError(f"'{name}' istemcisi oluşturulamadı (API anahtarını kontrol edin)") from exc
    raise LLMError(f"'{name}' LLM sağlayıcısı desteklenmiyor")


@cache
def _chain_client(chain: Chain) -> LLMClient:
    clients = [client for name in chain for client in _provider_clients(name)]
    if len(clients) == 1:
        return clients[0]
    return FallbackLLMClient(clients, _cooldowns())


@cache
def _routed_client(parse_chain: Chain, score_chain: Chain) -> TaskRoutedLLMClient:
    return TaskRoutedLLMClient(_chain_client(parse_chain), _chain_client(score_chain))


def _chain(value: str) -> Chain:
    return tuple(item.strip() for item in value.split(","))


def get_llm_client(provider: str | None = None) -> LLMClient:
    """Uygulamadaki tek LLM giriş noktası (CLAUDE.md). `provider` yalnızca eval içindir.

    Virgülle ayrılmış liste ("gemini,groq") verilirse sağlayıcılar sırayla denenir;
    LLM_PARSE_PROVIDER / LLM_SCORE_PROVIDER ayrıştırma ve puanlamayı ayrı zincirlere yönlendirir.
    """
    if provider is not None:
        return _chain_client(_chain(provider))
    settings = get_settings()
    parse_chain = tuple(settings.parse_providers)
    score_chain = tuple(settings.score_providers)
    if parse_chain == score_chain:
        return _chain_client(parse_chain)
    return _routed_client(parse_chain, score_chain)
