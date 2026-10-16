"""Ayrıştırma ve puanlamayı farklı sağlayıcılara yönlendiren istemci.

Ücretsiz kotası küçük sağlayıcı (Gemini) yalnızca bir işe ayrılınca CV başına bir istek harcar;
örn. ayrıştırma Groq'ta, puanlama Gemini'de (LLM_PARSE_PROVIDER / LLM_SCORE_PROVIDER).
"""

import threading
from typing import Any

from app.llm.base import LLMClient


class TaskRoutedLLMClient:
    def __init__(self, parse_client: LLMClient, score_client: LLMClient) -> None:
        self._parse_client = parse_client
        self._score_client = score_client
        # Pipeline `model_name`'i çağrıdan sonra okuyup audit'e yazar; thread başına tutulur.
        self._last = threading.local()

    @property
    def model_name(self) -> str:
        client: LLMClient = getattr(self._last, "client", self._parse_client)
        return client.model_name

    def parse_cv(self, cv_text: str) -> dict[str, Any]:
        self._last.client = self._parse_client
        return self._parse_client.parse_cv(cv_text)

    def score_cv(
        self, anonymized_cv: str, criteria: list[dict[str, str]], profile: dict[str, Any]
    ) -> dict[str, Any]:
        self._last.client = self._score_client
        return self._score_client.score_cv(anonymized_cv, criteria, profile)
