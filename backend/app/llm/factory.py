from app.core.config import get_settings
from app.llm.base import LLMClient, LLMError
from app.llm.fake_client import FakeLLMClient


def get_llm_client() -> LLMClient:
    provider = get_settings().llm_provider
    if provider == "fake":
        return FakeLLMClient()
    # Gerçek Anthropic istemcisi Aşama 4'te (F5) eklenir.
    raise LLMError(f"'{provider}' LLM sağlayıcısı henüz desteklenmiyor")
