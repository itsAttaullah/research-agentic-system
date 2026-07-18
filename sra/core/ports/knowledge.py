"""Knowledge extraction and store ports."""

from __future__ import annotations

from typing import Protocol, runtime_checkable
from uuid import UUID

from sra.models.knowledge import Disagreement, ExtractionResult, KnowledgeUnit
from sra.models.sources import SourceRecord


@runtime_checkable
class KnowledgeExtractor(Protocol):
    """Convert a document into structured KnowledgeUnits."""

    async def extract(
        self,
        *,
        source: SourceRecord,
        text: str,
        topic: str = "",
    ) -> ExtractionResult: ...


@runtime_checkable
class KnowledgeStore(Protocol):
    """Durable structured knowledge with provenance and disagreements."""

    async def upsert_units(self, units: list[KnowledgeUnit]) -> int: ...

    async def get_unit(self, unit_id: UUID) -> KnowledgeUnit | None: ...

    async def query_by_topic(self, topic: str, *, limit: int = 100) -> list[KnowledgeUnit]: ...

    async def query_by_entity(self, entity: str, *, limit: int = 100) -> list[KnowledgeUnit]: ...

    async def record_disagreement(self, disagreement: Disagreement) -> None: ...

    async def list_disagreements(self, *, topic: str | None = None) -> list[Disagreement]: ...

    async def version(self) -> int:
        """Monotonic knowledge version used in checkpoints."""
        ...
