"""Working and long-term memory snapshots."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from sra.core.time import utc_now
from sra.models.knowledge import KnowledgeUnit
from sra.models.plan import ResearchPlan, ResearchTask
from sra.models.sources import SourceRecord


class WorkingMemory(BaseModel):
    """Ephemeral, run-scoped memory the agent reasons over each step."""

    objective: str = ""
    plan: ResearchPlan | None = None
    active_task: ResearchTask | None = None
    open_questions: list[str] = Field(default_factory=list)
    visited_source_keys: list[str] = Field(
        default_factory=list,
        description="identity_key() values to prevent revisiting identical sources.",
    )
    recent_evidence: list[KnowledgeUnit] = Field(default_factory=list)
    recent_tool_call_ids: list[UUID] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)
    updated_at: datetime = Field(default_factory=utc_now)


class LongTermMemoryEntry(BaseModel):
    """A durable fact or strategy reusable across runs."""

    key: str
    kind: str = Field(
        description="past_research | company | industry | strategy | fact",
    )
    content: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)
    source_run_id: UUID | None = None


class MemorySnapshot(BaseModel):
    """Combined memory view persisted inside checkpoints."""

    working: WorkingMemory = Field(default_factory=WorkingMemory)
    long_term_keys: list[str] = Field(
        default_factory=list,
        description="Keys of long-term entries relevant to this run (not full dump).",
    )
    known_sources: list[SourceRecord] = Field(default_factory=list)
