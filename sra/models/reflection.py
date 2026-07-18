"""Reflection, confidence, and critic result models."""

from datetime import datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from sra.core.time import utc_now


class ReflectionResult(BaseModel):
    """Post-step evaluation that influences future planning and task selection."""

    reflection_id: UUID = Field(default_factory=uuid4)
    at: datetime = Field(default_factory=utc_now)
    answered_questions: list[str] = Field(default_factory=list)
    new_questions: list[str] = Field(default_factory=list)
    should_continue: bool = True
    strategy_should_change: bool = False
    strategy_change_summary: str = ""
    source_trust_notes: list[str] = Field(default_factory=list)
    evidence_quality: float = Field(default=0.5, ge=0.0, le=1.0)
    notes: str = ""


class TopicConfidence(BaseModel):
    """Confidence for one research topic / investigation."""

    topic: str
    score: float = Field(ge=0.0, le=1.0)
    rationale: str = ""
    evidence_unit_ids: list[UUID] = Field(default_factory=list)
    needs_more_research: bool = False


class ConfidenceMap(BaseModel):
    """Per-topic confidence snapshot for a run."""

    topics: list[TopicConfidence] = Field(default_factory=list)
    overall: float = Field(default=0.0, ge=0.0, le=1.0)
    updated_at: datetime = Field(default_factory=utc_now)

    def low_confidence_topics(self, threshold: float = 0.7) -> list[TopicConfidence]:
        return [t for t in self.topics if t.score < threshold or t.needs_more_research]


class CritiqueFinding(BaseModel):
    """A single critic issue that may block finalization."""

    code: str = Field(description="e.g. missing_evidence, weak_assumption, bias")
    severity: str = Field(default="medium", description="low | medium | high | blocker")
    message: str
    related_topics: list[str] = Field(default_factory=list)


class CritiqueResult(BaseModel):
    """Critic gate outcome. Failed critiques return the run to planning."""

    critique_id: UUID = Field(default_factory=uuid4)
    at: datetime = Field(default_factory=utc_now)
    passed: bool
    findings: list[CritiqueFinding] = Field(default_factory=list)
    forced_replan: bool = False
    replan_directives: list[str] = Field(default_factory=list)
    summary: str = ""
