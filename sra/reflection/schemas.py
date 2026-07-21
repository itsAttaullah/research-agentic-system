"""LLM-facing draft schema for reflection results."""

from __future__ import annotations

from pydantic import BaseModel, Field


class DraftReflection(BaseModel):
    """Structured reflection output before domain identity is assigned."""

    answered_questions: list[str] = Field(default_factory=list)
    new_questions: list[str] = Field(default_factory=list)
    should_continue: bool = True
    strategy_should_change: bool = False
    strategy_change_summary: str = ""
    source_trust_notes: list[str] = Field(default_factory=list)
    evidence_quality: float = Field(default=0.5, ge=0.0, le=1.0)
    notes: str = ""
