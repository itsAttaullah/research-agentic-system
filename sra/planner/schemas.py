"""LLM-facing draft schemas for research plans.

These are intentionally separate from :class:`~sra.models.plan.ResearchPlan`
so the model can omit internal identity fields (IDs, versions, revisions)
which the planner owns.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class DraftInvestigation(BaseModel):
    """One investigation area proposed by the planner LLM."""

    title: str = Field(min_length=1)
    rationale: str = ""
    hypotheses: list[str] = Field(default_factory=list)
    success_criteria: list[str] = Field(default_factory=list)
    priority: int = Field(default=50, ge=0, le=100)
    related_open_questions: list[str] = Field(default_factory=list)
    suggested_tools: list[str] = Field(
        default_factory=list,
        description="Optional tool hints for the first task under this investigation.",
    )


class DraftPlan(BaseModel):
    """Structured planner output before domain identity is assigned."""

    goal_summary: str = Field(min_length=1)
    investigations: list[DraftInvestigation] = Field(min_length=1)
    open_questions: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    out_of_scope: list[str] = Field(default_factory=list)
    revision_summary: str = Field(
        default="",
        description="Short summary of what changed; required when revising.",
    )
