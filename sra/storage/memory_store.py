"""Low-level persistence helpers for memory and visited sources."""

from __future__ import annotations

import json
import sqlite3
from typing import Any
from uuid import UUID

import aiosqlite

from sra.core.time import utc_now
from sra.models.memory import LongTermMemoryEntry, WorkingMemory
from sra.models.sources import SourceRecord
from sra.storage.sqlite import SqliteControlPlane


class MemoryStore:
    """SQLite repository for working memory, visits, and long-term entries."""

    def __init__(self, db: SqliteControlPlane) -> None:
        self._db = db

    async def save_working(self, run_id: UUID, working: WorkingMemory) -> None:
        conn = await self._db.connect()
        working.updated_at = utc_now()
        await conn.execute(
            """
            INSERT INTO working_memory (run_id, payload, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(run_id) DO UPDATE SET
                payload = excluded.payload,
                updated_at = excluded.updated_at
            """,
            (
                str(run_id),
                working.model_dump_json(),
                working.updated_at.isoformat(),
            ),
        )
        await conn.commit()

    async def load_working(self, run_id: UUID) -> WorkingMemory | None:
        conn = await self._db.connect()
        cursor = await conn.execute(
            "SELECT payload FROM working_memory WHERE run_id = ?",
            (str(run_id),),
        )
        row = await cursor.fetchone()
        if row is None:
            return None
        return WorkingMemory.model_validate_json(row["payload"])

    async def has_visit(self, run_id: UUID, identity_key: str) -> bool:
        conn = await self._db.connect()
        cursor = await conn.execute(
            """
            SELECT 1 FROM visited_sources
            WHERE run_id = ? AND identity_key = ?
            LIMIT 1
            """,
            (str(run_id), identity_key),
        )
        return await cursor.fetchone() is not None

    async def insert_visit(
        self,
        run_id: UUID,
        source: SourceRecord,
    ) -> bool:
        """Insert a visit. Returns False if the identity key already exists for the run."""
        conn = await self._db.connect()
        identity_key = source.identity_key()
        try:
            await conn.execute(
                """
                INSERT INTO visited_sources (run_id, identity_key, payload, visited_at)
                VALUES (?, ?, ?, ?)
                """,
                (
                    str(run_id),
                    identity_key,
                    source.model_dump_json(),
                    source.visited_at.isoformat(),
                ),
            )
            await conn.commit()
        except sqlite3.IntegrityError:
            await conn.rollback()
            return False
        return True

    async def list_visits(self, run_id: UUID) -> list[SourceRecord]:
        conn = await self._db.connect()
        cursor = await conn.execute(
            """
            SELECT payload FROM visited_sources
            WHERE run_id = ?
            ORDER BY visited_at ASC
            """,
            (str(run_id),),
        )
        rows = await cursor.fetchall()
        return [SourceRecord.model_validate_json(row["payload"]) for row in rows]

    async def put_long_term(self, entry: LongTermMemoryEntry) -> None:
        conn = await self._db.connect()
        await conn.execute(
            """
            INSERT INTO long_term_memory
                (key, kind, content, metadata, created_at, source_run_id)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(key) DO UPDATE SET
                kind = excluded.kind,
                content = excluded.content,
                metadata = excluded.metadata,
                created_at = excluded.created_at,
                source_run_id = excluded.source_run_id
            """,
            (
                entry.key,
                entry.kind,
                entry.content,
                json.dumps(entry.metadata),
                entry.created_at.isoformat(),
                str(entry.source_run_id) if entry.source_run_id else None,
            ),
        )
        await conn.commit()

    async def get_long_term(self, key: str) -> LongTermMemoryEntry | None:
        conn = await self._db.connect()
        cursor = await conn.execute(
            """
            SELECT key, kind, content, metadata, created_at, source_run_id
            FROM long_term_memory
            WHERE key = ?
            """,
            (key,),
        )
        row = await cursor.fetchone()
        if row is None:
            return None
        return _row_to_ltm(row)

    async def search_long_term(self, query: str, *, limit: int = 20) -> list[LongTermMemoryEntry]:
        conn = await self._db.connect()
        pattern = f"%{query.strip()}%"
        cursor = await conn.execute(
            """
            SELECT key, kind, content, metadata, created_at, source_run_id
            FROM long_term_memory
            WHERE key LIKE ? OR content LIKE ? OR kind LIKE ?
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (pattern, pattern, pattern, limit),
        )
        rows = await cursor.fetchall()
        return [_row_to_ltm(row) for row in rows]

    async def list_long_term_by_run(self, run_id: UUID) -> list[LongTermMemoryEntry]:
        conn = await self._db.connect()
        cursor = await conn.execute(
            """
            SELECT key, kind, content, metadata, created_at, source_run_id
            FROM long_term_memory
            WHERE source_run_id = ?
            ORDER BY created_at ASC
            """,
            (str(run_id),),
        )
        rows = await cursor.fetchall()
        return [_row_to_ltm(row) for row in rows]


def _row_to_ltm(row: aiosqlite.Row) -> LongTermMemoryEntry:
    metadata_raw: Any = row["metadata"]
    metadata = json.loads(metadata_raw) if isinstance(metadata_raw, str) else {}
    source_run_id = row["source_run_id"]
    return LongTermMemoryEntry(
        key=str(row["key"]),
        kind=str(row["kind"]),
        content=str(row["content"]),
        metadata=metadata if isinstance(metadata, dict) else {},
        created_at=row["created_at"],
        source_run_id=UUID(source_run_id) if source_run_id else None,
    )
