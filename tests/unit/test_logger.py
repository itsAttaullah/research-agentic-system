"""Unit tests for the structured execution logger."""

from __future__ import annotations

from typing import Any

import pytest
from sra.core.context import RunContext
from sra.models.enums import AgentState
from sra.models.goal import ResearchGoal
from sra.observability import StructlogExecutionLogger


class CapturingLogger:
    def __init__(self) -> None:
        self.events: list[dict[str, Any]] = []

    def info(self, message: str, **kwargs: Any) -> None:
        self.events.append({"message": message, **kwargs})


@pytest.mark.asyncio
async def test_structlog_execution_logger_emits_events() -> None:
    capture = CapturingLogger()
    logger = StructlogExecutionLogger(capture)
    ctx = RunContext.create(ResearchGoal(question="Log me"))

    await logger.log(ctx, "agent_action", "hello", data={"k": 1})
    await logger.state_transition(
        ctx,
        from_state=AgentState.IDLE,
        to_state=AgentState.PLANNING,
    )

    assert capture.events[0]["event_type"] == "agent_action"
    assert capture.events[0]["data"] == {"k": 1}
    assert capture.events[1]["event_type"] == "state_transition"
    assert "idle" in capture.events[1]["message"]
