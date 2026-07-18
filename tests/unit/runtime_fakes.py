"""Deterministic collaborators for runtime unit tests."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any
from uuid import UUID

from pydantic import BaseModel
from sra.core.context import RunContext
from sra.core.errors import BudgetExceededError, ToolNotFoundError
from sra.models.actions import AgentAction
from sra.models.checkpoint import RunSnapshot
from sra.models.enums import AgentState, ReportFormat
from sra.models.plan import ResearchPlan, ResearchTask
from sra.models.reflection import (
    ConfidenceMap,
    CritiqueResult,
    ReflectionResult,
    TopicConfidence,
)
from sra.models.reporting import ReportArtifact, ReportDocument
from sra.models.tools import ToolCall, ToolDescriptor, ToolResult


class FakePlanner:
    def __init__(self) -> None:
        self.created = 0
        self.revised = 0

    async def create_plan(self, ctx: RunContext) -> ResearchPlan:
        self.created += 1
        return ResearchPlan(goal_summary=ctx.goal.question)

    async def revise_plan(
        self,
        ctx: RunContext,
        *,
        reason: str,
        reflection: ReflectionResult | None = None,
        critique: CritiqueResult | None = None,
    ) -> ResearchPlan:
        self.revised += 1
        current = ctx.plan or ResearchPlan(goal_summary=ctx.goal.question)
        return current.model_copy(update={"version": current.version + 1})


class FakeTaskManager:
    def __init__(self) -> None:
        self.enqueued: list[str] = []

    async def sync_tasks(self, ctx: RunContext) -> list[ResearchTask]:
        return list(ctx.tasks)

    async def next_task(self, ctx: RunContext) -> ResearchTask | None:
        return None

    async def mark_done(self, ctx: RunContext, task_id: UUID) -> None:
        return None

    async def enqueue_from_questions(
        self,
        ctx: RunContext,
        questions: list[str],
        *,
        priority: int = 60,
    ) -> list[ResearchTask]:
        self.enqueued.extend(questions)
        return []


class FakeResearchEngine:
    def __init__(self, actions: Sequence[AgentAction]) -> None:
        self.actions = list(actions)
        self.calls = 0

    async def propose_action(
        self,
        ctx: RunContext,
        *,
        available_tools: list[ToolDescriptor],
    ) -> AgentAction:
        self.calls += 1
        if not self.actions:
            raise AssertionError("FakeResearchEngine ran out of actions")
        return self.actions.pop(0)


class EmptyInput(BaseModel):
    query: str = ""


class EmptyOutput(BaseModel):
    value: str = ""


class FakeTool:
    def __init__(self, name: str, *, tags: list[str] | None = None) -> None:
        self._name = name
        self._tags = tags or []

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return f"Fake {self._name}"

    @property
    def input_schema(self) -> type[BaseModel]:
        return EmptyInput

    @property
    def output_schema(self) -> type[BaseModel]:
        return EmptyOutput

    @property
    def tags(self) -> list[str]:
        return self._tags

    async def execute(self, payload: BaseModel, ctx: Any) -> BaseModel:
        return EmptyOutput(value="ok")


class FakeToolRegistry:
    def __init__(self, *tools: FakeTool) -> None:
        self.tools = {tool.name: tool for tool in tools}
        self.calls: list[ToolCall] = []

    def register(self, tool: FakeTool) -> None:
        self.tools[tool.name] = tool

    def get(self, name: str) -> FakeTool:
        try:
            return self.tools[name]
        except KeyError as exc:
            raise ToolNotFoundError(f"Unknown tool: {name}") from exc

    def list_descriptors(self) -> list[ToolDescriptor]:
        return [
            ToolDescriptor(
                name=tool.name,
                description=tool.description,
                input_schema_name=tool.input_schema.__name__,
                output_schema_name=tool.output_schema.__name__,
                tags=tool.tags,
            )
            for tool in self.tools.values()
        ]

    async def execute(self, call: ToolCall, *, run_id: UUID) -> ToolResult:
        self.calls.append(call)
        return ToolResult(
            call_id=call.call_id,
            tool_name=call.tool_name,
            success=True,
            output={"value": "ok"},
        )

    def describe_for_prompt(self) -> list[dict[str, Any]]:
        return [descriptor.model_dump() for descriptor in self.list_descriptors()]


class FakeReflection:
    def __init__(self, *results: ReflectionResult) -> None:
        self.results = list(results)
        self.calls = 0

    async def reflect(
        self,
        ctx: RunContext,
        *,
        latest_tool_result: ToolResult | None = None,
    ) -> ReflectionResult:
        self.calls += 1
        if self.results:
            return self.results.pop(0)
        return ReflectionResult()


class FakeCritic:
    def __init__(self, *results: CritiqueResult) -> None:
        self.results = list(results)
        self.calls = 0

    async def critique(self, ctx: RunContext) -> CritiqueResult:
        self.calls += 1
        if self.results:
            return self.results.pop(0)
        return CritiqueResult(passed=True)


class FakeConfidence:
    async def estimate(self, ctx: RunContext) -> ConfidenceMap:
        return ConfidenceMap(
            topics=[TopicConfidence(topic="overall", score=0.9)],
            overall=0.9,
        )

    def below_threshold(
        self,
        confidence: ConfidenceMap,
        *,
        threshold: float,
    ) -> list[str]:
        return [topic.topic for topic in confidence.topics if topic.score < threshold]


class FakeBudget:
    def ledger(self, ctx: RunContext) -> Any:
        return ctx.budget

    async def record_iteration(self, ctx: RunContext) -> None:
        ctx.budget.usage.iterations += 1

    async def record_llm_usage(
        self,
        ctx: RunContext,
        *,
        tokens: int,
        cost_usd: float,
    ) -> None:
        ctx.budget.usage.tokens += tokens
        ctx.budget.usage.cost_usd += cost_usd

    async def record_tool_usage(
        self,
        ctx: RunContext,
        *,
        cost_usd: float = 0.0,
        sources_delta: int = 0,
    ) -> None:
        ctx.budget.usage.tool_calls += 1
        ctx.budget.usage.cost_usd += cost_usd
        ctx.budget.usage.sources_visited += sources_delta

    async def check_or_raise(self, ctx: RunContext) -> None:
        if ctx.budget.usage.iterations >= ctx.budget.limits.max_iterations:
            raise BudgetExceededError("Iteration budget exhausted")


class FakeCheckpoints:
    def __init__(self) -> None:
        self.snapshots: list[RunSnapshot] = []

    async def save(self, ctx: RunContext) -> RunSnapshot:
        snapshot = ctx.to_snapshot().model_copy(deep=True)
        self.snapshots.append(snapshot)
        return snapshot

    async def latest(self, run_id: UUID) -> RunSnapshot | None:
        matches = [snapshot for snapshot in self.snapshots if snapshot.run_id == run_id]
        return matches[-1] if matches else None

    async def load(self, snapshot_id: UUID) -> RunSnapshot:
        return next(item for item in self.snapshots if item.snapshot_id == snapshot_id)

    async def list_for_run(self, run_id: UUID) -> list[RunSnapshot]:
        return [snapshot for snapshot in self.snapshots if snapshot.run_id == run_id]


class FakeLogger:
    def __init__(self) -> None:
        self.events: list[tuple[str, str]] = []
        self.transitions: list[tuple[AgentState, AgentState]] = []

    async def log(
        self,
        ctx: RunContext,
        event_type: str,
        message: str,
        *,
        data: dict[str, Any] | None = None,
    ) -> None:
        self.events.append((event_type, message))

    async def state_transition(
        self,
        ctx: RunContext,
        *,
        from_state: AgentState,
        to_state: AgentState,
    ) -> None:
        self.transitions.append((from_state, to_state))


class FakeReports:
    def __init__(self) -> None:
        self.rendered: list[ReportFormat] = []

    async def build(self, ctx: RunContext) -> ReportDocument:
        return ReportDocument(run_id=ctx.run_id, title=ctx.goal.question)

    async def render(
        self,
        document: ReportDocument,
        *,
        fmt: ReportFormat,
    ) -> ReportArtifact:
        self.rendered.append(fmt)
        return ReportArtifact(
            report_id=document.report_id,
            run_id=document.run_id,
            format=fmt,
            content="report",
        )


class UnusedMemory:
    """Runtime does not directly manipulate memory storage in this phase."""
