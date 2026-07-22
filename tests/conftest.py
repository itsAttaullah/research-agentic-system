"""Shared pytest fixtures for unit and integration tests."""

from __future__ import annotations

from pathlib import Path

import pytest
from sra.storage import SqliteControlPlane


@pytest.fixture
async def control_plane(tmp_path: Path) -> SqliteControlPlane:
    db = SqliteControlPlane(tmp_path / "control.sqlite3")
    await db.connect()
    yield db
    await db.close()
