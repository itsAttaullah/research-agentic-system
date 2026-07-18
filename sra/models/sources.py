"""Source records and provenance used by memory and knowledge layers."""

from datetime import datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, HttpUrl

from sra.core.time import utc_now
from sra.models.enums import TrustTier


class SourceRecord(BaseModel):
    """A visited or cached source with identity, trust, and content fingerprint."""

    source_id: UUID = Field(default_factory=uuid4)
    url: str | None = Field(
        default=None,
        description="Canonical URL when applicable; local paths use path instead.",
    )
    path: str | None = None
    title: str = ""
    source_type: str = Field(
        default="web",
        description="web | pdf | html | markdown | news | academic | github | reddit | youtube | local",
    )
    trust_tier: TrustTier = TrustTier.UNKNOWN
    content_hash: str = Field(
        default="",
        description="Hash of normalized content used for deduplication.",
    )
    visited_at: datetime = Field(default_factory=utc_now)
    retrieved_at: datetime | None = None
    http_status: int | None = None
    notes: str = ""

    def identity_key(self) -> str:
        """Stable key for visited-source deduplication."""
        if self.content_hash:
            return f"hash:{self.content_hash}"
        if self.url:
            return f"url:{self.url.rstrip('/').lower()}"
        if self.path:
            return f"path:{self.path}"
        return f"id:{self.source_id}"


class Citation(BaseModel):
    """Pointer from a knowledge unit back to a source (and optional locator)."""

    source_id: UUID
    quote: str = ""
    locator: str = Field(
        default="",
        description="Page, paragraph, timestamp, or section anchor.",
    )
    url: HttpUrl | str | None = None
