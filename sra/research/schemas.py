"""LLM-facing draft schema for research-engine actions."""

from __future__ import annotations

from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field


class DraftAgentAction(BaseModel):
    """Loose draft that is normalized into a typed AgentAction."""

    kind: Literal[
        "invoke_tool",
        "update_plan",
        "reflect",
        "request_critic",
        "finalize",
    ]
    tool_name: str | None = None
    arguments: dict[str, Any] = Field(default_factory=dict)
    rationale: str = ""
    related_task_id: UUID | None = None
    reason: str = ""
    focus: str = ""
    summary: str = ""
    # update_plan carries a full plan object when needed
    plan: dict[str, Any] | None = None
