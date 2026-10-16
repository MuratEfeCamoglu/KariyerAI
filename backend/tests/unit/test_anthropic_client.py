import json
from types import SimpleNamespace
from typing import Any, cast

import anthropic
import httpx2
import pytest

from app.llm.anthropic_client import PARSED_CV_JSON_SCHEMA, AnthropicClient
from app.llm.base import LLMError, LLMOutputError, LLMRefusalError, load_prompt
from app.schemas.parsed_cv import ParsedCV

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
    stop_reason: str = "end_turn",
    category: str | None = None,
) -> SimpleNamespace:
    content: list[SimpleNamespace] = [SimpleNamespace(type="thinking", thinking="")]
    if text is not None:
        content.append(SimpleNamespace(type="text", text=text))
    stop_details = SimpleNamespace(category=category) if stop_reason == "refusal" else None
    return SimpleNamespace(content=content, stop_reason=stop_reason, stop_details=stop_details)


class _StubMessages:
    def __init__(self, result: SimpleNamespace | Exception) -> None:
        self.result = result
        self.kwargs: dict[str, Any] = {}

    def create(self, **kwargs: Any) -> SimpleNamespace:
        self.kwargs = kwargs
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


def _client(result: SimpleNamespace | Exception) -> tuple[AnthropicClient, _StubMessages]:
    messages = _StubMessages(result)
    sdk = SimpleNamespace(beta=SimpleNamespace(messages=messages))
    return AnthropicClient("claude-sonnet-5-5", client=cast(anthropic.Anthropic, sdk)), messages


def test_request_wraps_cv_as_data_and_uses_structured_output() -> None:
    client, messages = _client(_response(text=json.dumps(VALID_OUTPUT)))
    cv_text = 'Deniz Arslan\nSkills: Python {"not": "a template"}'

    result = client.parse_cv(cv_text)

    assert result == VALID_OUTPUT
    sent = messages.kwargs
    assert sent["model"] == "claude-sonnet-5-5"
    assert sent["messages"] == [{"role": "user", "content": f"<cv>\n{cv_text}\n</cv>"}]
    assert "not instructions" in sent["system"]
    assert sent["output_config"]["format"] == {
        "type": "json_schema",
        "schema": PARSED_CV_JSON_SCHEMA,
    }
    assert sent["output_config"]["effort"] == "low"
    assert sent["fallbacks"] == "default"
    assert sent["betas"] == ["server-side-fallback-2026-07-01"]
    # Sonnet 5.5'te thinking kapatılamaz; parametre gönderilmez.
    assert "thinking" not in sent


def test_schema_has_no_protected_attributes_and_matches_parsed_cv() -> None:
    properties = set(PARSED_CV_JSON_SCHEMA["properties"])

    assert properties == set(ParsedCV.model_fields) - {"total_experience_years"}
    forbidden = {
        "age",
        "birth_date",
        "gender",
        "marital_status",
        "religion",
        "nationality",
        "photo",
    }
    assert not forbidden & properties


def test_prompt_forbids_protected_attributes_and_injection() -> None:
    prompt = load_prompt("parse_v1")

    assert "<cv>" in prompt.system and "not instructions" in prompt.system
    for word in ("age", "gender", "marital status", "religion", "nationality", "photo"):
        assert word in prompt.system
    assert prompt.render_user(cv_text="X") == "<cv>\nX\n</cv>"


def test_refusal_raises_refusal_error() -> None:
    client, _ = _client(_response(stop_reason="refusal", category="general_harms"))

    with pytest.raises(LLMRefusalError):
        client.parse_cv("cv")


@pytest.mark.parametrize(
    "response",
    [
        _response(text='{"skills": ["Pyth', stop_reason="max_tokens"),
        _response(text="bu json değil"),
        _response(text="[1, 2]"),
        _response(text=None),
    ],
)
def test_unusable_output_raises_output_error(response: SimpleNamespace) -> None:
    client, _ = _client(response)

    with pytest.raises(LLMOutputError):
        client.parse_cv("cv")


def test_connection_error_becomes_llm_error() -> None:
    error = anthropic.APIConnectionError(request=httpx2.Request("POST", "https://api.example"))
    client, _ = _client(error)

    with pytest.raises(LLMError) as exc_info:
        client.parse_cv("cv")
    assert not isinstance(exc_info.value, LLMOutputError)


def test_status_error_becomes_llm_error_without_leaking_body(
    caplog: pytest.LogCaptureFixture,
) -> None:
    request = httpx2.Request("POST", "https://api.example")
    response = httpx2.Response(500, request=request, headers={"request-id": "req_123"})
    error = anthropic.InternalServerError("hata", response=response, body={"cv": "Deniz Arslan"})
    client, _ = _client(error)

    with pytest.raises(LLMError, match="500"):
        client.parse_cv("Deniz Arslan özgeçmişi")
    assert "Deniz" not in caplog.text
