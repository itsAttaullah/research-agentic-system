"""SQLite-backed Memory Manager implementing working + long-term memory."""

from __future__ import annotations

from uuid import UUID

from sra.core.context import RunContext
from sra.core.time import utc_now
from sra.models.knowledge import KnowledgeUnit
from sra.models.memory import LongTermMemoryEntry, WorkingMemory
from sra.models.sources import SourceRecord
from sra.storage.memory_store import MemoryStore
from sra.storage.sqlite import SqliteControlPlane


class SqliteMemoryManager:
    """MemoryManager port backed by the SQLite control plane."""

    def __init__(self, db: SqliteControlPlane) -> None:
        self._store = MemoryStore(db)

    async def get_working(self, ctx: RunContext) -> WorkingMemory:
        stored = await self._store.load_working(ctx.run_id)
        if stored is not None:
            ctx.memory.working = stored
            return stored
        if not ctx.memory.working.objective:
            ctx.memory.working.objective = ctx.goal.question
        return ctx.memory.working

    async def update_working(self, ctx: RunContext, working: WorkingMemory) -> None:
        working.updated_at = utc_now()
        ctx.memory.working = working
        await self._store.save_working(ctx.run_id, working)

    async def record_visit(self, ctx: RunContext, source: SourceRecord) -> bool:
        identity_key = source.identity_key()
        if identity_key in ctx.memory.working.visited_source_keys:
            return False
        if await self._store.has_visit(ctx.run_id, identity_key):
            if identity_key not in ctx.memory.working.visited_source_keys:
                ctx.memory.working.visited_source_keys.append(identity_key)
            return False

        inserted = await self._store.insert_visit(ctx.run_id, source)
        if not inserted:
            return False

        ctx.memory.working.visited_source_keys.append(identity_key)
        if all(existing.source_id != source.source_id for existing in ctx.memory.known_sources):
            ctx.memory.known_sources.append(source)
        await self._store.save_working(ctx.run_id, ctx.memory.working)
        return True

    async def has_visited(self, ctx: RunContext, identity_key: str) -> bool:
        if identity_key in ctx.memory.working.visited_source_keys:
            return True
        return await self._store.has_visit(ctx.run_id, identity_key)

    async def append_evidence(
        self,
        ctx: RunContext,
        units: list[KnowledgeUnit],
        *,
        keep_last: int = 50,
    ) -> None:
        if keep_last < 1:
            msg = "keep_last must be >= 1"
            raise ValueError(msg)
        if not units:
            return
        working = ctx.memory.working
        working.recent_evidence.extend(units)
        if len(working.recent_evidence) > keep_last:
            working.recent_evidence = working.recent_evidence[-keep_last:]
        working.updated_at = utc_now()
        await self._store.save_working(ctx.run_id, working)

    async def put_long_term(self, entry: LongTermMemoryEntry) -> None:
        await self._store.put_long_term(entry)

    async def search_long_term(
        self,
        query: str,
        *,
        limit: int = 20,
    ) -> list[LongTermMemoryEntry]:
        cleaned = query.strip()
        if not cleaned:
            return []
        return await self._store.search_long_term(cleaned, limit=limit)

    async def promote_run_insights(self, run_id: UUID) -> int:
        """Promote durable insights from a completed run into long-term memory."""
        working = await self._store.load_working(run_id)
        if working is None:
            return 0

        written = 0
        if working.objective:
            await self.put_long_term(
                LongTermMemoryEntry(
                    key=f"past_research:{run_id}",
                    kind="past_research",
                    content=working.objective,
                    metadata={
                        "open_questions": working.open_questions[:20],
                        "visited_sources": len(working.visited_source_keys),
                    },
                    source_run_id=run_id,
                )
            )
            written += 1

        if working.plan is not None:
            await self.put_long_term(
                LongTermMemoryEntry(
                    key=f"strategy:{run_id}",
                    kind="strategy",
                    content=working.plan.goal_summary,
                    metadata={
                        "investigations": [item.title for item in working.plan.investigations],
                        "assumptions": working.plan.assumptions,
                        "version": working.plan.version,
                    },
                    source_run_id=run_id,
                )
            )
            written += 1

        for unit in working.recent_evidence:
            for entity in unit.entities:
                cleaned = entity.strip()
                if not cleaned:
                    continue
                kind = "company" if unit.kind.value in {"company", "product"} else "fact"
                key = f"{kind}:{cleaned.casefold()}:{unit.unit_id}"
                await self.put_long_term(
                    LongTermMemoryEntry(
                        key=key,
                        kind=kind if kind in {"company", "fact"} else "fact",
                        content=unit.statement,
                        metadata={
                            "entity": cleaned,
                            "topic": unit.topic,
                            "knowledge_kind": unit.kind.value,
                        },
                        source_run_id=run_id,
                    )
                )
                written += 1

            if not unit.entities and unit.statement.strip():
                await self.put_long_term(
                    LongTermMemoryEntry(
                        key=f"fact:{unit.unit_id}",
                        kind="fact",
                        content=unit.statement,
                        metadata={"topic": unit.topic, "knowledge_kind": unit.kind.value},
                        source_run_id=run_id,
                    )
                )
                written += 1

        return written
