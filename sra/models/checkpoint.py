"""Checkpoint / RunSnapshot models for crash-safe resume."""

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from sra.core.time import utc_now
from sra.models.budget import BudgetLedger
from sra.models.enums import AgentState
from sra.models.goal import ResearchGoal
from sra.models.memory import MemorySnapshot
from sra.models.plan import ResearchPlan, ResearchTask
from sra.models.reflection import ConfidenceMap, CritiqueResult, ReflectionResult
from sra.models.tools import ToolResult


class RunSnapshot(BaseModel):
    """Full recoverable state persisted after every state transition."""

    snapshot_id: UUID = Field(default_factory=uuid4)
    run_id: UUID
    state: AgentState
    goal: ResearchGoal
    plan: ResearchPlan | None = None
    tasks: list[ResearchTask] = Field(default_factory=list)
    memory: MemorySnapshot = Field(default_factory=MemorySnapshot)
    confidence: ConfidenceMap = Field(default_factory=ConfidenceMap)
    last_reflection: ReflectionResult | None = None
    last_critique: CritiqueResult | None = None
    budget: BudgetLedger = Field(default_factory=BudgetLedger)
    tool_history: list[ToolResult] = Field(default_factory=list)
    knowledge_version: int = Field(default=0, ge=0)
    error_message: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)
