"""Default Budget Manager — enforces hard run limits."""

from __future__ import annotations

from sra.core.context import RunContext
from sra.core.errors import BudgetExceededError
from sra.core.time import utc_now
from sra.models.budget import BudgetLedger


class DefaultBudgetManager:
    """BudgetManager port: track usage on the run context and abort on exhaustion."""

    def ledger(self, ctx: RunContext) -> BudgetLedger:
        return ctx.budget

    async def record_iteration(self, ctx: RunContext) -> None:
        self._refresh_elapsed(ctx)
        ctx.budget.usage.iterations += 1
        ctx.budget.last_updated_at = utc_now()

    async def record_llm_usage(
        self,
        ctx: RunContext,
        *,
        tokens: int,
        cost_usd: float,
    ) -> None:
        self._refresh_elapsed(ctx)
        ctx.budget.usage.tokens += max(0, tokens)
        ctx.budget.usage.cost_usd += max(0.0, cost_usd)
        ctx.budget.usage.llm_calls += 1
        ctx.budget.last_updated_at = utc_now()

    async def record_tool_usage(
        self,
        ctx: RunContext,
        *,
        cost_usd: float = 0.0,
        sources_delta: int = 0,
    ) -> None:
        self._refresh_elapsed(ctx)
        ctx.budget.usage.tool_calls += 1
        ctx.budget.usage.cost_usd += max(0.0, cost_usd)
        ctx.budget.usage.sources_visited += max(0, sources_delta)
        ctx.budget.last_updated_at = utc_now()

    async def check_or_raise(self, ctx: RunContext) -> None:
        self._refresh_elapsed(ctx)
        if not ctx.budget.is_exhausted():
            return
        reason = ctx.budget.exhaustion_reason or self._detect_reason(ctx)
        ctx.budget.exhausted = True
        ctx.budget.exhaustion_reason = reason
        raise BudgetExceededError(reason, details=ctx.budget.model_dump(mode="json"))

    @staticmethod
    def _refresh_elapsed(ctx: RunContext) -> None:
        now = utc_now()
        ctx.budget.usage.elapsed_seconds = max(
            0.0,
            (now - ctx.budget.started_at).total_seconds(),
        )
        ctx.budget.last_updated_at = now

    @staticmethod
    def _detect_reason(ctx: RunContext) -> str:
        usage = ctx.budget.usage
        limits = ctx.budget.limits
        if usage.iterations >= limits.max_iterations:
            return "Iteration budget exhausted"
        if usage.tokens >= limits.max_tokens:
            return "Token budget exhausted"
        if usage.cost_usd >= limits.max_cost_usd:
            return "Cost budget exhausted"
        if (usage.elapsed_seconds / 60.0) >= limits.max_minutes:
            return "Time budget exhausted"
        if usage.sources_visited >= limits.max_sources:
            return "Source-visit budget exhausted"
        return "Budget exhausted"
