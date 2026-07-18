"""LLM client port — OpenAI and Anthropic adapters implement this."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel, Field


class LLMMessage(BaseModel):
    role: str  # system | user | assistant | tool
    content: str


class LLMRequest(BaseModel):
    messages: list[LLMMessage]
    model: str | None = None
    temperature: float = 0.2
    max_tokens: int | None = None
    response_schema_name: str | None = Field(
        default=None,
        description="When set, the adapter should request structured output matching this name.",
    )
    metadata: dict[str, Any] = Field(default_factory=dict)


class LLMResponse(BaseModel):
    content: str
    raw_json: dict[str, Any] | None = None
    model: str = ""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    cost_usd: float = 0.0


@runtime_checkable
class LLMClient(Protocol):
    """Port for chat/completions used by Planner, Engine, Reflection, Critic."""

    async def complete(self, request: LLMRequest) -> LLMResponse:
        """Return a completion. Raises LLMError on provider failure."""
        ...
