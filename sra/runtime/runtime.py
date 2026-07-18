"""Provider-independent autonomous research decision loop."""

from __future__ import annotations

from uuid import UUID

from sra.core.context import RunContext
from sra.core.errors import InvalidActionError
from sra.core.state_machine import can_transition
from sra.models.actions import (
    AgentAction,
    FinalizeAction,
    InvokeToolAction,
    ReflectAction,
    RequestCriticAction,
    UpdatePlanAction,
)
from sra.models.budget import BudgetLimits
from sra.models.enums import AgentState
from sra.models.goal import ResearchGoal
from sra.models.reporting import ReportArtifact
from sra.models.tools import ToolCall, ToolResult
from sra.runtime.dependencies import RuntimeDependencies
from sra.runtime.lifecycle import StateController
from sra.runtime.result import RunOutcome, RuntimeOptions
from sra.runtime.validation import ActionValidator


class ResearchRuntime:
    """Execute validated agent decisions until the run reaches a terminal state.

    Research strategy remains in injected reasoning components. This class owns
    only orchestration, safety, lifecycle, persistence, and budget enforcement.
    """

    def __init__(
        self,
        dependencies: RuntimeDependencies,
        *,
        options: RuntimeOptions | None = None,
    ) -> None:
        self._deps = dependencies
        self._options = options or RuntimeOptions()
        self._states = StateController(dependencies.checkpoints, dependencies.logger)
        self._validator = ActionValidator(dependencies.tools)

    async def start(
        self,
        goal: ResearchGoal,
        *,
        limits: BudgetLimits | None = None,
    ) -> RunOutcome:
        """Create and execute a new research run."""
        ctx = RunContext.create(goal, limits=limits)
        return await self.run(ctx)

    async def resume(self, run_id: UUID) -> RunOutcome:
        """Resume the latest durable snapshot for ``run_id``."""
        snapshot = await self._deps.checkpoints.latest(run_id)
        if snapshot is None:
            raise LookupError(f"No checkpoint exists for run {run_id}")
        return await self.run(RunContext.from_snapshot(snapshot))

    async def pause(self, ctx: RunContext) -> None:
        """Persist a cooperative pause at the next caller-controlled boundary."""
        if ctx.state in {AgentState.COMPLETED, AgentState.FAILED, AgentState.WAITING}:
            return
        await self._states.transition(ctx, AgentState.WAITING)

    async def run(self, ctx: RunContext) -> RunOutcome:
        """Continue ``ctx`` from its current durable state."""
        try:
            return await self._continue(ctx)
        except Exception as exc:
            await self._mark_failed(ctx, exc)
            raise

    async def _continue(self, ctx: RunContext) -> RunOutcome:
        artifacts = await self._restore_execution_point(ctx)
        if artifacts is not None:
            return RunOutcome(ctx, artifacts)

        invalid_actions = 0
        while ctx.state not in {AgentState.COMPLETED, AgentState.FAILED, AgentState.WAITING}:
            await self._deps.budget.check_or_raise(ctx)
            await self._deps.budget.record_iteration(ctx)

            action = await self._deps.research_engine.propose_action(
                ctx,
                available_tools=self._deps.tools.list_descriptors(),
            )
            try:
                self._validator.validate(action, ctx)
            except InvalidActionError as exc:
                invalid_actions += 1
                await self._record_invalid_action(ctx, exc, invalid_actions)
                if invalid_actions > self._options.max_consecutive_invalid_actions:
                    raise
                continue

            invalid_actions = 0
            artifacts = await self._dispatch(ctx, action)
            if artifacts is not None:
                return RunOutcome(ctx, artifacts)

        return RunOutcome(ctx)

    async def _restore_execution_point(
        self,
        ctx: RunContext,
    ) -> tuple[ReportArtifact, ...] | None:
        if ctx.state in {AgentState.COMPLETED, AgentState.FAILED, AgentState.WAITING}:
            if ctx.state is AgentState.WAITING:
                target = AgentState.RESEARCHING if ctx.plan is not None else AgentState.PLANNING
                await self._states.transition(ctx, target)
            else:
                return ()

        if ctx.state is AgentState.IDLE:
            await self._create_initial_plan(ctx)
        elif ctx.state is AgentState.PLANNING:
            await self._complete_planning(ctx)
        elif ctx.state in {AgentState.READING, AgentState.EXTRACTING}:
            # Tool calls are not replayed automatically: side effects may not be
            # idempotent. Resume from reflection using the durable observations.
            await self._states.transition(ctx, AgentState.REFLECTING)
            await self._perform_reflection(ctx)
        elif ctx.state is AgentState.REFLECTING:
            await self._perform_reflection(ctx)
        elif ctx.state is AgentState.GENERATING_REPORT:
            return await self._generate_reports(ctx)
        return None

    async def _create_initial_plan(self, ctx: RunContext) -> None:
        await self._states.transition(ctx, AgentState.PLANNING)
        ctx.plan = await self._deps.planner.create_plan(ctx)
        await self._complete_planning(ctx)

    async def _complete_planning(self, ctx: RunContext) -> None:
        if ctx.plan is None:
            ctx.plan = await self._deps.planner.create_plan(ctx)
        ctx.memory.working.plan = ctx.plan
        ctx.tasks = await self._deps.task_manager.sync_tasks(ctx)
        await self._states.checkpoint(ctx)
        await self._states.transition(ctx, AgentState.RESEARCHING)

    async def _dispatch(
        self,
        ctx: RunContext,
        action: AgentAction,
    ) -> tuple[ReportArtifact, ...] | None:
        await self._deps.logger.log(
            ctx,
            "agent_action",
            f"Dispatching {action.kind.value}",
            data={"action": action.model_dump(mode="json")},
        )
        if isinstance(action, InvokeToolAction):
            await self._invoke_tool(ctx, action)
            return None
        if isinstance(action, UpdatePlanAction):
            await self._apply_plan_update(ctx, action)
            return None
        if isinstance(action, ReflectAction):
            await self._reflect(ctx)
            return None
        if isinstance(action, (RequestCriticAction, FinalizeAction)):
            return await self._critique_and_maybe_finalize(ctx)
        raise InvalidActionError(f"Unsupported action: {type(action).__name__}")

    async def _invoke_tool(self, ctx: RunContext, action: InvokeToolAction) -> None:
        tool = self._deps.tools.get(action.tool_name)
        if {"read", "reader", "fetch", "document"}.intersection(tool.tags):
            await self._states.transition(ctx, AgentState.READING)

        call = ToolCall(
            tool_name=action.tool_name,
            arguments=action.arguments,
            related_task_id=action.related_task_id,
        )
        await self._deps.logger.log(
            ctx,
            "tool_call",
            f"Executing tool {call.tool_name}",
            data={"call": call.model_dump(mode="json")},
        )
        result = await self._deps.tools.execute(call, run_id=ctx.run_id)
        await self._record_tool_result(ctx, result)

        await self._states.transition(ctx, AgentState.REFLECTING)
        await self._perform_reflection(ctx, latest_tool_result=result)

    async def _record_tool_result(self, ctx: RunContext, result: ToolResult) -> None:
        ctx.tool_history.append(result)
        ctx.memory.working.recent_tool_call_ids.append(result.call_id)
        await self._deps.budget.record_tool_usage(
            ctx,
            cost_usd=result.cost_usd,
            sources_delta=1 if result.success else 0,
        )
        await self._deps.logger.log(
            ctx,
            "tool_result",
            f"Tool {result.tool_name} {'succeeded' if result.success else 'failed'}",
            data={"result": result.model_dump(mode="json")},
        )
        await self._states.checkpoint(ctx)
        await self._deps.budget.check_or_raise(ctx)

    async def _apply_plan_update(self, ctx: RunContext, action: UpdatePlanAction) -> None:
        await self._states.transition(ctx, AgentState.PLANNING)
        ctx.plan = action.plan
        ctx.memory.working.plan = action.plan
        ctx.tasks = await self._deps.task_manager.sync_tasks(ctx)
        await self._states.checkpoint(ctx)
        await self._states.transition(ctx, AgentState.RESEARCHING)

    async def _reflect(self, ctx: RunContext) -> None:
        await self._states.transition(ctx, AgentState.REFLECTING)
        await self._perform_reflection(ctx)

    async def _perform_reflection(
        self,
        ctx: RunContext,
        *,
        latest_tool_result: ToolResult | None = None,
    ) -> None:
        reflection = await self._deps.reflection.reflect(
            ctx,
            latest_tool_result=latest_tool_result,
        )
        ctx.last_reflection = reflection
        ctx.confidence = await self._deps.confidence.estimate(ctx)
        ctx.memory.working.open_questions.extend(
            question
            for question in reflection.new_questions
            if question not in ctx.memory.working.open_questions
        )
        if reflection.new_questions:
            await self._enqueue_questions(ctx, reflection.new_questions)

        low_topics = self._deps.confidence.below_threshold(
            ctx.confidence,
            threshold=self._options.confidence_threshold,
        )
        if low_topics:
            questions = [f"Increase evidence confidence for: {topic}" for topic in low_topics]
            await self._enqueue_questions(ctx, questions, priority=70)

        await self._deps.logger.log(
            ctx,
            "reflection",
            "Research step reflected and confidence updated",
            data={
                "reflection": reflection.model_dump(mode="json"),
                "confidence": ctx.confidence.model_dump(mode="json"),
            },
        )
        await self._states.checkpoint(ctx)

        if reflection.strategy_should_change:
            await self._replan(
                ctx,
                reason=reflection.strategy_change_summary or "Reflection requested replanning",
            )
        else:
            await self._states.transition(ctx, AgentState.RESEARCHING)

    async def _enqueue_questions(
        self,
        ctx: RunContext,
        questions: list[str],
        *,
        priority: int = 60,
    ) -> None:
        created = await self._deps.task_manager.enqueue_from_questions(
            ctx,
            questions,
            priority=priority,
        )
        known_ids = {task.id for task in ctx.tasks}
        ctx.tasks.extend(task for task in created if task.id not in known_ids)

    async def _replan(self, ctx: RunContext, *, reason: str) -> None:
        await self._states.transition(ctx, AgentState.PLANNING)
        ctx.plan = await self._deps.planner.revise_plan(
            ctx,
            reason=reason,
            reflection=ctx.last_reflection,
            critique=ctx.last_critique,
        )
        ctx.memory.working.plan = ctx.plan
        ctx.tasks = await self._deps.task_manager.sync_tasks(ctx)
        await self._states.checkpoint(ctx)
        await self._states.transition(ctx, AgentState.RESEARCHING)

    async def _critique_and_maybe_finalize(
        self,
        ctx: RunContext,
    ) -> tuple[ReportArtifact, ...] | None:
        critique = await self._deps.critic.critique(ctx)
        ctx.last_critique = critique
        await self._deps.logger.log(
            ctx,
            "critique",
            "Critic evaluated report readiness",
            data={"critique": critique.model_dump(mode="json")},
        )
        await self._states.checkpoint(ctx)
        if not critique.passed or critique.forced_replan:
            await self._replan(ctx, reason=critique.summary or "Critic requested more research")
            return None

        await self._states.transition(ctx, AgentState.GENERATING_REPORT)
        return await self._generate_reports(ctx)

    async def _generate_reports(self, ctx: RunContext) -> tuple[ReportArtifact, ...]:
        document = await self._deps.reports.build(ctx)
        rendered = []
        for report_format in self._options.report_formats:
            rendered.append(await self._deps.reports.render(document, fmt=report_format))
        artifacts = tuple(rendered)
        await self._deps.logger.log(
            ctx,
            "report_generated",
            f"Generated {len(artifacts)} report artifact(s)",
            data={"formats": [artifact.format.value for artifact in artifacts]},
        )
        await self._states.transition(ctx, AgentState.COMPLETED)
        return artifacts

    async def _record_invalid_action(
        self,
        ctx: RunContext,
        error: InvalidActionError,
        attempt: int,
    ) -> None:
        note = f"Rejected agent action ({attempt}): {error.message}"
        ctx.memory.working.notes.append(note)
        await self._deps.logger.log(
            ctx,
            "invalid_action",
            note,
            data={"details": error.details, "attempt": attempt},
        )
        await self._states.checkpoint(ctx)

    async def _mark_failed(self, ctx: RunContext, exc: Exception) -> None:
        ctx.error_message = str(exc)
        if ctx.state in {AgentState.COMPLETED, AgentState.FAILED}:
            return
        try:
            await self._deps.logger.log(
                ctx,
                "run_failed",
                str(exc),
                data={"error_type": type(exc).__name__},
            )
            if can_transition(ctx.state, AgentState.FAILED):
                await self._states.transition(ctx, AgentState.FAILED)
            else:
                await self._states.checkpoint(ctx)
        except Exception:
            # Preserve the original failure. Persistence/logging failures are
            # observable at their own adapter boundaries and must not mask it.
            return
