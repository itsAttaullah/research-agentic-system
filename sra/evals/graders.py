"""End-state eval grading for completed research runs."""

from __future__ import annotations

from pydantic import BaseModel, Field

from sra.models.enums import AgentState, ReportFormat
from sra.runtime.result import RunOutcome


class EvalCheck(BaseModel):
    name: str
    passed: bool
    detail: str = ""


class EndStateGrade(BaseModel):
    """Outcome-oriented grade — verifies state produced by the agent, not prose style."""

    passed: bool
    score: float = Field(ge=0.0, le=1.0)
    checks: list[EvalCheck] = Field(default_factory=list)


def grade_run_outcome(
    outcome: RunOutcome,
    *,
    require_reports: bool = True,
    require_tool_use: bool = False,
    min_confidence: float | None = None,
) -> EndStateGrade:
    """Grade a finished run by durable end-state properties."""
    ctx = outcome.context
    checks: list[EvalCheck] = []

    checks.append(
        EvalCheck(
            name="terminal_completed",
            passed=ctx.state is AgentState.COMPLETED,
            detail=f"state={ctx.state.value}",
        )
    )
    checks.append(
        EvalCheck(
            name="has_plan",
            passed=ctx.plan is not None and bool(ctx.plan.goal_summary.strip()),
            detail="plan missing" if ctx.plan is None else "ok",
        )
    )
    if require_reports:
        has_md_or_json = any(
            artifact.format in {ReportFormat.MARKDOWN, ReportFormat.JSON}
            and (artifact.content or artifact.path)
            for artifact in outcome.artifacts
        )
        checks.append(
            EvalCheck(
                name="has_report_artifact",
                passed=has_md_or_json,
                detail=f"artifacts={len(outcome.artifacts)}",
            )
        )
    if require_tool_use:
        checks.append(
            EvalCheck(
                name="used_tools",
                passed=any(item.success for item in ctx.tool_history),
                detail=f"tool_calls={len(ctx.tool_history)}",
            )
        )
    if min_confidence is not None:
        overall = ctx.confidence.overall
        checks.append(
            EvalCheck(
                name="min_confidence",
                passed=overall >= min_confidence,
                detail=f"overall={overall:.3f} threshold={min_confidence:.3f}",
            )
        )

    passed_count = sum(1 for check in checks if check.passed)
    score = passed_count / len(checks) if checks else 0.0
    return EndStateGrade(passed=all(check.passed for check in checks), score=score, checks=checks)
