"""Research Engine port — proposes the next AgentAction; never executes tools."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from sra.core.context import RunContext
from sra.models.actions import AgentAction
from sra.models.tools import ToolDescriptor


@runtime_checkable
class ResearchEngine(Protocol):
    """LLM reasoning boundary. Outputs typed actions for the Runtime to validate."""

    async def propose_action(
        self,
        ctx: RunContext,
        *,
        available_tools: list[ToolDescriptor],
    ) -> AgentAction:
        """Propose exactly one next action. Must not call tools itself."""
        ...
