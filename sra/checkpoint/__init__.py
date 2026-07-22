"""Checkpoint Manager: persists a full RunSnapshot on every state transition
and restores it for crash-safe, automatic resume.
"""

from sra.checkpoint.manager import SqliteCheckpointManager

__all__ = ["SqliteCheckpointManager"]
