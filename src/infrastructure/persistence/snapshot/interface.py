"""Snapshot interface for state persistence."""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional, dict, list


@dataclass
class SnapshotMetadata:
    """Metadata for a snapshot."""
    snapshot_id: str
    sequence_number: int
    timestamp: datetime
    size_bytes: int
    checksum: str
    description: Optional[str] = None


class ISnapshotManager(ABC):
    """Interface for snapshot management."""

    @abstractmethod
    async def create_snapshot(
        self,
        sequence_number: int,
        state: dict[str, Any],
        description: Optional[str] = None
    ) -> SnapshotMetadata:
        """Create a new snapshot of the current state."""
        pass

    @abstractmethod
    async def load_snapshot(self, snapshot_id: str) -> dict[str, Any]:
        """Load a snapshot by ID."""
        pass

    @abstractmethod
    async def list_snapshots(self) -> list[SnapshotMetadata]:
        """list all available snapshots."""
        pass

    @abstractmethod
    async def delete_snapshot(self, snapshot_id: str) -> bool:
        """Delete a snapshot."""
        pass

    @abstractmethod
    async def get_latest_snapshot(self) -> Optional[SnapshotMetadata]:
        """Get the most recent snapshot."""
        pass

    @abstractmethod
    async def cleanup_old_snapshots(self, keep_count: int = 5) -> int:
        """Remove old snapshots, keeping the most recent ones."""
        pass
