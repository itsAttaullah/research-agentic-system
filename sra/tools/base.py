"""Convenience base class for tool plugins."""

from __future__ import annotations

from abc import ABC, abstractmethod

from pydantic import BaseModel

from sra.core.ports.tools import ToolContext


class BaseTool(ABC):
    """Implements the Tool protocol surface with declarative class attributes."""

    name: str
    description: str
    input_schema: type[BaseModel]
    output_schema: type[BaseModel]
    tags: list[str]

    @abstractmethod
    async def execute(self, payload: BaseModel, ctx: ToolContext) -> BaseModel:
        """Perform the tool side effect."""
