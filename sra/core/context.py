"""RunContext: per-run mutable execution context owned by the Runtime.

No global agent state. Each research run gets its own RunContext.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID, uuid4

from sra.core.time import utc_now
from sra.models.budget import BudgetLedger, BudgetLimits
from sra.models.checkpoint import RunSnapshot
from sra.models.enums import AgentState
from sra.models.goal import ResearchGoal
from sra.models.memory import MemorySnapshot
from sra.models.plan import ResearchPlan, ResearchTask
from sra.models.reflection import ConfidenceMap, CritiqueResult, ReflectionResult
from sra.models.tools import ToolResult


@dataclass
class RunContext:
    """All mutable state for one research run.

    Collaborators receive this (or narrow views of it) via method arguments;
    they must not reach into process globals.
    """

    goal: ResearchGoal
    run_id: UUID = field(default_factory=uuid4)
    state: AgentState = AgentState.IDLE
    plan: ResearchPlan | None = None
    tasks: list[ResearchTask] = field(default_factory=list)
    memory: MemorySnapshot = field(default_factory=MemorySnapshot)
    confidence: ConfidenceMap = field(default_factory=ConfidenceMap)
    last_reflection: ReflectionResult | None = None
    last_critique: CritiqueResult | None = None
    budget: BudgetLedger = field(default_factory=BudgetLedger)
    tool_history: list[ToolResult] = field(default_factory=list)
    knowledge_version: int = 0
    error_message: str | None = None
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)

    @classmethod
    def create(
        cls,
        goal: ResearchGoal,
        *,
        limits: BudgetLimits | None = None,
    ) -> RunContext:
        budget = BudgetLedger(limits=limits or BudgetLimits())
        ctx = cls(goal=goal, budget=budget)
        ctx.memory.working.objective = goal.question
        return ctx

    def to_snapshot(self) -> RunSnapshot:
        return RunSnapshot(
            run_id=self.run_id,
            state=self.state,
            goal=self.goal,
            plan=self.plan,
            tasks=list(self.tasks),
            memory=self.memory,
            confidence=self.confidence,
            last_reflection=self.last_reflection,
            last_critique=self.last_critique,
            budget=self.budget,
            tool_history=list(self.tool_history),
            knowledge_version=self.knowledge_version,
            error_message=self.error_message,
        )

    @classmethod
    def from_snapshot(cls, snapshot: RunSnapshot) -> RunContext:
        return cls(
            run_id=snapshot.run_id,
            goal=snapshot.goal,
            state=snapshot.state,
            plan=snapshot.plan,
            tasks=list(snapshot.tasks),
            memory=snapshot.memory,
            confidence=snapshot.confidence,
            last_reflection=snapshot.last_reflection,
            last_critique=snapshot.last_critique,
            budget=snapshot.budget,
            tool_history=list(snapshot.tool_history),
            knowledge_version=snapshot.knowledge_version,
            error_message=snapshot.error_message,
            updated_at=utc_now(),
        )

    def touch(self) -> None:
        self.updated_at = utc_now()
        self.budget.last_updated_at = utc_now()
