"""Structured + human-readable execution logger."""

from __future__ import annotations

from typing import Any

import structlog

from sra.core.context import RunContext
from sra.models.enums import AgentState

_logger = structlog.get_logger("sra.runtime")


class StructlogExecutionLogger:
    """ExecutionLogger port backed by structlog."""

    def __init__(self, logger: Any | None = None) -> None:
        self._logger = logger or _logger

    async def log(
        self,
        ctx: RunContext,
        event_type: str,
        message: str,
        *,
        data: dict[str, Any] | None = None,
    ) -> None:
        self._logger.info(
            message,
            event_type=event_type,
            run_id=str(ctx.run_id),
            state=ctx.state.value,
            data=data or {},
        )

    async def state_transition(
        self,
        ctx: RunContext,
        *,
        from_state: AgentState,
        to_state: AgentState,
    ) -> None:
        self._logger.info(
            f"State transition: {from_state.value} -> {to_state.value}",
            event_type="state_transition",
            run_id=str(ctx.run_id),
            from_state=from_state.value,
            to_state=to_state.value,
        )
