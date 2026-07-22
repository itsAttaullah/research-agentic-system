"""Unit tests for the default budget manager."""

from __future__ import annotations

import pytest
from sra.budget import DefaultBudgetManager
from sra.core.context import RunContext
from sra.core.errors import BudgetExceededError
from sra.models.budget import BudgetLimits
from sra.models.goal import ResearchGoal


@pytest.mark.asyncio
async def test_budget_tracks_usage_and_raises_on_iteration_limit() -> None:
    manager = DefaultBudgetManager()
    ctx = RunContext.create(
        ResearchGoal(question="Test budget"),
        limits=BudgetLimits(max_iterations=2),
    )

    await manager.check_or_raise(ctx)
    await manager.record_iteration(ctx)
    await manager.record_llm_usage(ctx, tokens=100, cost_usd=0.01)
    await manager.record_tool_usage(ctx, cost_usd=0.02, sources_delta=1)
    assert ctx.budget.usage.iterations == 1
    assert ctx.budget.usage.tokens == 100
    assert ctx.budget.usage.tool_calls == 1
    assert ctx.budget.usage.sources_visited == 1

    await manager.record_iteration(ctx)
    with pytest.raises(BudgetExceededError, match="Iteration"):
        await manager.check_or_raise(ctx)
