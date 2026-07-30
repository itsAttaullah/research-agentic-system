"""In-process tool registry with schema validation and sandboxed execution."""

from __future__ import annotations

import time
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ValidationError

from sra.core.errors import (
    ConfigurationError,
    ToolExecutionError,
    ToolNotFoundError,
    ToolValidationError,
)
from sra.core.ports.tools import Tool, ToolContext
from sra.core.time import utc_now
from sra.models.tools import ToolCall, ToolDescriptor, ToolResult


class InMemoryToolRegistry:
    """Concrete ToolRegistry: catalog + validate + execute + validate."""

    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        if not tool.name.strip():
            raise ToolValidationError("Tool name cannot be empty")
        if tool.name in self._tools:
            raise ToolValidationError(
                f"Tool already registered: {tool.name}",
                details={"tool_name": tool.name},
            )
        self._tools[tool.name] = tool

    def get(self, name: str) -> Tool:
        try:
            return self._tools[name]
        except KeyError as exc:
            raise ToolNotFoundError(
                f"Tool is not registered: {name}",
                details={"tool_name": name},
            ) from exc

    def list_descriptors(self) -> list[ToolDescriptor]:
        return [
            ToolDescriptor(
                name=tool.name,
                description=tool.description,
                input_schema_name=tool.input_schema.__name__,
                output_schema_name=tool.output_schema.__name__,
                tags=list(tool.tags),
            )
            for tool in sorted(self._tools.values(), key=lambda item: item.name)
        ]

    def describe_for_prompt(self) -> list[dict[str, Any]]:
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "tags": list(tool.tags),
                "input_fields": sorted(tool.input_schema.model_fields.keys()),
            }
            for tool in sorted(self._tools.values(), key=lambda item: item.name)
        ]

    async def execute(self, call: ToolCall, *, run_id: UUID) -> ToolResult:
        started = time.perf_counter()
        try:
            tool = self.get(call.tool_name)
            payload = self._parse_input(tool, call.arguments)
            ctx = ToolContext(run_id=run_id, call_id=call.call_id)
            output = await tool.execute(payload, ctx)
            validated = self._parse_output(tool, output)
            return ToolResult(
                call_id=call.call_id,
                tool_name=call.tool_name,
                success=True,
                output=validated.model_dump(mode="json"),
                duration_ms=(time.perf_counter() - started) * 1000.0,
                completed_at=utc_now(),
            )
        except (
            ToolNotFoundError,
            ToolValidationError,
            ToolExecutionError,
            ConfigurationError,
        ) as exc:
            message = exc.message if hasattr(exc, "message") else str(exc)
            return ToolResult(
                call_id=call.call_id,
                tool_name=call.tool_name,
                success=False,
                error=message,
                duration_ms=(time.perf_counter() - started) * 1000.0,
                completed_at=utc_now(),
            )
        except Exception as exc:  # noqa: BLE001 - convert unexpected tool crashes
            return ToolResult(
                call_id=call.call_id,
                tool_name=call.tool_name,
                success=False,
                error=f"Unexpected tool failure: {exc}",
                duration_ms=(time.perf_counter() - started) * 1000.0,
                completed_at=utc_now(),
            )

    @staticmethod
    def _parse_input(tool: Tool, arguments: dict[str, Any]) -> BaseModel:
        try:
            return tool.input_schema.model_validate(arguments)
        except ValidationError as exc:
            raise ToolValidationError(
                f"Invalid arguments for tool {tool.name}",
                details={"errors": exc.errors()},
            ) from exc

    @staticmethod
    def _parse_output(tool: Tool, output: BaseModel | dict[str, Any]) -> BaseModel:
        try:
            if isinstance(output, tool.output_schema):
                return output
            if isinstance(output, BaseModel):
                return tool.output_schema.model_validate(output.model_dump())
            return tool.output_schema.model_validate(output)
        except ValidationError as exc:
            raise ToolValidationError(
                f"Invalid output from tool {tool.name}",
                details={"errors": exc.errors()},
            ) from exc
