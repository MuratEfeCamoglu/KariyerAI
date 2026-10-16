import logging
from typing import Any, Literal

import anthropic
from anthropic.types.beta import BetaMessageParam, BetaOutputConfigParam

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

# ISKELET §3.6: zaman aşımı 60 sn; ağ/429/5xx hatasında SDK üstel beklemeyle 2 kez yeniden dener.
REQUEST_TIMEOUT_SECONDS = 60.0
MAX_NETWORK_RETRIES = 2
MAX_OUTPUT_TOKENS = 16_000
# Yapılandırılmış veri çıkarma düşük efor seviyesinde iyi sonuç verir ve p95 ≤ 30 sn hedefine
# (F5c) yardımcı olur; eval (evals.run) recall'u ölçerek bu seçimi doğrular.
PARSE_EFFORT: Literal["low"] = "low"
# Kanıtı birebir alıntılamak ve eşanlamlıları ayırt etmek çıkarmadan daha fazla muhakeme ister.
SCORE_EFFORT: Literal["medium"] = "medium"
# Güvenlik sınıflandırıcısı nadiren meşru bir CV'yi reddedebilir; sunucu tarafı yedek model
# aynı istek içinde devreye girer (yalnızca Claude API'de).
FALLBACK_BETA = "server-side-fallback-2026-07-01"


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
            effort=PARSE_EFFORT,
        )

    def score_cv(
        self, anonymized_cv: str, criteria: list[dict[str, str]], profile: dict[str, Any]
    ) -> dict[str, Any]:
        prompt = self._score_prompt
        return self._complete_json(
            system=prompt.system,
            user=render_score_input(prompt, anonymized_cv, criteria, profile),
            schema=SCORE_JSON_SCHEMA,
            effort=SCORE_EFFORT,
        )

    def _complete_json(
        self,
        *,
        system: str,
        user: str,
        schema: dict[str, Any],
        effort: Literal["low", "medium"],
    ) -> dict[str, Any]:
        messages: list[BetaMessageParam] = [{"role": "user", "content": user}]
        output_config: BetaOutputConfigParam = {
            "effort": effort,
            "format": {"type": "json_schema", "schema": schema},
        }
        try:
            response = self._client.beta.messages.create(
                model=self._model,
                max_tokens=MAX_OUTPUT_TOKENS,
                system=system,
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
            logger.warning("İstek reddedildi: category=%s", category)
            raise LLMRefusalError("Model bu CV'yi işlemeyi reddetti")
        if response.stop_reason == "max_tokens":
            raise LLMOutputError("Çıktı token sınırında kesildi")

        text = next((block.text for block in response.content if block.type == "text"), None)
        return parse_json_object(text)
