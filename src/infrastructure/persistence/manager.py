"""Persistence manager that coordinates WAL and snapshots."""
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from pathlib import Path
import uuid

from src.infrastructure.persistence.wal.interface import IWriteAheadLog, OperationType
from src.infrastructure.persistence.wal.file_wal import FileWAL
from src.infrastructure.persistence.snapshot.interface import ISnapshotManager
from src.infrastructure.persistence.snapshot.file_snapshot import FileSnapshotManager
from src.infrastructure.persistence.serialization.serializers import StateSerializer
from src.core.logging import get_logger
from src.core.config import settings

logger = get_logger(__name__)


class PersistenceManager:
    """Manages persistence operations including WAL and snapshots."""
    
    def __init__(
        self,
        wal: Optional[IWriteAheadLog] = None,
        snapshot_manager: Optional[ISnapshotManager] = None,
        auto_checkpoint_interval: int = 1000,
        auto_snapshot_interval: timedelta = timedelta(hours=1)
    ):
        """Initialize persistence manager.
        
        Args:
            wal: Write-ahead log instance
            snapshot_manager: Snapshot manager instance
            auto_checkpoint_interval: Operations between checkpoints
            auto_snapshot_interval: Time between snapshots
        """
        self.wal = wal or FileWAL(settings.wal_directory)
        self.snapshot_manager = snapshot_manager or FileSnapshotManager(
            settings.snapshot_directory
        )
        
        self.auto_checkpoint_interval = auto_checkpoint_interval
        self.auto_snapshot_interval = auto_snapshot_interval
        
        self.operations_since_checkpoint = 0
        self.last_snapshot_time = datetime.utcnow()
        self.is_recovering = False
        
        # Background tasks
        self._checkpoint_task: Optional[asyncio.Task] = None
        self._snapshot_task: Optional[asyncio.Task] = None
    
    async def initialize(self) -> None:
        """Initialize persistence manager and recover state."""
        logger.info("Initializing persistence manager")
        
        # Initialize WAL
        if hasattr(self.wal, 'initialize'):
            await self.wal.initialize()
        
        # Start background tasks
        self._checkpoint_task = asyncio.create_task(self._auto_checkpoint_loop())
        self._snapshot_task = asyncio.create_task(self._auto_snapshot_loop())
        
        logger.info("Persistence manager initialized")
    
    async def shutdown(self) -> None:
        """Shutdown persistence manager."""
        logger.info("Shutting down persistence manager")
        
        # Cancel background tasks
        if self._checkpoint_task:
            self._checkpoint_task.cancel()
        if self._snapshot_task:
            self._snapshot_task.cancel()
        
        # Final checkpoint
        await self.create_checkpoint()
        
        # Close WAL
        await self.wal.close()
        
        logger.info("Persistence manager shutdown complete")
    
    async def log_operation(
        self,
        operation_type: OperationType,
        resource_id: uuid.UUID,
        data: dict
    ) -> int:
        """Log an operation to WAL."""
        if self.is_recovering:
            return -1
        
        sequence = await self.wal.append(operation_type, resource_id, data)
        self.operations_since_checkpoint += 1
        
        # Check if we need to checkpoint
        if self.operations_since_checkpoint >= self.auto_checkpoint_interval:
            asyncio.create_task(self.create_checkpoint())
        
        return sequence
    
    async def create_checkpoint(self) -> int:
        """Create a WAL checkpoint."""
        sequence = await self.wal.checkpoint()
        self.operations_since_checkpoint = 0
        
        logger.info(f"Checkpoint created at sequence {sequence}")
        return sequence
    
    async def create_snapshot(
        self,
        state: Dict[str, Any],
        description: Optional[str] = None
    ) -> str:
        """Create a snapshot of current state."""
        # Get current WAL sequence
        current_sequence = await self.create_checkpoint()
        
        # Serialize state
        serialized_state = StateSerializer.serialize_state(state)
        
        # Create snapshot
        metadata = await self.snapshot_manager.create_snapshot(
            sequence_number=current_sequence,
            state={'serialized': serialized_state},
            description=description
        )
        
        self.last_snapshot_time = datetime.utcnow()
        
        # Cleanup old snapshots
        await self.snapshot_manager.cleanup_old_snapshots()
        
        # Truncate WAL up to snapshot
        await self.wal.truncate(current_sequence)
        
        return metadata.snapshot_id
    
    async def recover_state(self) -> Dict[str, Any]:
        """Recover state from snapshot and WAL."""
        self.is_recovering = True
        logger.info("Starting state recovery")
        
        try:
            # Load latest snapshot
            latest_snapshot = await self.snapshot_manager.get_latest_snapshot()
            
            if latest_snapshot:
                logger.info(
                    f"Loading snapshot {latest_snapshot.snapshot_id} "
                    f"at sequence {latest_snapshot.sequence_number}"
                )
                
                snapshot_data = await self.snapshot_manager.load_snapshot(
                    latest_snapshot.snapshot_id
                )
                
                # Deserialize state
                state = StateSerializer.deserialize_state(
                    snapshot_data['serialized']
                )
                
                # Replay WAL from snapshot
                replay_from = latest_snapshot.sequence_number + 1
            else:
                logger.info("No snapshot found, replaying entire WAL")
                state = {}
                replay_from = 0
            
            # Replay WAL entries
            entries = await self.wal.read(replay_from)
            logger.info(f"Replaying {len(entries)} WAL entries")
            
            for entry in entries:
                # Apply operation to state
                await self._apply_wal_entry(state, entry)
            
            logger.info("State recovery complete")
            return state
            
        finally:
            self.is_recovering = False
    
    async def _apply_wal_entry(self, state: Dict[str, Any], entry) -> None:
        """Apply a WAL entry to the state."""
        # This would be implemented based on your specific operations
        # For now, we'll just store the operations
        if 'operations' not in state:
            state['operations'] = []
        
        state['operations'].append({
            'sequence': entry.sequence_number,
            'type': entry.operation_type.value,
            'resource_id': str(entry.resource_id),
            'data': entry.data,
            'timestamp': entry.timestamp.isoformat()
        })
    
    async def _auto_checkpoint_loop(self) -> None:
        """Background task for automatic checkpoints."""
        while True:
            try:
                await asyncio.sleep(60)  # Check every minute
                
                if self.operations_since_checkpoint > 0:
                    await self.create_checkpoint()
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in checkpoint loop: {e}")
    
    async def _auto_snapshot_loop(self) -> None:
        """Background task for automatic snapshots."""
        while True:
            try:
                await asyncio.sleep(300)  # Check every 5 minutes
                
                time_since_snapshot = datetime.utcnow() - self.last_snapshot_time
                if time_since_snapshot >= self.auto_snapshot_interval:
                    # This would need access to current state
                    # In real implementation, this would be passed in
                    logger.info("Auto-snapshot triggered (implementation needed)")
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in snapshot loop: {e}")


# Singleton instance
_persistence_manager: Optional[PersistenceManager] = None


def get_persistence_manager() -> PersistenceManager:
    """Get or create persistence manager instance."""
    global _persistence_manager
    
    if _persistence_manager is None:
        _persistence_manager = PersistenceManager()
    
    return _persistence_manager
