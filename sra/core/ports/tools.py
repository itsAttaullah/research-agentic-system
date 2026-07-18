"""Tool protocol and registry port."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable
from uuid import UUID

from pydantic import BaseModel

from sra.models.tools import ToolCall, ToolDescriptor, ToolResult


class ToolContext(BaseModel):
    """Execution context passed into every tool (budget-aware, no secrets dump)."""

    run_id: UUID
    call_id: UUID
    timeout_seconds: float = 60.0
    max_response_bytes: int = 2_000_000


@runtime_checkable
class Tool(Protocol):
    """Pluggable tool. Implementations live under sra.tools.*; Runtime never
    imports them directly — only via ToolRegistry.
    """

    @property
    def name(self) -> str: ...

    @property
    def description(self) -> str: ...

    @property
    def input_schema(self) -> type[BaseModel]: ...

    @property
    def output_schema(self) -> type[BaseModel]: ...

    @property
    def tags(self) -> list[str]: ...

    async def execute(self, payload: BaseModel, ctx: ToolContext) -> BaseModel:
        """Perform the side effect. Raises ToolExecutionError on failure."""
        ...


@runtime_checkable
class ToolRegistry(Protocol):
    """Capability catalog + sandboxed execution entrypoint."""

    def register(self, tool: Tool) -> None: ...

    def get(self, name: str) -> Tool: ...

    def list_descriptors(self) -> list[ToolDescriptor]: ...

    async def execute(self, call: ToolCall, *, run_id: UUID) -> ToolResult:
        """Validate args against the tool schema, execute, validate output."""
        ...

    def describe_for_prompt(self) -> list[dict[str, Any]]:
        """Compact JSON-serializable tool list for LLM prompts."""
        ...
