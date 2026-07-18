"""Reflection, Critic, and Confidence ports."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from sra.core.context import RunContext
from sra.models.reflection import ConfidenceMap, CritiqueResult, ReflectionResult
from sra.models.tools import ToolResult


@runtime_checkable
class ReflectionEngine(Protocol):
    """Per-step evaluation that feeds planning and task selection."""

    async def reflect(
        self,
        ctx: RunContext,
        *,
        latest_tool_result: ToolResult | None = None,
    ) -> ReflectionResult: ...


@runtime_checkable
class Critic(Protocol):
    """Hard gate before report generation."""

    async def critique(self, ctx: RunContext) -> CritiqueResult: ...


@runtime_checkable
class ConfidenceEstimator(Protocol):
    """Per-topic confidence; low scores trigger more research."""

    async def estimate(self, ctx: RunContext) -> ConfidenceMap: ...

    def below_threshold(
        self,
        confidence: ConfidenceMap,
        *,
        threshold: float,
    ) -> list[str]:
        """Return topic names that need more research."""
        ...
