"""Shared enumerations for agent state, trust, and knowledge typing."""

from enum import StrEnum


class AgentState(StrEnum):
    """Lifecycle states of a research run. Persisted on every transition."""

    IDLE = "idle"
    PLANNING = "planning"
    RESEARCHING = "researching"
    READING = "reading"
    EXTRACTING = "extracting"
    REFLECTING = "reflecting"
    WAITING = "waiting"
    GENERATING_REPORT = "generating_report"
    COMPLETED = "completed"
    FAILED = "failed"


class TrustTier(StrEnum):
    """Source trust ranking used during validation and conflict resolution."""

    OFFICIAL = "official"  # company / product primary sites
    GOVERNMENT = "government"
    ACADEMIC = "academic"
    TRUSTED_PUBLICATION = "trusted_publication"
    NEWS = "news"
    COMMUNITY = "community"  # Reddit, forums, discussions
    BLOG = "blog"
    UNKNOWN = "unknown"


class KnowledgeKind(StrEnum):
    """Structured unit kinds stored in the knowledge store."""

    FACT = "fact"
    CLAIM = "claim"
    STATISTIC = "statistic"
    SOURCE = "source"
    COMPANY = "company"
    PRODUCT = "product"
    RISK = "risk"
    ADVANTAGE = "advantage"
    DATE = "date"


class ActionKind(StrEnum):
    """Discriminant for AgentAction variants proposed by the Research Engine."""

    INVOKE_TOOL = "invoke_tool"
    UPDATE_PLAN = "update_plan"
    REFLECT = "reflect"
    REQUEST_CRITIC = "request_critic"
    FINALIZE = "finalize"


class ReportFormat(StrEnum):
    MARKDOWN = "markdown"
    HTML = "html"
    PDF = "pdf"
    JSON = "json"


class TaskStatus(StrEnum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    DONE = "done"
    CANCELLED = "cancelled"
