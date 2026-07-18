"""Memory Manager port."""

from __future__ import annotations

from typing import Protocol, runtime_checkable
from uuid import UUID

from sra.core.context import RunContext
from sra.models.knowledge import KnowledgeUnit
from sra.models.memory import LongTermMemoryEntry, WorkingMemory
from sra.models.sources import SourceRecord


@runtime_checkable
class MemoryManager(Protocol):
    """Working + long-term memory with source deduplication helpers."""

    async def get_working(self, ctx: RunContext) -> WorkingMemory: ...

    async def update_working(self, ctx: RunContext, working: WorkingMemory) -> None: ...

    async def record_visit(self, ctx: RunContext, source: SourceRecord) -> bool:
        """Record a visit. Returns False if the source was already visited."""
        ...

    async def has_visited(self, ctx: RunContext, identity_key: str) -> bool: ...

    async def append_evidence(
        self,
        ctx: RunContext,
        units: list[KnowledgeUnit],
        *,
        keep_last: int = 50,
    ) -> None: ...

    async def put_long_term(self, entry: LongTermMemoryEntry) -> None: ...

    async def search_long_term(
        self,
        query: str,
        *,
        limit: int = 20,
    ) -> list[LongTermMemoryEntry]: ...

    async def promote_run_insights(self, run_id: UUID) -> int:
        """Persist durable insights from a completed run. Returns count written."""
        ...
