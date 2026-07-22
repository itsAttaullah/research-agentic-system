"""Low-level persistence for crash-safe RunSnapshots."""

from __future__ import annotations

from uuid import UUID

import aiosqlite

from sra.core.errors import CheckpointError
from sra.models.checkpoint import RunSnapshot
from sra.storage.sqlite import SqliteControlPlane


class CheckpointStore:
    """SQLite repository for full-run checkpoint payloads."""

    def __init__(self, db: SqliteControlPlane) -> None:
        self._db = db

    async def insert(self, snapshot: RunSnapshot) -> RunSnapshot:
        conn = await self._db.connect()
        try:
            await conn.execute(
                """
                INSERT INTO checkpoints (snapshot_id, run_id, state, payload, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    str(snapshot.snapshot_id),
                    str(snapshot.run_id),
                    snapshot.state.value,
                    snapshot.model_dump_json(),
                    snapshot.created_at.isoformat(),
                ),
            )
            await conn.commit()
        except Exception as exc:  # noqa: BLE001 - normalize adapter failures
            await conn.rollback()
            raise CheckpointError(
                "Failed to persist checkpoint snapshot",
                details={
                    "run_id": str(snapshot.run_id),
                    "snapshot_id": str(snapshot.snapshot_id),
                    "error": str(exc),
                },
            ) from exc
        return snapshot

    async def get(self, snapshot_id: UUID) -> RunSnapshot | None:
        conn = await self._db.connect()
        cursor = await conn.execute(
            "SELECT payload FROM checkpoints WHERE snapshot_id = ?",
            (str(snapshot_id),),
        )
        row = await cursor.fetchone()
        if row is None:
            return None
        return _row_to_snapshot(row)

    async def latest_for_run(self, run_id: UUID) -> RunSnapshot | None:
        conn = await self._db.connect()
        cursor = await conn.execute(
            """
            SELECT payload FROM checkpoints
            WHERE run_id = ?
            ORDER BY created_at DESC, snapshot_id DESC
            LIMIT 1
            """,
            (str(run_id),),
        )
        row = await cursor.fetchone()
        if row is None:
            return None
        return _row_to_snapshot(row)

    async def list_for_run(self, run_id: UUID) -> list[RunSnapshot]:
        conn = await self._db.connect()
        cursor = await conn.execute(
            """
            SELECT payload FROM checkpoints
            WHERE run_id = ?
            ORDER BY created_at ASC, snapshot_id ASC
            """,
            (str(run_id),),
        )
        rows = await cursor.fetchall()
        return [_row_to_snapshot(row) for row in rows]


def _row_to_snapshot(row: aiosqlite.Row) -> RunSnapshot:
    try:
        return RunSnapshot.model_validate_json(row["payload"])
    except Exception as exc:  # noqa: BLE001
        raise CheckpointError(
            "Failed to deserialize checkpoint snapshot",
            details={"error": str(exc)},
        ) from exc
