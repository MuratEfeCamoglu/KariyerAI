from typing import Any, Protocol


class LLMError(Exception):
    """LLM çağrısı başarısız oldu (ağ, zaman aşımı, sağlayıcı hatası)."""


class LLMClient(Protocol):
    """Servislerin gördüğü tek LLM arayüzü; somut istemciye yalnızca factory erişir."""

    @property
    def model_name(self) -> str: ...

    def parse_cv(self, cv_text: str) -> dict[str, Any]:
        """CV metninden ParsedCV biçiminde ham JSON döner; doğrulama çağıranın işidir."""
        ...
