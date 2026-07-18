"""Research goal and run identity models."""

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from sra.core.time import utc_now


class ResearchGoal(BaseModel):
    """User-supplied research objective and optional hard constraints."""

    question: str = Field(min_length=1, description="Natural-language research question.")
    constraints: dict[str, Any] = Field(
        default_factory=dict,
        description="Optional constraints (region, time horizon, industries, exclusions).",
    )
    success_criteria: list[str] = Field(
        default_factory=list,
        description="What must be true for the run to be considered successful.",
    )
    created_at: datetime = Field(default_factory=utc_now)


class RunIdentity(BaseModel):
    """Stable identifiers for a single research run."""

    run_id: UUID = Field(default_factory=uuid4)
    created_at: datetime = Field(default_factory=utc_now)
    goal: ResearchGoal
