"""Budget ledger and limit models enforced by the Budget Manager."""

from datetime import datetime

from pydantic import BaseModel, Field

from sra.core.time import utc_now


class BudgetLimits(BaseModel):
    """Hard caps for a research run. Exceeding any limit aborts the run."""

    max_iterations: int = Field(default=40, ge=1)
    max_tokens: int = Field(default=500_000, ge=1)
    max_cost_usd: float = Field(default=5.0, ge=0.0)
    max_minutes: float = Field(default=30.0, gt=0.0)
    max_sources: int = Field(default=60, ge=1)


class BudgetUsage(BaseModel):
    """Cumulative consumption counters."""

    iterations: int = 0
    tokens: int = 0
    cost_usd: float = 0.0
    elapsed_seconds: float = 0.0
    sources_visited: int = 0
    tool_calls: int = 0
    llm_calls: int = 0


class BudgetLedger(BaseModel):
    """Limits + usage + timestamps for observability and abort decisions."""

    limits: BudgetLimits = Field(default_factory=BudgetLimits)
    usage: BudgetUsage = Field(default_factory=BudgetUsage)
    started_at: datetime = Field(default_factory=utc_now)
    last_updated_at: datetime = Field(default_factory=utc_now)
    exhausted: bool = False
    exhaustion_reason: str = ""

    def remaining_iterations(self) -> int:
        return max(0, self.limits.max_iterations - self.usage.iterations)

    def is_exhausted(self) -> bool:
        u, lim = self.usage, self.limits
        return (
            self.exhausted
            or u.iterations >= lim.max_iterations
            or u.tokens >= lim.max_tokens
            or u.cost_usd >= lim.max_cost_usd
            or (u.elapsed_seconds / 60.0) >= lim.max_minutes
            or u.sources_visited >= lim.max_sources
        )
