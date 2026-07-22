"""SQLite-backed Checkpoint Manager for crash-safe resume."""

from __future__ import annotations

from uuid import UUID

from sra.core.context import RunContext
from sra.core.errors import CheckpointError
from sra.core.time import utc_now
from sra.models.checkpoint import RunSnapshot
from sra.storage.checkpoint_store import CheckpointStore
from sra.storage.sqlite import SqliteControlPlane


class SqliteCheckpointManager:
    """CheckpointManager port: persist full RunSnapshots after every transition."""

    def __init__(self, db: SqliteControlPlane) -> None:
        self._store = CheckpointStore(db)

    async def save(self, ctx: RunContext) -> RunSnapshot:
        ctx.touch()
        snapshot = ctx.to_snapshot()
        # Ensure each persist gets a fresh identity/timestamp even if called rapidly.
        snapshot = snapshot.model_copy(
            update={
                "created_at": utc_now(),
            }
        )
        return await self._store.insert(snapshot)

    async def latest(self, run_id: UUID) -> RunSnapshot | None:
        return await self._store.latest_for_run(run_id)

    async def load(self, snapshot_id: UUID) -> RunSnapshot:
        snapshot = await self._store.get(snapshot_id)
        if snapshot is None:
            raise CheckpointError(
                f"Checkpoint not found: {snapshot_id}",
                details={"snapshot_id": str(snapshot_id)},
            )
        return snapshot

    async def list_for_run(self, run_id: UUID) -> list[RunSnapshot]:
        return await self._store.list_for_run(run_id)
