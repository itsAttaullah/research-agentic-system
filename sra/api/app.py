"""Thin FastAPI surface over the research runtime (no agent logic here)."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any
from uuid import UUID

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from sra.core.config import Settings
from sra.core.errors import SRAError
from sra.models.budget import BudgetLimits
from sra.models.goal import ResearchGoal
from sra.runtime.composition import build_runtime_from_settings
from sra.storage import SqliteControlPlane


class StartRunRequest(BaseModel):
    question: str = Field(min_length=1)
    success_criteria: list[str] = Field(default_factory=list)
    max_iterations: int | None = None
    max_cost_usd: float | None = None


class RunResponse(BaseModel):
    run_id: UUID
    state: str
    report_paths: list[str] = Field(default_factory=list)
    error: str | None = None


def create_app(settings: Settings | None = None) -> FastAPI:
    cfg = settings or Settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        cfg.ensure_data_dir()
        db = SqliteControlPlane(cfg.control_db)
        await db.connect()
        app.state.db = db
        app.state.runtime = build_runtime_from_settings(settings=cfg, control_db=db)
        yield
        await db.close()

    app = FastAPI(title="Strategic Research Agent", version="0.1.0", lifespan=lifespan)

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/runs", response_model=RunResponse)
    async def start_run(body: StartRunRequest) -> RunResponse:
        runtime = app.state.runtime
        limits = BudgetLimits(
            max_iterations=body.max_iterations or cfg.max_iterations,
            max_tokens=cfg.max_tokens,
            max_cost_usd=body.max_cost_usd or cfg.max_cost_usd,
            max_minutes=cfg.max_minutes,
            max_sources=cfg.max_sources,
        )
        goal = ResearchGoal(question=body.question, success_criteria=body.success_criteria)
        try:
            outcome = await runtime.start(goal, limits=limits)
        except SRAError as exc:
            raise HTTPException(status_code=400, detail=exc.message) from exc
        return _to_response(outcome)

    @app.post("/runs/{run_id}/resume", response_model=RunResponse)
    async def resume_run(run_id: UUID) -> RunResponse:
        runtime = app.state.runtime
        try:
            outcome = await runtime.resume(run_id)
        except LookupError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except SRAError as exc:
            raise HTTPException(status_code=400, detail=exc.message) from exc
        return _to_response(outcome)

    return app


def _to_response(outcome: Any) -> RunResponse:
    return RunResponse(
        run_id=outcome.context.run_id,
        state=outcome.context.state.value,
        report_paths=[
            str(artifact.path) for artifact in outcome.artifacts if artifact.path is not None
        ],
        error=outcome.context.error_message or None,
    )
