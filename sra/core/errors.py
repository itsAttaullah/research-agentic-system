"""Typed error hierarchy for the Strategic Research Agent.

Runtime and collaborators raise these; the API/CLI map them to user-facing
responses. No bare Exception swallowing at package boundaries.
"""

from __future__ import annotations

from typing import Any


class SRAError(Exception):
    """Base error for all SRA failures."""

    def __init__(self, message: str, *, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class ConfigurationError(SRAError):
    """Missing or invalid configuration / environment."""


class InvalidActionError(SRAError):
    """Research Engine proposed an action the Runtime rejected."""


class ToolNotFoundError(SRAError):
    """Requested tool name is not registered."""


class ToolExecutionError(SRAError):
    """Tool execute() failed after validation."""


class ToolValidationError(SRAError):
    """Tool input or output failed schema validation."""


class BudgetExceededError(SRAError):
    """A hard budget limit was hit; the run must abort."""


class CheckpointError(SRAError):
    """Checkpoint persist or restore failed."""


class StateTransitionError(SRAError):
    """Illegal agent state transition."""


class PlanningError(SRAError):
    """Planner could not produce or revise a valid plan."""


class ReflectionError(SRAError):
    """Reflection Engine could not produce a valid reflection result."""


class KnowledgeError(SRAError):
    """Knowledge extraction or store failure."""


class CritiqueBlockedError(SRAError):
    """Critic rejected finalization; run must return to planning."""


class ReportGenerationError(SRAError):
    """Report rendering failed."""


class LLMError(SRAError):
    """LLM provider call failed or returned unusable output."""


class StorageError(SRAError):
    """Underlying storage adapter failure."""
