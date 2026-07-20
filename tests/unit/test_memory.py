"""Unit tests for SQLite-backed memory manager."""

from __future__ import annotations

from pathlib import Path

import pytest
from sra.core.context import RunContext
from sra.memory import SqliteMemoryManager
from sra.models.enums import KnowledgeKind, TrustTier
from sra.models.goal import ResearchGoal
from sra.models.knowledge import KnowledgeUnit
from sra.models.memory import LongTermMemoryEntry
from sra.models.plan import ResearchPlan
from sra.models.sources import SourceRecord
from sra.storage import SqliteControlPlane


@pytest.fixture
async def memory(tmp_path: Path) -> SqliteMemoryManager:
    db = SqliteControlPlane(tmp_path / "control.sqlite3")
    await db.connect()
    return SqliteMemoryManager(db)


def _ctx(question: str = "Should I build an AI startup for dentists?") -> RunContext:
    return RunContext.create(ResearchGoal(question=question))


@pytest.mark.asyncio
async def test_working_memory_round_trip(memory: SqliteMemoryManager) -> None:
    ctx = _ctx()
    working = await memory.get_working(ctx)
    assert working.objective == ctx.goal.question

    working.open_questions.append("What is market size?")
    working.notes.append("Start with competitors")
    await memory.update_working(ctx, working)

    ctx2 = RunContext.create(ctx.goal)
    ctx2.run_id = ctx.run_id
    restored = await memory.get_working(ctx2)
    assert restored.open_questions == ["What is market size?"]
    assert restored.notes == ["Start with competitors"]


@pytest.mark.asyncio
async def test_record_visit_deduplicates_sources(memory: SqliteMemoryManager) -> None:
    ctx = _ctx()
    source = SourceRecord(
        url="https://Example.com/Report/",
        title="Market Report",
        trust_tier=TrustTier.TRUSTED_PUBLICATION,
    )

    first = await memory.record_visit(ctx, source)
    second = await memory.record_visit(ctx, source)

    assert first is True
    assert second is False
    assert await memory.has_visited(ctx, source.identity_key())
    assert source.identity_key() in ctx.memory.working.visited_source_keys
    assert len(ctx.memory.known_sources) == 1


@pytest.mark.asyncio
async def test_content_hash_identity_prevents_revisit(memory: SqliteMemoryManager) -> None:
    ctx = _ctx()
    a = SourceRecord(url="https://a.example/1", content_hash="abc123")
    b = SourceRecord(url="https://b.example/2", content_hash="abc123")

    assert await memory.record_visit(ctx, a) is True
    assert await memory.record_visit(ctx, b) is False


@pytest.mark.asyncio
async def test_append_evidence_keeps_bounded_window(memory: SqliteMemoryManager) -> None:
    ctx = _ctx()
    units = [
        KnowledgeUnit(kind=KnowledgeKind.FACT, statement=f"Fact {index}", topic="market")
        for index in range(5)
    ]
    await memory.append_evidence(ctx, units, keep_last=3)
    assert len(ctx.memory.working.recent_evidence) == 3
    assert ctx.memory.working.recent_evidence[0].statement == "Fact 2"


@pytest.mark.asyncio
async def test_long_term_put_search_and_promote(memory: SqliteMemoryManager) -> None:
    ctx = _ctx()
    ctx.memory.working.plan = ResearchPlan(goal_summary="Dental AI feasibility")
    ctx.memory.working.recent_evidence = [
        KnowledgeUnit(
            kind=KnowledgeKind.COMPANY,
            statement="Pearl builds dental AI imaging tools",
            entities=["Pearl"],
            topic="competitors",
        ),
        KnowledgeUnit(
            kind=KnowledgeKind.FACT,
            statement="US dental clinics exceed 150k locations",
            topic="market",
        ),
    ]
    await memory.update_working(ctx, ctx.memory.working)

    await memory.put_long_term(
        LongTermMemoryEntry(
            key="industry:dentistry",
            kind="industry",
            content="Dentistry practices are adopting AI imaging and scheduling tools.",
            source_run_id=ctx.run_id,
        )
    )
    hits = await memory.search_long_term("dentistry")
    assert any(item.key == "industry:dentistry" for item in hits)

    written = await memory.promote_run_insights(ctx.run_id)
    assert written >= 3

    past = await memory.search_long_term("AI startup for dentists")
    assert any(item.kind == "past_research" for item in past)
    strategies = await memory.search_long_term("Dental AI feasibility")
    assert any(item.kind == "strategy" for item in strategies)
    companies = await memory.search_long_term("Pearl")
    assert any(item.kind == "company" for item in companies)
