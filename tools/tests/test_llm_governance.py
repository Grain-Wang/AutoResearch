from __future__ import annotations

from typing import Any

from researchclaw.llm.governance import AGENTS_PROMPT_MARKER, GovernedLLMClient


class RecordingClient:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def chat(self, messages: list[dict[str, str]], **kwargs: Any) -> str:
        self.calls.append({"messages": messages, **kwargs})
        return "ok"


def test_direct_chat_receives_authoritative_workspace_rules() -> None:
    inner = RecordingClient()
    client = GovernedLLMClient(inner, "DIRECT_RULE_456")

    assert client.chat([{"role": "user", "content": "work"}]) == "ok"

    system = inner.calls[0]["system"]
    assert AGENTS_PROMPT_MARKER in system
    assert "DIRECT_RULE_456" in system


def test_already_governed_prompt_is_not_duplicated() -> None:
    inner = RecordingClient()
    client = GovernedLLMClient(inner, "DIRECT_RULE_456")
    content = f"{AGENTS_PROMPT_MARKER}\nDIRECT_RULE_456"

    client.chat([{"role": "user", "content": content}], system="stage system")

    assert inner.calls[0]["system"] == "stage system"
