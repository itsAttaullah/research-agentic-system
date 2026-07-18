"""Timezone-aware UTC helpers (datetime.utcnow is deprecated on 3.12+)."""

from datetime import UTC, datetime


def utc_now() -> datetime:
    return datetime.now(UTC)
