"""Integration test: end-to-end research run with real adapters + scripted engine."""

from __future__ import annotations

from pathlib import Path

import pytest
from sra.budget import DefaultBudgetManager
from sra.checkpoint import SqliteCheckpointManager
from sra.confidence import EvidenceConfidenceEstimator
from sra.core.config import Settings
from sra.core.ports.llm import LLMRequest, LLMResponse
from sra.memory import SqliteMemoryManager
from sra.models.actions import FinalizeAction, InvokeToolAction
from sra.models.budget import BudgetLimits
from sra.models.enums import AgentState, ReportFormat
from sra.models.goal import ResearchGoal
from sra.models.reflection import CritiqueResult, ReflectionResult
from sra.observability import StructlogExecutionLogger
from sra.reporting import ResearchReportGenerator
from sra.runtime import ResearchRuntime, RuntimeDependencies, RuntimeOptions, build_runtime
from sra.storage import SqliteControlPlane
from sra.tasks import DefaultTaskManager
from sra.tools import InMemoryToolRegistry
from sra.tools.compute import CalculatorTool

from tests.unit.runtime_fakes import FakeCritic, FakePlanner, FakeReflection, FakeResearchEngine


class ScriptedLLM:
    async def complete(self, request: LLMRequest) -> LLMResponse:
        return LLMResponse(content="{}", raw_json={}, model="fake")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_end_to_end_run_with_real_storage_and_reporting(tmp_path: Path) -> None:
    db = SqliteControlPlane(tmp_path / "control.sqlite3")
    await db.connect()
    try:
        registry = InMemoryToolRegistry()
        registry.register(CalculatorTool())

        runtime = ResearchRuntime(
            RuntimeDependencies(
                planner=FakePlanner(),
                task_manager=DefaultTaskManager(),
                research_engine=FakeResearchEngine(
                    [
                        InvokeToolAction(
                            tool_name="calculator",
                            arguments={"expression": "10 + 5"},
                            rationale="Sanity compute step",
                        ),
                        FinalizeAction(summary="Enough for a draft recommendation"),
                    ]
                ),
                tools=registry,
                memory=SqliteMemoryManager(db),
                reflection=FakeReflection(
                    ReflectionResult(
                        answered_questions=[],
                        new_questions=["What is willingness to pay?"],
                        should_continue=True,
                        evidence_quality=0.7,
                        notes="Calculator step complete",
                    )
                ),
                critic=FakeCritic(CritiqueResult(passed=True, summary="Pass gate")),
                confidence=EvidenceConfidenceEstimator(),
                budget=DefaultBudgetManager(),
                checkpoints=SqliteCheckpointManager(db),
                logger=StructlogExecutionLogger(),
                reports=ResearchReportGenerator(output_dir=tmp_path / "reports"),
            ),
            options=RuntimeOptions(
                confidence_threshold=0.7,
                report_formats=(ReportFormat.MARKDOWN, ReportFormat.JSON),
            ),
        )

        goal = ResearchGoal(question="Should I build an AI startup for dentists?")
        outcome = await runtime.start(goal, limits=BudgetLimits(max_iterations=10))

        assert outcome.context.state is AgentState.COMPLETED
        assert len(outcome.artifacts) == 2
        assert outcome.context.tool_history[-1].success is True
        assert outcome.context.tool_history[-1].output["result"] == 15

        checkpoints = SqliteCheckpointManager(db)
        history = await checkpoints.list_for_run(outcome.context.run_id)
        assert len(history) >= 3
        assert history[-1].state is AgentState.COMPLETED

        resumed = await runtime.resume(outcome.context.run_id)
        assert resumed.context.state is AgentState.COMPLETED
        assert resumed.context.run_id == outcome.context.run_id

        assert all(
            artifact.path is not None and artifact.path.exists() for artifact in outcome.artifacts
        )
        markdown = next(item for item in outcome.artifacts if item.format is ReportFormat.MARKDOWN)
        assert markdown.content is not None
        assert "Executive Summary" in markdown.content
    finally:
        await db.close()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_build_runtime_composition_smoke(tmp_path: Path) -> None:
    settings = Settings(
        data_dir=tmp_path / "data",
        control_db=tmp_path / "data" / "control.sqlite3",
        knowledge_db=tmp_path / "data" / "knowledge.duckdb",
        local_document_roots=str(tmp_path / "data"),
    )
    settings.ensure_data_dir()
    runtime = build_runtime(ScriptedLLM(), settings=settings, report_output_dir=tmp_path / "out")
    assert isinstance(runtime, ResearchRuntime)
