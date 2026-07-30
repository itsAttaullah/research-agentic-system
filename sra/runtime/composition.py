"""Application composition root — wires concrete adapters into the runtime."""

from __future__ import annotations

from pathlib import Path

from sra.budget import DefaultBudgetManager
from sra.checkpoint import SqliteCheckpointManager
from sra.confidence import EvidenceConfidenceEstimator
from sra.core.config import Settings
from sra.core.ports.llm import LLMClient
from sra.critic import LLMCritic
from sra.llm import build_llm_client
from sra.memory import SqliteMemoryManager
from sra.observability import StructlogExecutionLogger
from sra.planner import LLMPlanner
from sra.reflection import LLMReflectionEngine
from sra.reporting import ResearchReportGenerator
from sra.research import LLMResearchEngine
from sra.runtime.dependencies import RuntimeDependencies
from sra.runtime.result import RuntimeOptions
from sra.runtime.runtime import ResearchRuntime
from sra.storage import SqliteControlPlane
from sra.tasks import DefaultTaskManager
from sra.tools import create_default_registry


def build_runtime(
    llm: LLMClient,
    *,
    settings: Settings | None = None,
    control_db: SqliteControlPlane | None = None,
    report_output_dir: Path | str | None = None,
) -> ResearchRuntime:
    """Compose a production ResearchRuntime from settings and an LLM client.

    LLM provider adapters are injected by the caller so OpenAI/Anthropic can be
    swapped without changing orchestration code.
    """
    cfg = settings or Settings()
    db = control_db or SqliteControlPlane(cfg.control_db)
    reports_dir = Path(report_output_dir) if report_output_dir else cfg.data_dir / "reports"

    tools = create_default_registry(cfg)
    dependencies = RuntimeDependencies(
        planner=LLMPlanner(llm),
        task_manager=DefaultTaskManager(),
        research_engine=LLMResearchEngine(llm),
        tools=tools,
        memory=SqliteMemoryManager(db),
        reflection=LLMReflectionEngine(llm),
        critic=LLMCritic(llm),
        confidence=EvidenceConfidenceEstimator(),
        budget=DefaultBudgetManager(),
        checkpoints=SqliteCheckpointManager(db),
        logger=StructlogExecutionLogger(),
        reports=ResearchReportGenerator(output_dir=reports_dir),
    )
    options = RuntimeOptions(
        confidence_threshold=cfg.confidence_threshold,
        tool_autonomy=cfg.tool_autonomy,
    )
    return ResearchRuntime(dependencies, options=options)


def build_runtime_from_settings(
    *,
    settings: Settings | None = None,
    control_db: SqliteControlPlane | None = None,
    report_output_dir: Path | str | None = None,
) -> ResearchRuntime:
    """Compose a runtime using the configured OpenAI/Anthropic adapter."""
    cfg = settings or Settings()
    return build_runtime(
        build_llm_client(cfg),
        settings=cfg,
        control_db=control_db,
        report_output_dir=report_output_dir,
    )
