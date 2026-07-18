"""Unit tests for domain models and state-machine transition table."""

from __future__ import annotations

import pytest
from sra.core.context import RunContext
from sra.core.errors import StateTransitionError
from sra.core.state_machine import assert_transition, can_transition
from sra.models import (
    AgentState,
    BudgetLimits,
    InvokeToolAction,
    ResearchGoal,
    ResearchPlan,
    SourceRecord,
    TrustTier,
)


def test_research_goal_and_run_context() -> None:
    goal = ResearchGoal(question="Should I build an AI startup for dentists?")
    ctx = RunContext.create(goal, limits=BudgetLimits(max_iterations=10))
    assert ctx.state is AgentState.IDLE
    assert ctx.memory.working.objective == goal.question
    assert ctx.budget.limits.max_iterations == 10
    snap = ctx.to_snapshot()
    restored = RunContext.from_snapshot(snap)
    assert restored.run_id == ctx.run_id
    assert restored.goal.question == goal.question


def test_illegal_state_transition_raises() -> None:
    with pytest.raises(StateTransitionError):
        assert_transition(AgentState.IDLE, AgentState.COMPLETED)
    assert can_transition(AgentState.IDLE, AgentState.PLANNING)
    assert not can_transition(AgentState.COMPLETED, AgentState.PLANNING)


def test_invoke_tool_action_discriminator() -> None:
    action = InvokeToolAction(
        tool_name="google_search",
        arguments={"query": "dental AI market size"},
        rationale="Need TAM estimate",
    )
    assert action.kind.value == "invoke_tool"
    assert action.tool_name == "google_search"


def test_source_identity_key_prefers_hash() -> None:
    source = SourceRecord(
        url="https://Example.com/Report/",
        content_hash="abc123",
        trust_tier=TrustTier.TRUSTED_PUBLICATION,
    )
    assert source.identity_key() == "hash:abc123"


def test_research_plan_active_investigations() -> None:
    plan = ResearchPlan(goal_summary="dental AI startup feasibility")
    assert plan.version == 1
    assert plan.active_investigations() == []
