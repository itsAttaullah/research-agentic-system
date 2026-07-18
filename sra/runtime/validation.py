"""Validation boundary for every LLM-proposed agent action."""

from collections.abc import Sequence

from sra.core.context import RunContext
from sra.core.errors import InvalidActionError, ToolNotFoundError
from sra.core.ports import ToolRegistry
from sra.models.actions import (
    AgentAction,
    FinalizeAction,
    InvokeToolAction,
    ReflectAction,
    RequestCriticAction,
    UpdatePlanAction,
)

_ACTION_TYPES = (
    InvokeToolAction,
    UpdatePlanAction,
    ReflectAction,
    RequestCriticAction,
    FinalizeAction,
)


class ActionValidator:
    """Enforces runtime safety rules before dispatching an action."""

    def __init__(self, tools: ToolRegistry) -> None:
        self._tools = tools

    def validate(self, action: AgentAction, ctx: RunContext) -> None:
        if not isinstance(action, _ACTION_TYPES):
            raise InvalidActionError(
                "Research Engine returned an unsupported action type",
                details={"type": type(action).__name__},
            )

        if isinstance(action, InvokeToolAction):
            self._validate_tool_action(action, ctx)
        elif isinstance(action, UpdatePlanAction):
            self._validate_plan_action(action)
        elif isinstance(action, FinalizeAction) and ctx.plan is None:
            raise InvalidActionError("Cannot finalize a run without a research plan")

    def _validate_tool_action(self, action: InvokeToolAction, ctx: RunContext) -> None:
        try:
            self._tools.get(action.tool_name)
        except (KeyError, LookupError, ToolNotFoundError) as exc:
            raise InvalidActionError(
                f"Tool is not registered: {action.tool_name}",
                details={"tool_name": action.tool_name},
            ) from exc

        if action.related_task_id is not None and action.related_task_id not in {
            task.id for task in ctx.tasks
        }:
            raise InvalidActionError(
                "Tool action references an unknown research task",
                details={"task_id": str(action.related_task_id)},
            )

    @staticmethod
    def _validate_plan_action(action: UpdatePlanAction) -> None:
        if not action.reason.strip():
            raise InvalidActionError("A plan update must include a reason")
        if not action.plan.goal_summary.strip():
            raise InvalidActionError("A research plan must include a goal summary")


def action_type_names() -> Sequence[str]:
    """Expose supported action names for diagnostics and tests."""
    return tuple(action_type.__name__ for action_type in _ACTION_TYPES)
