"""AgentAction variants proposed by the Research Engine and validated by the Runtime."""

from typing import Annotated, Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field

from sra.models.enums import ActionKind
from sra.models.plan import ResearchPlan


class InvokeToolAction(BaseModel):
    """Request to execute a registered tool with schema-validated arguments."""

    kind: Literal[ActionKind.INVOKE_TOOL] = ActionKind.INVOKE_TOOL
    tool_name: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    rationale: str = ""
    related_task_id: UUID | None = None


class UpdatePlanAction(BaseModel):
    """Request to replace or revise the active ResearchPlan."""

    kind: Literal[ActionKind.UPDATE_PLAN] = ActionKind.UPDATE_PLAN
    plan: ResearchPlan
    reason: str


class ReflectAction(BaseModel):
    """Request a reflection cycle over recent observations."""

    kind: Literal[ActionKind.REFLECT] = ActionKind.REFLECT
    focus: str = Field(
        default="",
        description="Optional focus (task id, question, or free-text concern).",
    )


class RequestCriticAction(BaseModel):
    """Request the Critic gate before finalization."""

    kind: Literal[ActionKind.REQUEST_CRITIC] = ActionKind.REQUEST_CRITIC
    reason: str = ""


class FinalizeAction(BaseModel):
    """Signal readiness to generate the final report (Critic must still pass)."""

    kind: Literal[ActionKind.FINALIZE] = ActionKind.FINALIZE
    summary: str = ""


AgentAction = Annotated[
    InvokeToolAction
    | UpdatePlanAction
    | ReflectAction
    | RequestCriticAction
    | FinalizeAction,
    Field(discriminator="kind"),
]
