"""Report request / artifact models."""

from datetime import datetime
from pathlib import Path
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from sra.core.time import utc_now
from sra.models.enums import ReportFormat
from sra.models.reflection import ConfidenceMap


class ReportSection(BaseModel):
    title: str
    body_markdown: str
    order: int = 0


class ReportDocument(BaseModel):
    """Canonical in-memory report before format rendering."""

    report_id: UUID = Field(default_factory=uuid4)
    run_id: UUID
    title: str
    sections: list[ReportSection] = Field(default_factory=list)
    confidence: ConfidenceMap = Field(default_factory=ConfidenceMap)
    references: list[str] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=utc_now)


class ReportArtifact(BaseModel):
    """Rendered report on disk or as inline content."""

    report_id: UUID
    run_id: UUID
    format: ReportFormat
    path: Path | None = None
    content: str | None = None
    created_at: datetime = Field(default_factory=utc_now)
