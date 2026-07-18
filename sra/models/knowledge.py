"""Structured knowledge units extracted from documents — not raw text dumps."""

from datetime import date, datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from sra.core.time import utc_now
from sra.models.enums import KnowledgeKind, TrustTier
from sra.models.sources import Citation


class KnowledgeUnit(BaseModel):
    """One extracted, typed piece of knowledge with provenance."""

    unit_id: UUID = Field(default_factory=uuid4)
    kind: KnowledgeKind
    statement: str = Field(min_length=1)
    value: float | str | None = Field(
        default=None,
        description="Numeric or canonical value when kind is STATISTIC/DATE/etc.",
    )
    unit: str | None = Field(default=None, description="e.g. USD, %, users.")
    as_of: date | None = None
    entities: list[str] = Field(
        default_factory=list,
        description="Companies, products, people, or places mentioned.",
    )
    topic: str = Field(default="", description="Investigation / topic label.")
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    trust_tier: TrustTier = TrustTier.UNKNOWN
    citations: list[Citation] = Field(default_factory=list)
    extracted_at: datetime = Field(default_factory=utc_now)
    metadata: dict[str, str] = Field(default_factory=dict)


class Disagreement(BaseModel):
    """Linked conflicting claims that must be explained in the report."""

    disagreement_id: UUID = Field(default_factory=uuid4)
    topic: str
    unit_ids: list[UUID] = Field(min_length=2)
    summary: str
    resolution: str = Field(
        default="",
        description="Agent explanation of which side is preferred and why, if any.",
    )
    created_at: datetime = Field(default_factory=utc_now)


class ExtractionResult(BaseModel):
    """Output of the knowledge extraction pipeline for one document."""

    source_id: UUID
    units: list[KnowledgeUnit] = Field(default_factory=list)
    disagreements: list[Disagreement] = Field(default_factory=list)
    raw_summary: str = ""
