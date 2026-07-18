"""Behavior tests for the provider-independent research runtime."""

from __future__ import annotations

import pytest
from sra.core.errors import InvalidActionError
from sra.models.actions import FinalizeAction, InvokeToolAction
from sra.models.enums import AgentState, ReportFormat
from sra.models.goal import ResearchGoal
from sra.models.reflection import CritiqueResult, ReflectionResult
from sra.runtime import ResearchRuntime, RuntimeDependencies, RuntimeOptions

from tests.unit.runtime_fakes import (
    FakeBudget,
    FakeCheckpoints,
    FakeConfidence,
    FakeCritic,
    FakeLogger,
    FakePlanner,
    FakeReflection,
    FakeReports,
    FakeResearchEngine,
    FakeTaskManager,
    FakeTool,
    FakeToolRegistry,
    UnusedMemory,
)


def build_runtime(
    actions: list,
    *,
    tools: FakeToolRegistry | None = None,
    critic: FakeCritic | None = None,
    reflection: FakeReflection | None = None,
    options: RuntimeOptions | None = None,
) -> tuple[ResearchRuntime, dict[str, object]]:
    planner = FakePlanner()
    task_manager = FakeTaskManager()
    engine = FakeResearchEngine(actions)
    registry = tools or FakeToolRegistry()
    reflection_engine = reflection or FakeReflection()
    critic_engine = critic or FakeCritic()
    checkpoints = FakeCheckpoints()
    logger = FakeLogger()
    reports = FakeReports()
    dependencies = RuntimeDependencies(
        planner=planner,
        task_manager=task_manager,
        research_engine=engine,
        tools=registry,
        memory=UnusedMemory(),
        reflection=reflection_engine,
        critic=critic_engine,
        confidence=FakeConfidence(),
        budget=FakeBudget(),
        checkpoints=checkpoints,
        logger=logger,
        reports=reports,
    )
    runtime = ResearchRuntime(dependencies, options=options)
    return runtime, {
        "planner": planner,
        "tasks": task_manager,
        "engine": engine,
        "tools": registry,
        "reflection": reflection_engine,
        "critic": critic_engine,
        "checkpoints": checkpoints,
        "logger": logger,
        "reports": reports,
    }


@pytest.mark.asyncio
async def test_runtime_plans_critiques_reports_and_completes() -> None:
    runtime, fakes = build_runtime([FinalizeAction(summary="Ready")])

    outcome = await runtime.start(ResearchGoal(question="Is this market viable?"))

    assert outcome.context.state is AgentState.COMPLETED
    assert outcome.context.plan is not None
    assert len(outcome.artifacts) == 1
    assert outcome.artifacts[0].format is ReportFormat.MARKDOWN
    assert fakes["logger"].transitions == [
        (AgentState.IDLE, AgentState.PLANNING),
        (AgentState.PLANNING, AgentState.RESEARCHING),
        (AgentState.RESEARCHING, AgentState.GENERATING_REPORT),
        (AgentState.GENERATING_REPORT, AgentState.COMPLETED),
    ]
    transition_count = len(fakes["logger"].transitions)
    assert len(fakes["checkpoints"].snapshots) >= transition_count


@pytest.mark.asyncio
async def test_tool_result_is_persisted_then_reflected() -> None:
    registry = FakeToolRegistry(FakeTool("search"))
    runtime, fakes = build_runtime(
        [
            InvokeToolAction(tool_name="search", arguments={"query": "market"}),
            FinalizeAction(),
        ],
        tools=registry,
        reflection=FakeReflection(ReflectionResult(new_questions=["Who buys this?"])),
    )

    outcome = await runtime.start(ResearchGoal(question="Research a market"))

    assert outcome.context.state is AgentState.COMPLETED
    assert len(outcome.context.tool_history) == 1
    assert outcome.context.tool_history[0].success
    assert "Who buys this?" in outcome.context.memory.working.open_questions
    assert "Who buys this?" in fakes["tasks"].enqueued
    assert (AgentState.RESEARCHING, AgentState.REFLECTING) in fakes["logger"].transitions
    assert (AgentState.REFLECTING, AgentState.RESEARCHING) in fakes["logger"].transitions


@pytest.mark.asyncio
async def test_reader_tool_uses_reading_state() -> None:
    registry = FakeToolRegistry(FakeTool("website_reader", tags=["reader"]))
    runtime, fakes = build_runtime(
        [
            InvokeToolAction(tool_name="website_reader"),
            FinalizeAction(),
        ],
        tools=registry,
    )

    await runtime.start(ResearchGoal(question="Read a source"))

    assert (AgentState.RESEARCHING, AgentState.READING) in fakes["logger"].transitions
    assert (AgentState.READING, AgentState.REFLECTING) in fakes["logger"].transitions


@pytest.mark.asyncio
async def test_failed_critic_forces_replan_before_finalization() -> None:
    critic = FakeCritic(
        CritiqueResult(
            passed=False,
            forced_replan=True,
            summary="Competitor evidence is weak",
        ),
        CritiqueResult(passed=True),
    )
    runtime, fakes = build_runtime(
        [FinalizeAction(), FinalizeAction()],
        critic=critic,
    )

    outcome = await runtime.start(ResearchGoal(question="Assess the opportunity"))

    assert outcome.context.state is AgentState.COMPLETED
    assert fakes["planner"].revised == 1
    assert outcome.context.plan is not None
    assert outcome.context.plan.version == 2
    assert (AgentState.RESEARCHING, AgentState.PLANNING) in fakes["logger"].transitions


@pytest.mark.asyncio
async def test_invalid_tool_action_is_rejected_and_engine_can_recover() -> None:
    runtime, fakes = build_runtime(
        [
            InvokeToolAction(tool_name="unregistered"),
            FinalizeAction(),
        ]
    )

    outcome = await runtime.start(ResearchGoal(question="Test action validation"))

    assert outcome.context.state is AgentState.COMPLETED
    assert any("Rejected agent action" in note for note in outcome.context.memory.working.notes)
    assert (
        "invalid_action",
        "Rejected agent action (1): Tool is not registered: unregistered",
    ) in (fakes["logger"].events)


@pytest.mark.asyncio
async def test_too_many_invalid_actions_fail_and_checkpoint_run() -> None:
    runtime, fakes = build_runtime(
        [
            InvokeToolAction(tool_name="missing-one"),
            InvokeToolAction(tool_name="missing-two"),
        ],
        options=RuntimeOptions(max_consecutive_invalid_actions=1),
    )

    with pytest.raises(InvalidActionError):
        await runtime.start(ResearchGoal(question="Test failure persistence"))

    latest = fakes["checkpoints"].snapshots[-1]
    assert latest.state is AgentState.FAILED
    assert latest.error_message is not None
