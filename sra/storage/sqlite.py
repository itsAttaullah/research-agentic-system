"""Async SQLite control-plane database (runs, memory, sources, checkpoints later)."""

from __future__ import annotations

from pathlib import Path

import aiosqlite

SCHEMA = """
CREATE TABLE IF NOT EXISTS working_memory (
    run_id TEXT PRIMARY KEY,
    payload TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS visited_sources (
    run_id TEXT NOT NULL,
    identity_key TEXT NOT NULL,
    payload TEXT NOT NULL,
    visited_at TEXT NOT NULL,
    PRIMARY KEY (run_id, identity_key)
);

CREATE INDEX IF NOT EXISTS idx_visited_sources_key
    ON visited_sources(identity_key);

CREATE TABLE IF NOT EXISTS long_term_memory (
    key TEXT PRIMARY KEY,
    kind TEXT NOT NULL,
    content TEXT NOT NULL,
    metadata TEXT NOT NULL,
    created_at TEXT NOT NULL,
    source_run_id TEXT
);

CREATE INDEX IF NOT EXISTS idx_long_term_kind
    ON long_term_memory(kind);

CREATE INDEX IF NOT EXISTS idx_long_term_content
    ON long_term_memory(content);
"""


class SqliteControlPlane:
    """Owns the SQLite connection used by control-plane adapters."""

    def __init__(self, path: Path | str) -> None:
        self.path = Path(path)
        self._conn: aiosqlite.Connection | None = None

    async def connect(self) -> aiosqlite.Connection:
        if self._conn is not None:
            return self._conn
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = await aiosqlite.connect(self.path)
        self._conn.row_factory = aiosqlite.Row
        await self._conn.execute("PRAGMA foreign_keys = ON")
        await self._conn.executescript(SCHEMA)
        await self._conn.commit()
        return self._conn

    async def close(self) -> None:
        if self._conn is not None:
            await self._conn.close()
            self._conn = None

    async def __aenter__(self) -> SqliteControlPlane:
        await self.connect()
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.close()
