import json
import logging
from typing import Any, Literal

import anthropic
from anthropic.types.beta import BetaMessageParam, BetaOutputConfigParam

from app.llm.base import (
    PARSE_PROMPT_VERSION,
    LLMError,
    LLMOutputError,
    LLMRefusalError,
    load_prompt,
)

logger = logging.getLogger(__name__)

# ISKELET §3.6: zaman aşımı 60 sn; ağ/429/5xx hatasında SDK üstel beklemeyle 2 kez yeniden dener.
REQUEST_TIMEOUT_SECONDS = 60.0
MAX_NETWORK_RETRIES = 2
MAX_OUTPUT_TOKENS = 16_000
# Yapılandırılmış veri çıkarma düşük efor seviyesinde iyi sonuç verir ve p95 ≤ 30 sn hedefine
# (F5c) yardımcı olur; eval (evals.run) recall'u ölçerek bu seçimi doğrular.
PARSE_EFFORT: Literal["low"] = "low"
# Güvenlik sınıflandırıcısı nadiren meşru bir CV'yi reddedebilir; sunucu tarafı yedek model
# aynı istek içinde devreye girer (yalnızca Claude API'de).
FALLBACK_BETA = "server-side-fallback-2026-07-01"

_NULLABLE_STRING: dict[str, Any] = {"type": ["string", "null"]}

# Structured outputs şeması: modelin ürettiği JSON bu yapıya uyar. Tarih biçimi gibi ince kurallar
# yine de ParsedCV ile doğrulanır. Korunan özellikler (yaş, cinsiyet vb.) şemada yoktur (F5b).
PARSED_CV_JSON_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "full_name",
        "email",
        "phone",
        "summary",
        "skills",
        "experiences",
        "education",
        "languages",
    ],
    "properties": {
        "full_name": _NULLABLE_STRING,
        "email": _NULLABLE_STRING,
        "phone": _NULLABLE_STRING,
        "summary": _NULLABLE_STRING,
        "skills": {"type": "array", "items": {"type": "string"}},
        "experiences": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["title", "company", "start", "end", "description"],
                "properties": {
                    "title": {"type": "string"},
                    "company": _NULLABLE_STRING,
                    "start": _NULLABLE_STRING,
                    "end": _NULLABLE_STRING,
                    "description": _NULLABLE_STRING,
                },
            },
        },
        "education": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["level", "field", "school", "end_year"],
                "properties": {
                    "level": {
                        "type": "string",
                        "enum": ["none", "high_school", "associate", "bachelor", "master", "phd"],
                    },
                    "field": _NULLABLE_STRING,
                    "school": _NULLABLE_STRING,
                    "end_year": {"type": ["integer", "null"]},
                },
            },
        },
        "languages": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["language", "level"],
                "properties": {
                    "language": {"type": "string"},
                    "level": {
                        "type": ["string", "null"],
                        "enum": ["A1", "A2", "B1", "B2", "C1", "C2", None],
                    },
                },
            },
        },
    },
}


class AnthropicClient:
    def __init__(
        self,
        model: str,
        api_key: str | None = None,
        client: anthropic.Anthropic | None = None,
    ) -> None:
        self._model = model
        # api_key None ise SDK ortamdan (ANTHROPIC_API_KEY veya `ant auth login` profili) okur.
        self._client = client or anthropic.Anthropic(
            api_key=api_key, timeout=REQUEST_TIMEOUT_SECONDS, max_retries=MAX_NETWORK_RETRIES
        )
        self._parse_prompt = load_prompt(PARSE_PROMPT_VERSION)

    @property
    def model_name(self) -> str:
        return self._model

    def parse_cv(self, cv_text: str) -> dict[str, Any]:
        prompt = self._parse_prompt
        messages: list[BetaMessageParam] = [
            {"role": "user", "content": prompt.render_user(cv_text=cv_text)}
        ]
        output_config: BetaOutputConfigParam = {
            "effort": PARSE_EFFORT,
            "format": {"type": "json_schema", "schema": PARSED_CV_JSON_SCHEMA},
        }
        try:
            response = self._client.beta.messages.create(
                model=self._model,
                max_tokens=MAX_OUTPUT_TOKENS,
                system=prompt.system,
                messages=messages,
                output_config=output_config,
                betas=[FALLBACK_BETA],
                fallbacks="default",
            )
        except anthropic.APIStatusError as exc:
            # İstek/yanıt gövdesi loglanmaz (CV içeriği); yalnızca durum kodu ve istek kimliği.
            logger.warning(
                "Anthropic API hatası: status=%s request_id=%s", exc.status_code, exc.request_id
            )
            raise LLMError(f"LLM sağlayıcısı hata döndürdü ({exc.status_code})") from exc
        except anthropic.APIConnectionError as exc:
            logger.warning("Anthropic API'ye ulaşılamadı: %s", type(exc).__name__)
            raise LLMError("LLM sağlayıcısına ulaşılamadı") from exc

        if response.stop_reason == "refusal":
            category = response.stop_details.category if response.stop_details else None
            logger.warning("Ayrıştırma reddedildi: category=%s", category)
            raise LLMRefusalError("Model bu CV'yi işlemeyi reddetti")
        if response.stop_reason == "max_tokens":
            raise LLMOutputError("Çıktı token sınırında kesildi")

        text = next((block.text for block in response.content if block.type == "text"), None)
        if text is None:
            raise LLMOutputError("Yanıtta metin yok")
        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            raise LLMOutputError("Yanıt geçerli JSON değil") from exc
        if not isinstance(data, dict):
            raise LLMOutputError("Yanıt bir JSON nesnesi değil")
        return data
