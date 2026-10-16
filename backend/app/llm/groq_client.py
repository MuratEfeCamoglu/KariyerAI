"""Groq istemcisi (OpenAI uyumlu API; ISKELET V2, §3.6).

Ücretsiz katmanın asıl sınırı dakikalık token kotasıdır; 429 yanıtındaki bekleme süresine uyulur.
Gerçek aday CV'leri için veri saklama koşulları: README, ISKELET R3.
"""

import logging
import time
from collections.abc import Callable
from typing import Any, Literal

import httpx

from app.llm.base import (
    PARSE_PROMPT_VERSION,
    PARSED_CV_JSON_SCHEMA,
    SCORE_JSON_SCHEMA,
    SCORE_PROMPT_VERSION,
    LLMError,
    LLMOutputError,
    LLMRateLimitError,
    load_prompt,
    parse_json_object,
    render_score_input,
)

logger = logging.getLogger(__name__)

BASE_URL = "https://api.groq.com/openai/v1"
# ISKELET §3.6: 60 sn zaman aşımı, geçici hatada (429/5xx/ağ) en fazla 2 yeniden deneme.
REQUEST_TIMEOUT_SECONDS = 60.0
MAX_RETRIES = 2
MAX_RETRY_WAIT_SECONDS = 30.0
MAX_COMPLETION_TOKENS = 8_000
_RETRYABLE_STATUS = frozenset({429, 500, 502, 503, 504})

ReasoningEffort = Literal["low", "medium"]


def _retry_after_header(response: httpx.Response) -> float | None:
    header = response.headers.get("retry-after")
    try:
        return max(float(header), 0.0) if header is not None else None
    except ValueError:
        return None


def _retry_after(response: httpx.Response, attempt: int) -> float:
    wait = _retry_after_header(response)
    return min(wait if wait is not None else 2.0**attempt, MAX_RETRY_WAIT_SECONDS)


class GroqClient:
    def __init__(
        self,
        model: str,
        api_key: str | None,
        transport: httpx.BaseTransport | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        if not api_key:
            raise ValueError("GROQ_API_KEY tanımlı değil")
        self._model = model
        self._sleep = sleep
        self._http = httpx.Client(
            base_url=BASE_URL,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=REQUEST_TIMEOUT_SECONDS,
            transport=transport,
        )
        self._parse_prompt = load_prompt(PARSE_PROMPT_VERSION)
        self._score_prompt = load_prompt(SCORE_PROMPT_VERSION)

    @property
    def model_name(self) -> str:
        return self._model

    def parse_cv(self, cv_text: str) -> dict[str, Any]:
        prompt = self._parse_prompt
        return self._complete_json(
            system=prompt.system,
            user=prompt.render_user(cv_text=cv_text),
            schema_name="parsed_cv",
            schema=PARSED_CV_JSON_SCHEMA,
            effort="low",
        )

    def score_cv(
        self, anonymized_cv: str, criteria: list[dict[str, str]], profile: dict[str, Any]
    ) -> dict[str, Any]:
        prompt = self._score_prompt
        return self._complete_json(
            system=prompt.system,
            user=render_score_input(prompt, anonymized_cv, criteria, profile),
            schema_name="criterion_judgments",
            schema=SCORE_JSON_SCHEMA,
            # Birebir alıntı ve eşanlamlı ayrımı çıkarmadan daha fazla muhakeme ister.
            effort="medium",
        )

    def _post(self, body: dict[str, Any]) -> httpx.Response:
        for attempt in range(MAX_RETRIES + 1):
            try:
                response = self._http.post("/chat/completions", json=body)
            except httpx.HTTPError as exc:
                logger.warning(
                    "Groq API'ye ulaşılamadı: %s (deneme %s)", type(exc).__name__, attempt
                )
                if attempt == MAX_RETRIES:
                    raise LLMError("LLM sağlayıcısına ulaşılamadı") from exc
                self._sleep(2.0**attempt)
                continue
            if response.status_code in _RETRYABLE_STATUS and attempt < MAX_RETRIES:
                wait = _retry_after(response, attempt)
                logger.info("Groq %s, %.1f sn sonra yeniden denenecek", response.status_code, wait)
                self._sleep(wait)
                continue
            return response
        raise AssertionError("ulaşılamaz")

    def _complete_json(
        self,
        *,
        system: str,
        user: str,
        schema_name: str,
        schema: dict[str, Any],
        effort: ReasoningEffort,
    ) -> dict[str, Any]:
        body = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": 0,
            "max_completion_tokens": MAX_COMPLETION_TOKENS,
            "reasoning_effort": effort,
            "response_format": {
                "type": "json_schema",
                "json_schema": {"name": schema_name, "strict": True, "schema": schema},
            },
        }
        response = self._post(body)

        if response.status_code == 400 and self._error_code(response) == "json_validate_failed":
            # Model şemaya uyan çıktı üretemedi; çağıran taraf bir kez yeniden dener (F5a).
            raise LLMOutputError("Model şemaya uygun JSON üretemedi")
        if response.status_code == 429:
            logger.warning("Groq kotası doldu: status=429")
            raise LLMRateLimitError(
                "LLM sağlayıcısının kotası doldu (429)", _retry_after_header(response)
            )
        if response.status_code != 200:
            # Yanıt gövdesi loglanmaz (CV içeriği yansıyabilir); yalnızca durum kodu.
            logger.warning("Groq API hatası: status=%s", response.status_code)
            raise LLMError(f"LLM sağlayıcısı hata döndürdü ({response.status_code})")

        choice = response.json()["choices"][0]
        if choice.get("finish_reason") == "length":
            raise LLMOutputError("Çıktı token sınırında kesildi")
        return parse_json_object(choice["message"].get("content"))

    @staticmethod
    def _error_code(response: httpx.Response) -> str | None:
        try:
            error = response.json().get("error", {})
        except ValueError:
            return None
        code = error.get("code") if isinstance(error, dict) else None
        return str(code) if code is not None else None
