"""CLI entrypoint wrapping the same composition root as the API."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from uuid import UUID

from sra.core.config import Settings
from sra.core.errors import SRAError
from sra.evals import grade_run_outcome
from sra.models.budget import BudgetLimits
from sra.models.goal import ResearchGoal
from sra.runtime.composition import build_runtime_from_settings
from sra.storage import SqliteControlPlane


def app() -> None:
    """Console script entrypoint configured in pyproject.toml."""
    raise SystemExit(main(sys.argv[1:]))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="sra",
        description="Strategic Research Agent — autonomous research CLI",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    run_parser = sub.add_parser("run", help="Start a new research run")
    run_parser.add_argument("question", help="Research question")
    run_parser.add_argument(
        "--criterion",
        action="append",
        default=[],
        help="Success criterion (repeatable)",
    )
    run_parser.add_argument("--max-iterations", type=int, default=None)
    run_parser.add_argument("--max-cost-usd", type=float, default=None)
    run_parser.add_argument(
        "--grade",
        action="store_true",
        help="Print an end-state eval grade after the run",
    )

    resume_parser = sub.add_parser("resume", help="Resume a run from its latest checkpoint")
    resume_parser.add_argument("run_id", help="Run UUID to resume")
    resume_parser.add_argument("--grade", action="store_true")

    args = parser.parse_args(argv)
    try:
        if args.command == "run":
            return asyncio.run(_cmd_run(args))
        if args.command == "resume":
            return asyncio.run(_cmd_resume(args))
    except SRAError as exc:
        print(f"error: {exc.message}", file=sys.stderr)
        return 2
    except Exception as exc:  # noqa: BLE001
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 1


async def _cmd_run(args: argparse.Namespace) -> int:
    settings = Settings()
    settings.ensure_data_dir()
    db = SqliteControlPlane(settings.control_db)
    await db.connect()
    try:
        runtime = build_runtime_from_settings(settings=settings, control_db=db)
        limits = BudgetLimits(
            max_iterations=args.max_iterations or settings.max_iterations,
            max_tokens=settings.max_tokens,
            max_cost_usd=args.max_cost_usd or settings.max_cost_usd,
            max_minutes=settings.max_minutes,
            max_sources=settings.max_sources,
        )
        goal = ResearchGoal(question=args.question, success_criteria=list(args.criterion))
        outcome = await runtime.start(goal, limits=limits)
        _print_outcome(outcome, grade=bool(args.grade))
        return 0 if outcome.context.error_message == "" else 1
    finally:
        await db.close()


async def _cmd_resume(args: argparse.Namespace) -> int:
    settings = Settings()
    settings.ensure_data_dir()
    db = SqliteControlPlane(settings.control_db)
    await db.connect()
    try:
        runtime = build_runtime_from_settings(settings=settings, control_db=db)
        outcome = await runtime.resume(UUID(args.run_id))
        _print_outcome(outcome, grade=bool(args.grade))
        return 0
    finally:
        await db.close()


def _print_outcome(outcome: object, *, grade: bool) -> None:
    from sra.runtime.result import RunOutcome

    assert isinstance(outcome, RunOutcome)
    paths = [str(artifact.path) for artifact in outcome.artifacts if artifact.path is not None]
    payload: dict[str, object] = {
        "run_id": str(outcome.context.run_id),
        "state": outcome.context.state.value,
        "iterations": outcome.context.budget.usage.iterations,
        "report_paths": paths,
        "error": outcome.context.error_message or None,
    }
    if grade:
        payload["grade"] = grade_run_outcome(outcome).model_dump(mode="json")
    print(json.dumps(payload, indent=2))
    for path in paths:
        print(f"report: {path}", file=sys.stderr)


if __name__ == "__main__":
    app()
