"""Dependency container for the research runtime.

This is deliberately a data-only composition boundary. Concrete adapters are
constructed by the future application composition root and injected here.
"""

from dataclasses import dataclass

from sra.core.ports import (
    BudgetManager,
    CheckpointManager,
    ConfidenceEstimator,
    Critic,
    ExecutionLogger,
    MemoryManager,
    Planner,
    ReflectionEngine,
    ReportGenerator,
    ResearchEngine,
    TaskManager,
    ToolRegistry,
)


@dataclass(frozen=True, slots=True)
class RuntimeDependencies:
    """Collaborators required by :class:`ResearchRuntime`."""

    planner: Planner
    task_manager: TaskManager
    research_engine: ResearchEngine
    tools: ToolRegistry
    memory: MemoryManager
    reflection: ReflectionEngine
    critic: Critic
    confidence: ConfidenceEstimator
    budget: BudgetManager
    checkpoints: CheckpointManager
    logger: ExecutionLogger
    reports: ReportGenerator
