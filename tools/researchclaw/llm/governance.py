"""Project-rule enforcement at the common LLM call boundary."""

from __future__ import annotations

from typing import Any


AGENTS_PROMPT_MARKER = "## Authoritative Workspace AGENTS.md"


class GovernedLLMClient:
    """Proxy that injects workspace rules into otherwise ungoverned LLM calls."""

    def __init__(self, client: Any, agents_text: str) -> None:
        self._client = client
        self._policy = (
            f"{AGENTS_PROMPT_MARKER}\n"
            "These workspace rules are authoritative and must be followed.\n\n"
            f"{agents_text}"
        )

    def __getattr__(self, name: str) -> Any:
        return getattr(self._client, name)

    def chat(
        self,
        messages: list[dict[str, str]],
        *,
        model: str | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
        json_mode: bool = False,
        system: str | None = None,
        strip_thinking: bool = False,
    ) -> Any:
        """Delegate a chat call after adding policy if the prompt lacks it."""
        prompt_text = "\n".join(
            [system or "", *(message.get("content", "") for message in messages)]
        )
        governed_system = system
        if AGENTS_PROMPT_MARKER not in prompt_text:
            governed_system = (
                f"{system}\n\n{self._policy}" if system else self._policy
            )
        return self._client.chat(
            messages,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            json_mode=json_mode,
            system=governed_system,
            strip_thinking=strip_thinking,
        )
