"""Unit tests for SQLite-backed checkpoint persistence and resume."""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import pytest
from sra.checkpoint import SqliteCheckpointManager
from sra.core.context import RunContext
from sra.core.errors import CheckpointError
from sra.models.enums import AgentState, KnowledgeKind, TrustTier
from sra.models.goal import ResearchGoal
from sra.models.knowledge import KnowledgeUnit
from sra.models.plan import Investigation, ResearchPlan, ResearchTask
from sra.models.reflection import ConfidenceMap, CritiqueResult, TopicConfidence
from sra.models.sources import SourceRecord
from sra.models.tools import ToolResult
from sra.storage import SqliteControlPlane


@pytest.fixture
async def checkpoints(tmp_path: Path) -> SqliteCheckpointManager:
    db = SqliteControlPlane(tmp_path / "control.sqlite3")
    await db.connect()
    return SqliteCheckpointManager(db)


def _rich_context() -> RunContext:
    ctx = RunContext.create(ResearchGoal(question="Should I build an AI startup for dentists?"))
    ctx.state = AgentState.RESEARCHING
    ctx.plan = ResearchPlan(
        goal_summary="Dental AI feasibility",
        investigations=[Investigation(title="Market size", priority=90)],
    )
    assert ctx.plan is not None
    ctx.tasks = [
        ResearchTask(
            investigation_id=ctx.plan.investigations[0].id,
            title="Market size",
            priority=90,
        )
    ]
    ctx.memory.working.open_questions = ["What will clinics pay?"]
    ctx.memory.working.visited_source_keys = ["url:https://example.com/report"]
    ctx.memory.working.recent_evidence = [
        KnowledgeUnit(
            kind=KnowledgeKind.STATISTIC,
            statement="There are ~200k dentists in the US.",
            topic="Market size",
            confidence=0.8,
            trust_tier=TrustTier.TRUSTED_PUBLICATION,
        )
    ]
    ctx.memory.known_sources = [
        SourceRecord(
            url="https://example.com/report",
            title="Market report",
            trust_tier=TrustTier.TRUSTED_PUBLICATION,
        )
    ]
    ctx.confidence = ConfidenceMap(
        topics=[TopicConfidence(topic="Market size", score=0.8)],
        overall=0.8,
    )
    ctx.last_critique = CritiqueResult(passed=True, summary="Ready for more research")
    ctx.tool_history = [
        ToolResult(
            call_id=uuid4(),
            tool_name="google_search",
            success=True,
            output={"results": []},
        )
    ]
    ctx.knowledge_version = 3
    ctx.budget.usage.iterations = 4
    ctx.budget.usage.tokens = 1200
    return ctx


@pytest.mark.asyncio
async def test_save_and_latest_round_trip(checkpoints: SqliteCheckpointManager) -> None:
    ctx = _rich_context()
    saved = await checkpoints.save(ctx)

    latest = await checkpoints.latest(ctx.run_id)
    assert latest is not None
    assert latest.snapshot_id == saved.snapshot_id
    assert latest.state is AgentState.RESEARCHING
    assert latest.plan is not None
    assert latest.plan.goal_summary == "Dental AI feasibility"
    assert latest.memory.working.open_questions == ["What will clinics pay?"]
    assert latest.tool_history[0].tool_name == "google_search"
    assert latest.knowledge_version == 3
    assert latest.budget.usage.iterations == 4


@pytest.mark.asyncio
async def test_list_for_run_is_chronological(checkpoints: SqliteCheckpointManager) -> None:
    ctx = _rich_context()
    first = await checkpoints.save(ctx)
    ctx.state = AgentState.REFLECTING
    second = await checkpoints.save(ctx)
    ctx.state = AgentState.GENERATING_REPORT
    third = await checkpoints.save(ctx)

    history = await checkpoints.list_for_run(ctx.run_id)
    assert [item.snapshot_id for item in history] == [
        first.snapshot_id,
        second.snapshot_id,
        third.snapshot_id,
    ]
    assert [item.state for item in history] == [
        AgentState.RESEARCHING,
        AgentState.REFLECTING,
        AgentState.GENERATING_REPORT,
    ]

    latest = await checkpoints.latest(ctx.run_id)
    assert latest is not None
    assert latest.snapshot_id == third.snapshot_id


@pytest.mark.asyncio
async def test_load_by_snapshot_id_and_missing(checkpoints: SqliteCheckpointManager) -> None:
    ctx = _rich_context()
    saved = await checkpoints.save(ctx)

    loaded = await checkpoints.load(saved.snapshot_id)
    assert loaded.run_id == ctx.run_id
    assert loaded.goal.question == ctx.goal.question

    with pytest.raises(CheckpointError, match="not found"):
        await checkpoints.load(uuid4())


@pytest.mark.asyncio
async def test_resume_restores_run_context(checkpoints: SqliteCheckpointManager) -> None:
    ctx = _rich_context()
    saved = await checkpoints.save(ctx)

    restored = RunContext.from_snapshot(saved)
    assert restored.run_id == ctx.run_id
    assert restored.state is AgentState.RESEARCHING
    assert restored.plan is not None
    assert restored.tasks[0].title == "Market size"
    assert restored.memory.known_sources[0].url == "https://example.com/report"
    assert restored.confidence.overall == 0.8
    assert restored.last_critique is not None
    assert restored.last_critique.passed is True
    assert restored.budget.usage.tokens == 1200
    assert restored.knowledge_version == 3


@pytest.mark.asyncio
async def test_latest_returns_none_for_unknown_run(
    checkpoints: SqliteCheckpointManager,
) -> None:
    assert await checkpoints.latest(uuid4()) is None
    assert await checkpoints.list_for_run(uuid4()) == []
