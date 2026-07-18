"""Planner and Task Manager ports."""

from __future__ import annotations

from typing import Protocol, runtime_checkable
from uuid import UUID

from sra.core.context import RunContext
from sra.models.plan import ResearchPlan, ResearchTask
from sra.models.reflection import CritiqueResult, ReflectionResult


@runtime_checkable
class Planner(Protocol):
    """Converts goals into ResearchPlans and revises them from new evidence."""

    async def create_plan(self, ctx: RunContext) -> ResearchPlan:
        """Initial plan from the research goal. Must not execute tools."""
        ...

    async def revise_plan(
        self,
        ctx: RunContext,
        *,
        reason: str,
        reflection: ReflectionResult | None = None,
        critique: CritiqueResult | None = None,
    ) -> ResearchPlan:
        """Update the plan given new evidence / critique directives."""
        ...


@runtime_checkable
class TaskManager(Protocol):
    """Materializes investigations into prioritized atomic tasks."""

    async def sync_tasks(self, ctx: RunContext) -> list[ResearchTask]:
        """Ensure ctx.tasks matches the current plan; return the full queue."""
        ...

    async def next_task(self, ctx: RunContext) -> ResearchTask | None:
        """Select the highest-priority ready task, or None if the queue is empty."""
        ...

    async def mark_done(self, ctx: RunContext, task_id: UUID) -> None: ...

    async def enqueue_from_questions(
        self,
        ctx: RunContext,
        questions: list[str],
        *,
        priority: int = 60,
    ) -> list[ResearchTask]:
        """Create tasks for newly discovered open questions."""
        ...
