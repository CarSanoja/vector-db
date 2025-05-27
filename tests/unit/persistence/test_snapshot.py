"""Tests for Snapshot Manager."""
import tempfile
from pathlib import Path

import pytest

from src.infrastructure.persistence.snapshot.file_snapshot import FileSnapshotManager


@pytest.mark.asyncio
async def test_snapshot_create_and_load():
   """Test snapshot creation and loading."""
   with tempfile.TemporaryDirectory() as tmpdir:
       snapshot_mgr = FileSnapshotManager(Path(tmpdir))

       state = {
           "libraries": {
               "lib1": {"name": "Library 1", "dimension": 128},
               "lib2": {"name": "Library 2", "dimension": 256}
           },
           "metadata": {"version": "1.0", "count": 2}
       }

       metadata = await snapshot_mgr.create_snapshot(
           sequence_number=100,
           state=state,
           description="Test snapshot"
       )

       assert metadata.sequence_number == 100
       assert metadata.description == "Test snapshot"
       assert metadata.size_bytes > 0

       loaded_state = await snapshot_mgr.load_snapshot(metadata.snapshot_id)
       assert loaded_state == state


@pytest.mark.asyncio
async def test_snapshot_list_and_cleanup():
   """Test snapshot listing and cleanup."""
   with tempfile.TemporaryDirectory() as tmpdir:
       snapshot_mgr = FileSnapshotManager(Path(tmpdir))

       for i in range(8):
           await snapshot_mgr.create_snapshot(
               sequence_number=i * 100,
               state={"index": i},
               description=f"Snapshot {i}"
           )

       snapshots = await snapshot_mgr.list_snapshots()
       assert len(snapshots) == 8
       # Should be sorted newest first
       assert snapshots[0].sequence_number == 700
       # Cleanup old snapshots
       deleted = await snapshot_mgr.cleanup_old_snapshots(keep_count=3)
       assert deleted == 5
       # Verify remaining
       remaining = await snapshot_mgr.list_snapshots()
       assert len(remaining) == 3
       assert all(s.sequence_number >= 500 for s in remaining)


@pytest.mark.asyncio
async def test_snapshot_compression():
   """Test snapshot compression."""
   with tempfile.TemporaryDirectory() as tmpdir:
       compressed_mgr = FileSnapshotManager(Path(tmpdir) / "compressed", use_compression=True)
       uncompressed_mgr = FileSnapshotManager(Path(tmpdir) / "uncompressed", use_compression=False)

       large_state = {
           "data": ["x" * 1000 for _ in range(100)]
       }
       compressed_meta = await compressed_mgr.create_snapshot(1, large_state)
       uncompressed_meta = await uncompressed_mgr.create_snapshot(1, large_state)

       assert compressed_meta.size_bytes < uncompressed_meta.size_bytes * 0.5

       assert await compressed_mgr.load_snapshot(compressed_meta.snapshot_id) == large_state
       assert await uncompressed_mgr.load_snapshot(uncompressed_meta.snapshot_id) == large_state
