"""Shared Pydantic domain models: ResearchGoal, ResearchPlan, AgentAction,
KnowledgeUnit, SourceRecord, ReflectionResult, ConfidenceMap, CritiqueResult,
RunSnapshot, BudgetLedger.

These are the contracts between packages; no behavior lives here beyond
lightweight pure helpers on the models themselves.
"""

from sra.models.actions import (
    AgentAction,
    FinalizeAction,
    InvokeToolAction,
    ReflectAction,
    RequestCriticAction,
    UpdatePlanAction,
)
from sra.models.budget import BudgetLedger, BudgetLimits, BudgetUsage
from sra.models.checkpoint import RunSnapshot
from sra.models.enums import (
    ActionKind,
    AgentState,
    KnowledgeKind,
    ReportFormat,
    TaskStatus,
    TrustTier,
)
from sra.models.goal import ResearchGoal, RunIdentity
from sra.models.knowledge import Disagreement, ExtractionResult, KnowledgeUnit
from sra.models.memory import LongTermMemoryEntry, MemorySnapshot, WorkingMemory
from sra.models.plan import Investigation, PlanRevision, ResearchPlan, ResearchTask
from sra.models.reflection import (
    ConfidenceMap,
    CritiqueFinding,
    CritiqueResult,
    ReflectionResult,
    TopicConfidence,
)
from sra.models.reporting import ReportArtifact, ReportDocument, ReportSection
from sra.models.sources import Citation, SourceRecord
from sra.models.tools import ToolCall, ToolDescriptor, ToolResult

__all__ = [
    "ActionKind",
    "AgentAction",
    "AgentState",
    "BudgetLedger",
    "BudgetLimits",
    "BudgetUsage",
    "Citation",
    "ConfidenceMap",
    "CritiqueFinding",
    "CritiqueResult",
    "Disagreement",
    "ExtractionResult",
    "FinalizeAction",
    "Investigation",
    "InvokeToolAction",
    "KnowledgeKind",
    "KnowledgeUnit",
    "LongTermMemoryEntry",
    "MemorySnapshot",
    "PlanRevision",
    "ReflectAction",
    "ReflectionResult",
    "ReportArtifact",
    "ReportDocument",
    "ReportFormat",
    "ReportSection",
    "RequestCriticAction",
    "ResearchGoal",
    "ResearchPlan",
    "ResearchTask",
    "RunIdentity",
    "RunSnapshot",
    "SourceRecord",
    "TaskStatus",
    "ToolCall",
    "ToolDescriptor",
    "ToolResult",
    "TopicConfidence",
    "TrustTier",
    "UpdatePlanAction",
    "WorkingMemory",
]
