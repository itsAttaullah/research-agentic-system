"""Tool call / result envelopes exchanged between Runtime and Tool Registry."""

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from sra.core.time import utc_now


class ToolCall(BaseModel):
    """Validated request to invoke a tool (post-schema parse)."""

    call_id: UUID = Field(default_factory=uuid4)
    tool_name: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    related_task_id: UUID | None = None
    requested_at: datetime = Field(default_factory=utc_now)


class ToolResult(BaseModel):
    """Normalized tool outcome returned to the Runtime."""

    call_id: UUID
    tool_name: str
    success: bool
    output: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None
    duration_ms: float = 0.0
    completed_at: datetime = Field(default_factory=utc_now)
    cost_usd: float = 0.0
    tokens_used: int = 0


class ToolDescriptor(BaseModel):
    """Discovery metadata exposed to the Research Engine (no execute capability)."""

    name: str
    description: str
    input_schema_name: str
    output_schema_name: str
    tags: list[str] = Field(default_factory=list)
