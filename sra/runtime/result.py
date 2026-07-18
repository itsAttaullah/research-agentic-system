"""Public runtime options and run outcome models."""

from dataclasses import dataclass

from sra.core.context import RunContext
from sra.models.enums import ReportFormat
from sra.models.reporting import ReportArtifact


@dataclass(frozen=True, slots=True)
class RuntimeOptions:
    """Mechanical runtime policy; contains no research strategy."""

    confidence_threshold: float = 0.7
    report_formats: tuple[ReportFormat, ...] = (ReportFormat.MARKDOWN,)
    max_consecutive_invalid_actions: int = 2

    def __post_init__(self) -> None:
        if not 0.0 <= self.confidence_threshold <= 1.0:
            msg = "confidence_threshold must be between 0.0 and 1.0"
            raise ValueError(msg)
        if not self.report_formats:
            msg = "At least one report format is required"
            raise ValueError(msg)
        if self.max_consecutive_invalid_actions < 0:
            msg = "max_consecutive_invalid_actions cannot be negative"
            raise ValueError(msg)


@dataclass(frozen=True, slots=True)
class RunOutcome:
    """Terminal runtime result returned to API or CLI callers."""

    context: RunContext
    artifacts: tuple[ReportArtifact, ...] = ()
