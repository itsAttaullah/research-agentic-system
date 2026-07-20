"""Research plan and investigation models produced/revised by the Planner."""

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from sra.core.time import utc_now
from sra.models.enums import TaskStatus


class Investigation(BaseModel):
    """A thematic area the planner decided to investigate (e.g. market size)."""

    id: UUID = Field(default_factory=uuid4)
    title: str
    rationale: str = ""
    hypotheses: list[str] = Field(default_factory=list)
    success_criteria: list[str] = Field(default_factory=list)
    priority: int = Field(default=50, ge=0, le=100, description="Higher = more urgent.")
    status: TaskStatus = TaskStatus.PENDING
    related_open_questions: list[str] = Field(default_factory=list)
    suggested_tools: list[str] = Field(
        default_factory=list,
        description="Optional tool hints for tasks derived from this investigation.",
    )


class ResearchTask(BaseModel):
    """Atomic unit of work derived from an investigation by the Task Manager."""

    id: UUID = Field(default_factory=uuid4)
    investigation_id: UUID
    title: str
    description: str = ""
    priority: int = Field(default=50, ge=0, le=100)
    status: TaskStatus = TaskStatus.PENDING
    suggested_tools: list[str] = Field(
        default_factory=list,
        description="Optional tool-name hints; the engine may ignore them.",
    )
    depends_on: list[UUID] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    metadata: dict[str, Any] = Field(default_factory=dict)


class PlanRevision(BaseModel):
    """Immutable record of a plan change for auditability."""

    revision_id: UUID = Field(default_factory=uuid4)
    at: datetime = Field(default_factory=utc_now)
    reason: str
    summary: str
    triggered_by: str = Field(
        default="planner",
        description="planner | reflection | critic | confidence | human",
    )


class ResearchPlan(BaseModel):
    """Structured strategy for a research run; revised as evidence arrives."""

    plan_id: UUID = Field(default_factory=uuid4)
    goal_summary: str
    investigations: list[Investigation] = Field(default_factory=list)
    open_questions: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    out_of_scope: list[str] = Field(default_factory=list)
    revisions: list[PlanRevision] = Field(default_factory=list)
    version: int = Field(default=1, ge=1)
    updated_at: datetime = Field(default_factory=utc_now)

    def active_investigations(self) -> list[Investigation]:
        return [i for i in self.investigations if i.status != TaskStatus.CANCELLED]
