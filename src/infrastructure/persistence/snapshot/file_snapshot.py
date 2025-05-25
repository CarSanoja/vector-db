"""File-based snapshot implementation."""
import os
import json
import gzip
import hashlib
import shutil
from typing import Optional, List, Dict, Any
from datetime import datetime
from pathlib import Path
import uuid
import aiofiles
import msgpack
from asyncio import Lock

from .interface import ISnapshotManager, SnapshotMetadata
from src.core.logging import get_logger

logger = get_logger(__name__)


class FileSnapshotManager(ISnapshotManager):
    """File-based snapshot manager with compression."""
    
    def __init__(self, snapshot_directory: Path, use_compression: bool = True):
        """Initialize snapshot manager.
        
        Args:
            snapshot_directory: Directory to store snapshots
            use_compression: Whether to compress snapshots
        """
        self.snapshot_directory = Path(snapshot_directory)
        self.use_compression = use_compression
        self.write_lock = Lock()
        
        # Create directory if it doesn't exist
        self.snapshot_directory.mkdir(parents=True, exist_ok=True)
        
        # Metadata cache
        self._metadata_cache: Optional[List[SnapshotMetadata]] = None
    
    async def create_snapshot(
        self,
        sequence_number: int,
        state: Dict[str, Any],
        description: Optional[str] = None
    ) -> SnapshotMetadata:
        """Create a new snapshot."""
        async with self.write_lock:
            snapshot_id = f"snapshot_{sequence_number}_{uuid.uuid4().hex[:8]}"
            timestamp = datetime.utcnow()
            
            # Serialize state
            serialized = msgpack.packb(state, use_bin_type=True)
            
            # Compress if enabled
            if self.use_compression:
                serialized = gzip.compress(serialized, compresslevel=6)
                snapshot_file = self.snapshot_directory / f"{snapshot_id}.msgpack.gz"
            else:
                snapshot_file = self.snapshot_directory / f"{snapshot_id}.msgpack"
            
            # Calculate checksum
            checksum = hashlib.sha256(serialized).hexdigest()
            
            # Write snapshot
            async with aiofiles.open(snapshot_file, 'wb') as f:
                await f.write(serialized)
            
            # Create metadata
            metadata = SnapshotMetadata(
                snapshot_id=snapshot_id,
                sequence_number=sequence_number,
                timestamp=timestamp,
                size_bytes=len(serialized),
                checksum=checksum,
                description=description
            )
            
            # Write metadata
            metadata_file = self.snapshot_directory / f"{snapshot_id}.meta"
            async with aiofiles.open(metadata_file, 'w') as f:
                await f.write(json.dumps({
                    "snapshot_id": metadata.snapshot_id,
                    "sequence_number": metadata.sequence_number,
                    "timestamp": metadata.timestamp.isoformat(),
                    "size_bytes": metadata.size_bytes,
                    "checksum": metadata.checksum,
                    "description": metadata.description
                }, indent=2))
            
            # Invalidate cache
            self._metadata_cache = None
            
            logger.info(
                f"Snapshot created",
                snapshot_id=snapshot_id,
                sequence=sequence_number,
                size_mb=metadata.size_bytes / 1024 / 1024
            )
            
            return metadata
    
    async def load_snapshot(self, snapshot_id: str) -> Dict[str, Any]:
        """Load a snapshot by ID."""
        # Find snapshot file
        snapshot_file = None
        for ext in ['.msgpack.gz', '.msgpack']:
            candidate = self.snapshot_directory / f"{snapshot_id}{ext}"
            if candidate.exists():
                snapshot_file = candidate
                break
        
        if not snapshot_file:
            raise FileNotFoundError(f"Snapshot {snapshot_id} not found")
        
        # Read snapshot
        async with aiofiles.open(snapshot_file, 'rb') as f:
            data = await f.read()
        
        # Verify checksum
        metadata = await self._load_metadata(snapshot_id)
        actual_checksum = hashlib.sha256(data).hexdigest()
        if actual_checksum != metadata.checksum:
            raise ValueError(f"Snapshot checksum mismatch for {snapshot_id}")
        
        # Decompress if needed
        if snapshot_file.suffix == '.gz':
            data = gzip.decompress(data)
        
        # Deserialize
        state = msgpack.unpackb(data, raw=False)
        
        logger.info(f"Snapshot loaded", snapshot_id=snapshot_id)
        return state
    
    async def list_snapshots(self) -> List[SnapshotMetadata]:
        """List all available snapshots."""
        if self._metadata_cache is not None:
            return self._metadata_cache
        
        snapshots = []
        
        for meta_file in self.snapshot_directory.glob("*.meta"):
            try:
                metadata = await self._load_metadata(meta_file.stem)
                snapshots.append(metadata)
            except Exception as e:
                logger.error(f"Failed to load metadata for {meta_file}: {e}")
                continue
        
        # Sort by timestamp (newest first)
        snapshots.sort(key=lambda s: s.timestamp, reverse=True)
        
        self._metadata_cache = snapshots
        return snapshots
    
    async def delete_snapshot(self, snapshot_id: str) -> bool:
        """Delete a snapshot."""
        async with self.write_lock:
            deleted = False
            
            # Delete snapshot file
            for ext in ['.msgpack.gz', '.msgpack']:
                snapshot_file = self.snapshot_directory / f"{snapshot_id}{ext}"
                if snapshot_file.exists():
                    snapshot_file.unlink()
                    deleted = True
                    break
            
            # Delete metadata
            meta_file = self.snapshot_directory / f"{snapshot_id}.meta"
            if meta_file.exists():
                meta_file.unlink()
                deleted = True
            
            # Invalidate cache
            if deleted:
                self._metadata_cache = None
                logger.info(f"Snapshot deleted", snapshot_id=snapshot_id)
            
            return deleted
    
    async def get_latest_snapshot(self) -> Optional[SnapshotMetadata]:
        """Get the most recent snapshot."""
        snapshots = await self.list_snapshots()
        return snapshots[0] if snapshots else None
    
    async def cleanup_old_snapshots(self, keep_count: int = 5) -> int:
        """Remove old snapshots."""
        snapshots = await self.list_snapshots()
        
        if len(snapshots) <= keep_count:
            return 0
        
        # Delete old snapshots
        deleted_count = 0
        for snapshot in snapshots[keep_count:]:
            if await self.delete_snapshot(snapshot.snapshot_id):
                deleted_count += 1
        
        logger.info(f"Cleaned up {deleted_count} old snapshots")
        return deleted_count
    
    async def _load_metadata(self, snapshot_id: str) -> SnapshotMetadata:
        """Load metadata for a snapshot."""
        meta_file = self.snapshot_directory / f"{snapshot_id}.meta"
        
        if not meta_file.exists():
            raise FileNotFoundError(f"Metadata for snapshot {snapshot_id} not found")
        
        async with aiofiles.open(meta_file, 'r') as f:
            data = json.loads(await f.read())
        
        return SnapshotMetadata(
            snapshot_id=data["snapshot_id"],
            sequence_number=data["sequence_number"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            size_bytes=data["size_bytes"],
            checksum=data["checksum"],
            description=data.get("description")
        )
