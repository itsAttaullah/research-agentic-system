"""Core primitives: RunContext, ports (protocols), errors, and the agent state enum.

Every other package depends on `core` and `models`; `core` depends on nothing
internal except `models`. This keeps the dependency graph acyclic.
"""

from sra.core.config import Settings
from sra.core.context import RunContext
from sra.core.errors import (
    BudgetExceededError,
    CheckpointError,
    ConfigurationError,
    CritiqueBlockedError,
    CritiqueError,
    InvalidActionError,
    KnowledgeError,
    LLMError,
    PlanningError,
    ReportGenerationError,
    SRAError,
    StateTransitionError,
    StorageError,
    ToolExecutionError,
    ToolNotFoundError,
    ToolValidationError,
)
from sra.core.state_machine import ALLOWED_TRANSITIONS, assert_transition, can_transition

__all__ = [
    "ALLOWED_TRANSITIONS",
    "BudgetExceededError",
    "CheckpointError",
    "ConfigurationError",
    "CritiqueBlockedError",
    "CritiqueError",
    "InvalidActionError",
    "KnowledgeError",
    "LLMError",
    "PlanningError",
    "ReportGenerationError",
    "RunContext",
    "SRAError",
    "Settings",
    "StateTransitionError",
    "StorageError",
    "ToolExecutionError",
    "ToolNotFoundError",
    "ToolValidationError",
    "assert_transition",
    "can_transition",
]
