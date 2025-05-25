"""Tests for Persistence Manager."""
import pytest
import tempfile
from pathlib import Path
from uuid import uuid4

from src.infrastructure.persistence.manager import PersistenceManager
from src.infrastructure.persistence.wal.file_wal import FileWAL
from src.infrastructure.persistence.snapshot.file_snapshot import FileSnapshotManager
from src.infrastructure.persistence.wal.interface import OperationType


@pytest.mark.asyncio
async def test_persistence_manager_operations():
   """Test persistence manager basic operations."""
   with tempfile.TemporaryDirectory() as tmpdir:
       tmppath = Path(tmpdir)
       
       # Create manager
       manager = PersistenceManager(
           wal=FileWAL(tmppath / "wal"),
           snapshot_manager=FileSnapshotManager(tmppath / "snapshots"),
           auto_checkpoint_interval=5
       )
       
       await manager.initialize()
       
       # Log operations
       resource_id = uuid4()
       seq1 = await manager.log_operation(
           OperationType.CREATE_LIBRARY,
           resource_id,
           {"name": "Test Library"}
       )
       assert seq1 > 0
       
       # Auto checkpoint should trigger after 5 operations
       for i in range(4):
           await manager.log_operation(
               OperationType.UPDATE_LIBRARY,
               resource_id,
               {"update": i}
           )
       
       # This should trigger auto checkpoint
       assert manager.operations_since_checkpoint == 0
       
       await manager.shutdown()


@pytest.mark.asyncio
async def test_persistence_manager_recovery():
   """Test persistence manager recovery."""
   with tempfile.TemporaryDirectory() as tmpdir:
       tmppath = Path(tmpdir)
       wal_dir = tmppath / "wal"
       snapshot_dir = tmppath / "snapshots"
       
       # First session - create state
       manager1 = PersistenceManager(
           wal=FileWAL(wal_dir),
           snapshot_manager=FileSnapshotManager(snapshot_dir)
       )
       await manager1.initialize()
       
       # Create some operations
       lib_id = uuid4()
       await manager1.log_operation(
           OperationType.CREATE_LIBRARY,
           lib_id,
           {"name": "Recovery Test"}
       )
       
       # Create snapshot
       state = {
           "libraries": {"test": {"id": str(lib_id), "name": "Recovery Test"}},
           "metadata": {"version": "1.0"}
       }
       snapshot_id = await manager1.create_snapshot(state, "Test snapshot")
       
       # Add more operations after snapshot
       await manager1.log_operation(
           OperationType.UPDATE_LIBRARY,
           lib_id,
           {"name": "Updated after snapshot"}
       )
       
       await manager1.shutdown()
       
       # Second session - recover
       manager2 = PersistenceManager(
           wal=FileWAL(wal_dir),
           snapshot_manager=FileSnapshotManager(snapshot_dir)
       )
       await manager2.initialize()
       
       recovered_state = await manager2.recover_state()
       
       # Should have snapshot data
       assert "libraries" in recovered_state
       
       # Should have WAL operations
       assert "operations" in recovered_state
       assert len(recovered_state["operations"]) >= 1
       
       await manager2.shutdown()


@pytest.mark.asyncio
async def test_persistence_manager_snapshot_cleanup():
   """Test snapshot cleanup after creation."""
   with tempfile.TemporaryDirectory() as tmpdir:
       tmppath = Path(tmpdir)
       
       manager = PersistenceManager(
           wal=FileWAL(tmppath / "wal"),
           snapshot_manager=FileSnapshotManager(tmppath / "snapshots")
       )
       await manager.initialize()
       
       # Create multiple snapshots
       for i in range(8):
           # Log some operations
           for j in range(10):
               await manager.log_operation(
                   OperationType.CREATE_CHUNK,
                   uuid4(),
                   {"index": i * 10 + j}
               )
           
           # Create snapshot
           await manager.create_snapshot(
               {"iteration": i},
               f"Snapshot {i}"
           )
       
       # Check that old snapshots were cleaned up
       snapshots = await manager.snapshot_manager.list_snapshots()
       assert len(snapshots) <= 5  # Default keep count
       
       await manager.shutdown()
