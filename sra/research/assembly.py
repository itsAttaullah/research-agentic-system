"""Normalize draft actions into typed AgentAction models."""

from __future__ import annotations

from sra.core.errors import InvalidActionError
from sra.models.actions import (
    AgentAction,
    FinalizeAction,
    InvokeToolAction,
    ReflectAction,
    RequestCriticAction,
    UpdatePlanAction,
)
from sra.models.plan import ResearchPlan
from sra.research.schemas import DraftAgentAction


def draft_to_action(draft: DraftAgentAction) -> AgentAction:
    if draft.kind == "invoke_tool":
        if not draft.tool_name or not draft.tool_name.strip():
            raise InvalidActionError("invoke_tool requires tool_name")
        return InvokeToolAction(
            tool_name=draft.tool_name.strip(),
            arguments=draft.arguments,
            rationale=draft.rationale,
            related_task_id=draft.related_task_id,
        )
    if draft.kind == "update_plan":
        if draft.plan is None:
            raise InvalidActionError("update_plan requires a plan object")
        if not draft.reason.strip():
            raise InvalidActionError("update_plan requires a reason")
        return UpdatePlanAction(
            plan=ResearchPlan.model_validate(draft.plan),
            reason=draft.reason.strip(),
        )
    if draft.kind == "reflect":
        return ReflectAction(focus=draft.focus)
    if draft.kind == "request_critic":
        return RequestCriticAction(reason=draft.reason or draft.rationale)
    if draft.kind == "finalize":
        return FinalizeAction(summary=draft.summary or draft.rationale)
    raise InvalidActionError(f"Unsupported action kind: {draft.kind}")
