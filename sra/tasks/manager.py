"""Default Task Manager: materializes plan investigations into a work queue."""

from __future__ import annotations

from uuid import UUID, uuid4

from sra.core.context import RunContext
from sra.core.errors import PlanningError
from sra.core.time import utc_now
from sra.models.enums import TaskStatus
from sra.models.plan import Investigation, ResearchTask

EMERGING_QUESTIONS_TITLE = "Emerging questions"


class DefaultTaskManager:
    """Deterministic task queue derived from the active :class:`ResearchPlan`."""

    async def sync_tasks(self, ctx: RunContext) -> list[ResearchTask]:
        plan = ctx.plan
        if plan is None:
            ctx.tasks = []
            return []

        active_ids = {item.id for item in plan.active_investigations()}
        retained: list[ResearchTask] = []
        covered_investigations: set[UUID] = set()

        for task in ctx.tasks:
            if task.investigation_id not in active_ids:
                if task.status not in {TaskStatus.DONE, TaskStatus.CANCELLED}:
                    task = task.model_copy(
                        update={"status": TaskStatus.CANCELLED, "updated_at": utc_now()}
                    )
                retained.append(task)
                continue
            retained.append(task)
            if task.status != TaskStatus.CANCELLED:
                covered_investigations.add(task.investigation_id)

        for investigation in plan.active_investigations():
            if investigation.id in covered_investigations:
                continue
            retained.append(_task_from_investigation(investigation))

        ctx.tasks = retained
        ctx.memory.working.plan = plan
        return list(ctx.tasks)

    async def next_task(self, ctx: RunContext) -> ResearchTask | None:
        done_ids = {task.id for task in ctx.tasks if task.status is TaskStatus.DONE}
        candidates = [
            task
            for task in ctx.tasks
            if task.status is TaskStatus.PENDING and all(dep in done_ids for dep in task.depends_on)
        ]
        if not candidates:
            return None
        candidates.sort(key=lambda task: (-task.priority, task.created_at, str(task.id)))
        selected = candidates[0]
        updated = selected.model_copy(
            update={"status": TaskStatus.IN_PROGRESS, "updated_at": utc_now()}
        )
        ctx.tasks = [updated if task.id == selected.id else task for task in ctx.tasks]
        ctx.memory.working.active_task = updated
        return updated

    async def mark_done(self, ctx: RunContext, task_id: UUID) -> None:
        found = False
        updated_tasks: list[ResearchTask] = []
        for task in ctx.tasks:
            if task.id != task_id:
                updated_tasks.append(task)
                continue
            found = True
            updated_tasks.append(
                task.model_copy(update={"status": TaskStatus.DONE, "updated_at": utc_now()})
            )
        if not found:
            raise PlanningError(
                "Cannot mark unknown task as done",
                details={"task_id": str(task_id)},
            )
        ctx.tasks = updated_tasks
        if ctx.memory.working.active_task and ctx.memory.working.active_task.id == task_id:
            ctx.memory.working.active_task = None

    async def enqueue_from_questions(
        self,
        ctx: RunContext,
        questions: list[str],
        *,
        priority: int = 60,
    ) -> list[ResearchTask]:
        cleaned = [question.strip() for question in questions if question.strip()]
        if not cleaned:
            return []

        investigation = _ensure_emerging_investigation(ctx, priority=priority)
        existing_titles = {task.title.casefold() for task in ctx.tasks}
        created: list[ResearchTask] = []
        for question in cleaned:
            if question.casefold() in existing_titles:
                continue
            task = ResearchTask(
                investigation_id=investigation.id,
                title=question,
                description=f"Investigate open question: {question}",
                priority=priority,
                status=TaskStatus.PENDING,
                suggested_tools=[],
                metadata={"source": "open_question"},
            )
            created.append(task)
            existing_titles.add(question.casefold())

        ctx.tasks.extend(created)
        for question in cleaned:
            if question not in ctx.memory.working.open_questions:
                ctx.memory.working.open_questions.append(question)
        return created


def _task_from_investigation(investigation: Investigation) -> ResearchTask:
    return ResearchTask(
        investigation_id=investigation.id,
        title=investigation.title,
        description=investigation.rationale or f"Investigate: {investigation.title}",
        priority=investigation.priority,
        status=TaskStatus.PENDING,
        suggested_tools=list(investigation.suggested_tools),
        metadata={"source": "investigation"},
    )


def _ensure_emerging_investigation(ctx: RunContext, *, priority: int) -> Investigation:
    plan = ctx.plan
    if plan is None:
        # Runtime normally always has a plan before enqueue; keep a local
        # placeholder investigation id if called early in tests.
        return Investigation(
            id=uuid4(),
            title=EMERGING_QUESTIONS_TITLE,
            rationale="Questions discovered during research",
            priority=priority,
        )

    for investigation in plan.investigations:
        if investigation.title.casefold() == EMERGING_QUESTIONS_TITLE.casefold():
            if investigation.status is TaskStatus.CANCELLED:
                investigation.status = TaskStatus.PENDING
            return investigation

    emerging = Investigation(
        title=EMERGING_QUESTIONS_TITLE,
        rationale="Questions discovered during research that need follow-up.",
        priority=priority,
        status=TaskStatus.PENDING,
    )
    ctx.plan = plan.model_copy(update={"investigations": [*plan.investigations, emerging]})
    return emerging
