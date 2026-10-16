import threading
from typing import Any

from app.llm.task_router import TaskRoutedLLMClient


class _StubLLM:
    def __init__(self, name: str) -> None:
        self.model_name = name
        self.calls: list[str] = []

    def parse_cv(self, cv_text: str) -> dict[str, Any]:
        self.calls.append("parse")
        return {}

    def score_cv(
        self, anonymized_cv: str, criteria: list[dict[str, str]], profile: dict[str, Any]
    ) -> dict[str, Any]:
        self.calls.append("score")
        return {}


def test_parse_and_score_go_to_their_own_clients() -> None:
    groq, gemini = _StubLLM("groq"), _StubLLM("gemini")
    client = TaskRoutedLLMClient(parse_client=groq, score_client=gemini)

    client.parse_cv("cv")
    assert client.model_name == "groq"
    client.score_cv("cv", [], {})
    assert client.model_name == "gemini"

    assert groq.calls == ["parse"]
    assert gemini.calls == ["score"]


def test_model_name_is_tracked_per_thread() -> None:
    client = TaskRoutedLLMClient(parse_client=_StubLLM("groq"), score_client=_StubLLM("gemini"))
    client.score_cv("cv", [], {})
    seen: list[str] = []

    thread = threading.Thread(target=lambda: seen.append(client.model_name))
    thread.start()
    thread.join()

    assert client.model_name == "gemini"
    assert seen == ["groq"]
