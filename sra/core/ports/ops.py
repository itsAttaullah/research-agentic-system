"""Budget, Checkpoint, Logger, and Report ports."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable
from uuid import UUID

from sra.core.context import RunContext
from sra.models.budget import BudgetLedger
from sra.models.checkpoint import RunSnapshot
from sra.models.enums import AgentState, ReportFormat
from sra.models.reporting import ReportArtifact, ReportDocument


@runtime_checkable
class BudgetManager(Protocol):
    """Tracks consumption and enforces hard abort limits."""

    def ledger(self, ctx: RunContext) -> BudgetLedger: ...

    async def record_iteration(self, ctx: RunContext) -> None: ...

    async def record_llm_usage(
        self,
        ctx: RunContext,
        *,
        tokens: int,
        cost_usd: float,
    ) -> None: ...

    async def record_tool_usage(
        self,
        ctx: RunContext,
        *,
        cost_usd: float = 0.0,
        sources_delta: int = 0,
    ) -> None: ...

    async def check_or_raise(self, ctx: RunContext) -> None:
        """Raise BudgetExceededError if any limit is exhausted."""
        ...


@runtime_checkable
class CheckpointManager(Protocol):
    """Persist and restore RunSnapshots."""

    async def save(self, ctx: RunContext) -> RunSnapshot: ...

    async def latest(self, run_id: UUID) -> RunSnapshot | None: ...

    async def load(self, snapshot_id: UUID) -> RunSnapshot: ...

    async def list_for_run(self, run_id: UUID) -> list[RunSnapshot]: ...


@runtime_checkable
class ExecutionLogger(Protocol):
    """Human-readable + structured audit trail."""

    async def log(
        self,
        ctx: RunContext,
        event_type: str,
        message: str,
        *,
        data: dict[str, Any] | None = None,
    ) -> None: ...

    async def state_transition(
        self,
        ctx: RunContext,
        *,
        from_state: AgentState,
        to_state: AgentState,
    ) -> None: ...


@runtime_checkable
class ReportGenerator(Protocol):
    """Render knowledge into professional reports. No new research."""

    async def build(self, ctx: RunContext) -> ReportDocument: ...

    async def render(
        self,
        document: ReportDocument,
        *,
        fmt: ReportFormat,
    ) -> ReportArtifact: ...
