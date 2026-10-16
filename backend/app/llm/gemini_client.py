"""Google Gemini istemcisi — yalnızca geliştirme ve eval içindir (ISKELET V2).

Ücretsiz katmanda gönderilen içerik sağlayıcının ürün geliştirmesinde kullanılabilir; bu yüzden
bu istemciye gerçek aday CV'si gönderilmez, yalnızca sentetik test/eval verisi gönderilir.
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

_REFUSAL_FINISH_REASONS = frozenset(
    {
        types.FinishReason.SAFETY,
        types.FinishReason.BLOCKLIST,
        types.FinishReason.PROHIBITED_CONTENT,
        types.FinishReason.SPII,
        types.FinishReason.RECITATION,
    }
)


class GeminiClient:
    def __init__(
        self, model: str, api_key: str | None = None, client: genai.Client | None = None
    ) -> None:
        self._model = model
        self._client = client or genai.Client(
            api_key=api_key,
            http_options=types.HttpOptions(
                timeout=REQUEST_TIMEOUT_MS,
                retry_options=types.HttpRetryOptions(attempts=TOTAL_ATTEMPTS),
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
