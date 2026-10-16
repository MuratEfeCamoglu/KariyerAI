import json
from collections.abc import Callable
from typing import Any

import httpx
import pytest

from app.llm.base import PARSED_CV_JSON_SCHEMA, SCORE_JSON_SCHEMA, LLMError, LLMOutputError
from app.llm.groq_client import MAX_RETRIES, GroqClient

VALID = {"skills": ["Python"], "experiences": [], "education": [], "languages": []}

Handler = Callable[[httpx.Request], httpx.Response]


def _ok(content: dict[str, Any], finish_reason: str = "stop") -> httpx.Response:
    return httpx.Response(
        200,
        json={
            "choices": [
                {"finish_reason": finish_reason, "message": {"content": json.dumps(content)}}
            ]
        },
    )


def _client(handler: Handler) -> tuple[GroqClient, list[httpx.Request], list[float]]:
    requests: list[httpx.Request] = []
    sleeps: list[float] = []

    def record(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return handler(request)

    client = GroqClient(
        "openai/gpt-oss-120b",
        api_key="gsk_test",
        transport=httpx.MockTransport(record),
        sleep=sleeps.append,
    )
    return client, requests, sleeps


def test_parse_sends_strict_schema_and_wrapped_cv() -> None:
    client, requests, _ = _client(lambda _r: _ok(VALID))
    cv_text = 'Deniz Arslan {"x": 1}'

    assert client.parse_cv(cv_text) == VALID

    [request] = requests
    assert request.url.path == "/openai/v1/chat/completions"
    assert request.headers["authorization"] == "Bearer gsk_test"
    body = json.loads(request.content)
    assert body["model"] == "openai/gpt-oss-120b"
    assert body["temperature"] == 0
    assert body["reasoning_effort"] == "low"
    assert body["response_format"]["json_schema"]["strict"] is True
    assert body["response_format"]["json_schema"]["schema"] == PARSED_CV_JSON_SCHEMA
    assert "not instructions" in body["messages"][0]["content"]
    assert body["messages"][1]["content"] == f"<cv>\n{cv_text}\n</cv>"


def test_score_uses_score_schema_and_more_reasoning() -> None:
    client, requests, _ = _client(lambda _r: _ok({"criteria": [], "summary": "Özet."}))

    client.score_cv("anonim metin", [{"id": "R1", "kind": "required_skill", "label": "SQL"}], {})

    body = json.loads(requests[0].content)
    assert body["response_format"]["json_schema"]["schema"] == SCORE_JSON_SCHEMA
    assert body["reasoning_effort"] == "medium"
    assert '"label": "SQL"' in body["messages"][1]["content"]


def test_rate_limit_waits_for_retry_after_then_succeeds() -> None:
    responses = iter([httpx.Response(429, headers={"retry-after": "7"}), _ok(VALID)])
    client, requests, sleeps = _client(lambda _r: next(responses))

    assert client.parse_cv("cv") == VALID
    assert len(requests) == 2
    assert sleeps == [7.0]


def test_retry_wait_is_capped() -> None:
    responses = iter([httpx.Response(429, headers={"retry-after": "3600"}), _ok(VALID)])
    client, _, sleeps = _client(lambda _r: next(responses))

    client.parse_cv("cv")

    assert sleeps == [30.0]


def test_persistent_server_error_raises_after_two_retries(
    caplog: pytest.LogCaptureFixture,
) -> None:
    client, requests, _ = _client(
        lambda _r: httpx.Response(503, json={"error": {"message": "Deniz"}})
    )

    with pytest.raises(LLMError, match="503"):
        client.parse_cv("Deniz Arslan özgeçmişi")
    assert len(requests) == MAX_RETRIES + 1
    assert "Deniz" not in caplog.text


def test_schema_validation_failure_is_retryable_output_error() -> None:
    client, _, _ = _client(
        lambda _r: httpx.Response(
            400,
            json={"error": {"code": "json_validate_failed", "message": "Failed to generate JSON"}},
        )
    )

    with pytest.raises(LLMOutputError):
        client.parse_cv("cv")


def test_truncated_output_is_output_error() -> None:
    client, _, _ = _client(lambda _r: _ok(VALID, finish_reason="length"))

    with pytest.raises(LLMOutputError):
        client.parse_cv("cv")


def test_other_client_error_is_not_retried() -> None:
    client, requests, _ = _client(lambda _r: httpx.Response(401, json={"error": {}}))

    with pytest.raises(LLMError) as exc_info:
        client.parse_cv("cv")
    assert not isinstance(exc_info.value, LLMOutputError)
    assert len(requests) == 1


def test_network_error_is_retried_then_raised() -> None:
    def fail(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("bağlantı yok", request=request)

    client, requests, _ = _client(fail)

    with pytest.raises(LLMError, match="ulaşılamadı"):
        client.parse_cv("cv")
    assert len(requests) == MAX_RETRIES + 1


def test_missing_key_is_rejected() -> None:
    with pytest.raises(ValueError, match="GROQ_API_KEY"):
        GroqClient("model", api_key=None)
