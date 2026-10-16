import json
from types import SimpleNamespace
from typing import Any, cast

import httpx
import pytest
from google import genai
from google.genai import errors, types

from app.llm.base import (
    PARSED_CV_JSON_SCHEMA,
    LLMError,
    LLMOutputError,
    LLMRateLimitError,
    LLMRefusalError,
)
from app.llm.gemini_client import GeminiClient

VALID_OUTPUT = {
    "full_name": "Deniz Arslan",
    "email": None,
    "phone": None,
    "summary": None,
    "skills": ["Python"],
    "experiences": [],
    "education": [],
    "languages": [],
}


def _response(
    *,
    text: str | None = None,
    finish_reason: types.FinishReason = types.FinishReason.STOP,
    block_reason: types.BlockedReason | None = None,
    candidates: bool = True,
) -> SimpleNamespace:
    return SimpleNamespace(
        text=text,
        prompt_feedback=SimpleNamespace(block_reason=block_reason) if block_reason else None,
        candidates=[SimpleNamespace(finish_reason=finish_reason)] if candidates else [],
    )


class _StubModels:
    def __init__(self, result: SimpleNamespace | Exception) -> None:
        self.result = result
        self.kwargs: dict[str, Any] = {}

    def generate_content(self, **kwargs: Any) -> SimpleNamespace:
        self.kwargs = kwargs
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


def _client(result: SimpleNamespace | Exception) -> tuple[GeminiClient, _StubModels]:
    models = _StubModels(result)
    sdk = SimpleNamespace(models=models)
    return GeminiClient("gemini-test", client=cast(genai.Client, sdk)), models


def test_request_uses_shared_prompt_and_json_schema() -> None:
    client, models = _client(_response(text=json.dumps(VALID_OUTPUT)))
    cv_text = 'Deniz Arslan\n{"not": "a template"}'

    assert client.parse_cv(cv_text) == VALID_OUTPUT

    sent = models.kwargs
    assert sent["model"] == "gemini-test"
    assert sent["contents"] == f"<cv>\n{cv_text}\n</cv>"
    config: types.GenerateContentConfig = sent["config"]
    assert config.system_instruction is not None
    assert "not instructions" in str(config.system_instruction)
    assert config.response_mime_type == "application/json"
    assert config.response_json_schema == PARSED_CV_JSON_SCHEMA
    assert config.temperature == 0


@pytest.mark.parametrize(
    "response",
    [
        _response(block_reason=types.BlockedReason.SAFETY),
        _response(text="{}", finish_reason=types.FinishReason.SAFETY),
        _response(text="{}", finish_reason=types.FinishReason.PROHIBITED_CONTENT),
    ],
)
def test_safety_blocks_raise_refusal(response: SimpleNamespace) -> None:
    client, _ = _client(response)

    with pytest.raises(LLMRefusalError):
        client.parse_cv("cv")


@pytest.mark.parametrize(
    "response",
    [
        _response(text='{"skills": ["Pyt', finish_reason=types.FinishReason.MAX_TOKENS),
        _response(text="json değil"),
        _response(text=None),
        _response(candidates=False),
    ],
)
def test_unusable_output_raises_output_error(response: SimpleNamespace) -> None:
    client, _ = _client(response)

    with pytest.raises(LLMOutputError):
        client.parse_cv("cv")


def test_api_error_becomes_llm_error_without_leaking_body(
    caplog: pytest.LogCaptureFixture,
) -> None:
    error = errors.ServerError(503, {"error": {"message": "Deniz Arslan özgeçmişi"}})
    client, _ = _client(error)

    with pytest.raises(LLMError, match="503"):
        client.parse_cv("cv")
    assert "Deniz" not in caplog.text


def test_network_error_becomes_llm_error() -> None:
    client, _ = _client(httpx.ConnectTimeout("zaman aşımı"))

    with pytest.raises(LLMError) as exc_info:
        client.parse_cv("cv")
    assert not isinstance(exc_info.value, LLMOutputError)


def test_quota_error_becomes_rate_limit_with_retry_delay() -> None:
    body = {
        "error": {
            "code": 429,
            "details": [
                {"@type": "type.googleapis.com/google.rpc.QuotaFailure"},
                {"@type": "type.googleapis.com/google.rpc.RetryInfo", "retryDelay": "51s"},
            ],
        }
    }
    client, _ = _client(errors.ClientError(429, body))

    with pytest.raises(LLMRateLimitError) as exc_info:
        client.parse_cv("cv")
    assert exc_info.value.retry_after == 51.0


def test_quota_error_without_retry_info_has_no_delay() -> None:
    client, _ = _client(errors.ClientError(429, {"error": {"code": 429}}))

    with pytest.raises(LLMRateLimitError) as exc_info:
        client.parse_cv("cv")
    assert exc_info.value.retry_after is None


def test_sdk_does_not_retry_quota_errors() -> None:
    # Kota dolunca SDK içinde beklemek yerine yedek sağlayıcıya hemen geçilmeli.
    client = GeminiClient("gemini-test", api_key="test-key")
    options = client._client._api_client._http_options.retry_options
    assert options is not None and options.http_status_codes is not None
    assert 429 not in options.http_status_codes
    assert 503 in options.http_status_codes
