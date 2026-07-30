"""Unit tests for end-state eval grading."""

from __future__ import annotations

from sra.core.context import RunContext
from sra.evals import grade_run_outcome
from sra.models.enums import AgentState, ReportFormat
from sra.models.goal import ResearchGoal
from sra.models.plan import ResearchPlan
from sra.models.reporting import ReportArtifact
from sra.runtime.result import RunOutcome


def test_grade_run_outcome_requires_completed_plan_and_report() -> None:
    ctx = RunContext.create(ResearchGoal(question="Should we build X?"))
    ctx.state = AgentState.COMPLETED
    ctx.plan = ResearchPlan(goal_summary="Build X?")
    outcome = RunOutcome(
        ctx,
        artifacts=(
            ReportArtifact(
                report_id=ctx.run_id,
                run_id=ctx.run_id,
                format=ReportFormat.MARKDOWN,
                content="# Report\n\nExecutive Summary",
            ),
        ),
    )
    grade = grade_run_outcome(outcome, require_tool_use=False)
    assert grade.passed is True
    assert grade.score == 1.0


def test_grade_run_outcome_fails_when_still_researching() -> None:
    ctx = RunContext.create(ResearchGoal(question="Should we build X?"))
    ctx.state = AgentState.RESEARCHING
    grade = grade_run_outcome(RunOutcome(ctx), require_reports=False)
    assert grade.passed is False
    assert any(not check.passed for check in grade.checks if check.name == "terminal_completed")
