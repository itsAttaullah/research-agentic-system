"""Allowed agent state transitions.

The Runtime is the only component that mutates AgentState; it consults this
table and raises StateTransitionError on illegal moves.
"""

from __future__ import annotations

from sra.core.errors import StateTransitionError
from sra.models.enums import AgentState

# From -> allowed destinations. FAILED and COMPLETED are terminal except
# WAITING can resume into the prior active phase via explicit resume paths.
ALLOWED_TRANSITIONS: dict[AgentState, frozenset[AgentState]] = {
    AgentState.IDLE: frozenset({AgentState.PLANNING, AgentState.FAILED}),
    AgentState.PLANNING: frozenset(
        {
            AgentState.RESEARCHING,
            AgentState.WAITING,
            AgentState.FAILED,
        }
    ),
    AgentState.RESEARCHING: frozenset(
        {
            AgentState.READING,
            AgentState.EXTRACTING,
            AgentState.REFLECTING,
            AgentState.PLANNING,
            AgentState.GENERATING_REPORT,
            AgentState.WAITING,
            AgentState.FAILED,
        }
    ),
    AgentState.READING: frozenset(
        {
            AgentState.EXTRACTING,
            AgentState.REFLECTING,
            AgentState.RESEARCHING,
            AgentState.WAITING,
            AgentState.FAILED,
        }
    ),
    AgentState.EXTRACTING: frozenset(
        {
            AgentState.REFLECTING,
            AgentState.RESEARCHING,
            AgentState.WAITING,
            AgentState.FAILED,
        }
    ),
    AgentState.REFLECTING: frozenset(
        {
            AgentState.PLANNING,
            AgentState.RESEARCHING,
            AgentState.GENERATING_REPORT,
            AgentState.WAITING,
            AgentState.FAILED,
        }
    ),
    AgentState.WAITING: frozenset(
        {
            AgentState.PLANNING,
            AgentState.RESEARCHING,
            AgentState.READING,
            AgentState.EXTRACTING,
            AgentState.REFLECTING,
            AgentState.GENERATING_REPORT,
            AgentState.FAILED,
        }
    ),
    AgentState.GENERATING_REPORT: frozenset(
        {
            AgentState.COMPLETED,
            AgentState.PLANNING,  # critic forced replan
            AgentState.FAILED,
        }
    ),
    AgentState.COMPLETED: frozenset(),
    AgentState.FAILED: frozenset(),
}


def assert_transition(current: AgentState, target: AgentState) -> None:
    """Raise StateTransitionError if current -> target is illegal."""
    allowed = ALLOWED_TRANSITIONS.get(current, frozenset())
    if target not in allowed:
        raise StateTransitionError(
            f"Illegal state transition: {current} -> {target}",
            details={"from": current.value, "to": target.value},
        )


def can_transition(current: AgentState, target: AgentState) -> bool:
    return target in ALLOWED_TRANSITIONS.get(current, frozenset())
