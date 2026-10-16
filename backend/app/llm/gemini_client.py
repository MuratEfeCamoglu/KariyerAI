"""Google Gemini istemcisi (ISKELET V2, §3.6).

Ücretsiz katmanda gönderilen içerik sağlayıcının ürün geliştirmesinde kullanılabilir; gerçek aday
CV'leri için ücretli katman önerilir (README, ISKELET R3).
"""

import logging
from typing import Any

import httpx
from google import genai
from google.genai import errors, types

from app.llm.base import (
    PARSE_PROMPT_VERSION,
    PARSED_CV_JSON_SCHEMA,
    SCORE_JSON_SCHEMA,
    SCORE_PROMPT_VERSION,
    LLMError,
    LLMOutputError,
    LLMRateLimitError,
    LLMRefusalError,
    load_prompt,
    parse_json_object,
    render_score_input,
)

logger = logging.getLogger(__name__)

# ISKELET §3.6 ile aynı davranış: 60 sn zaman aşımı, geçici hatada 2 yeniden deneme (toplam 3).
REQUEST_TIMEOUT_MS = 60_000
TOTAL_ATTEMPTS = 3
MAX_OUTPUT_TOKENS = 16_000
# 429 burada yeniden denenmez: kota dolunca beklemek yerine yedek sağlayıcıya geçilir (fallback).
_RETRYABLE_STATUS = [408, 500, 502, 503, 504]

_REFUSAL_FINISH_REASONS = frozenset(
    {
        types.FinishReason.SAFETY,
        types.FinishReason.BLOCKLIST,
        types.FinishReason.PROHIBITED_CONTENT,
        types.FinishReason.SPII,
        types.FinishReason.RECITATION,
    }
)


def _retry_delay(details: Any) -> float | None:
    """429 gövdesindeki google.rpc.RetryInfo `retryDelay` değerini ("51s") saniyeye çevirir."""
    error = details.get("error") if isinstance(details, dict) else None
    items = error.get("details") if isinstance(error, dict) else None
    if not isinstance(items, list):
        return None
    for item in items:
        delay = item.get("retryDelay") if isinstance(item, dict) else None
        if isinstance(delay, str) and delay.endswith("s"):
            try:
                return max(float(delay[:-1]), 0.0)
            except ValueError:
                return None
    return None


class GeminiClient:
    def __init__(
        self, model: str, api_key: str | None = None, client: genai.Client | None = None
    ) -> None:
        self._model = model
        self._client = client or genai.Client(
            api_key=api_key,
            http_options=types.HttpOptions(
                timeout=REQUEST_TIMEOUT_MS,
                retry_options=types.HttpRetryOptions(
                    attempts=TOTAL_ATTEMPTS, http_status_codes=_RETRYABLE_STATUS
                ),
            ),
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
            schema=PARSED_CV_JSON_SCHEMA,
        )

    def score_cv(
        self, anonymized_cv: str, criteria: list[dict[str, str]], profile: dict[str, Any]
    ) -> dict[str, Any]:
        prompt = self._score_prompt
        return self._complete_json(
            system=prompt.system,
            user=render_score_input(prompt, anonymized_cv, criteria, profile),
            schema=SCORE_JSON_SCHEMA,
        )

    def _complete_json(self, *, system: str, user: str, schema: dict[str, Any]) -> dict[str, Any]:
        config = types.GenerateContentConfig(
            system_instruction=system,
            response_mime_type="application/json",
            response_json_schema=schema,
            # Veri çıkarma: aynı CV'ye aynı çıktı (tutarlılık, ISKELET §1).
            temperature=0,
            max_output_tokens=MAX_OUTPUT_TOKENS,
        )
        try:
            response = self._client.models.generate_content(
                model=self._model, contents=user, config=config
            )
        except errors.APIError as exc:
            # Yanıt gövdesi loglanmaz (CV içeriği yansıyabilir); yalnızca durum kodu.
            logger.warning("Gemini API hatası: code=%s", exc.code)
            if exc.code == 429:
                raise LLMRateLimitError(
                    "LLM sağlayıcısının kotası doldu (429)", _retry_delay(exc.details)
                ) from exc
            raise LLMError(f"LLM sağlayıcısı hata döndürdü ({exc.code})") from exc
        except httpx.HTTPError as exc:
            logger.warning("Gemini API'ye ulaşılamadı: %s", type(exc).__name__)
            raise LLMError("LLM sağlayıcısına ulaşılamadı") from exc

        feedback = response.prompt_feedback
        if feedback is not None and feedback.block_reason is not None:
            logger.warning("İstek reddedildi: block_reason=%s", feedback.block_reason)
            raise LLMRefusalError("Model bu CV'yi işlemeyi reddetti")
        if not response.candidates:
            raise LLMOutputError("Yanıtta aday çıktı yok")
        finish_reason = response.candidates[0].finish_reason
        if finish_reason in _REFUSAL_FINISH_REASONS:
            logger.warning("İstek reddedildi: finish_reason=%s", finish_reason)
            raise LLMRefusalError("Model bu CV'yi işlemeyi reddetti")
        if finish_reason == types.FinishReason.MAX_TOKENS:
            raise LLMOutputError("Çıktı token sınırında kesildi")
        return parse_json_object(response.text)
