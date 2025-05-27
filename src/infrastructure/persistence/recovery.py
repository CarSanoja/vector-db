"""Recovery service for system state restoration with proper WAL replay."""
import uuid
from datetime import datetime
from typing import Any, Optional

from src.core.logging import get_logger
from src.domain.entities.library import Library
from src.infrastructure.persistence.manager import PersistenceManager
from src.infrastructure.repositories.persistent_library_repository import (
    PersistentLibraryRepository,
)

logger = get_logger(__name__)


class RecoveryService:
    """Service for recovering system state from persistence."""

    def __init__(
        self,
        persistence_manager: PersistenceManager,
        library_repository: Optional[PersistentLibraryRepository] = None
    ):
        """Initialize recovery service.
        Args:
            persistence_manager: Persistence manager instance
            library_repository: Library repository to restore
        """
        self.persistence_manager = persistence_manager
        self.library_repository = library_repository

        # Add other repositories as needed
        self.repositories = []
        if library_repository:
            self.repositories.append(('libraries', library_repository))

    async def recover_system(self) -> dict[str, Any]:
        """Recover complete system state."""
        start_time = datetime.utcnow()
        logger.info("Starting system recovery")

        try:
            # Recover state from persistence
            state = await self.persistence_manager.recover_state()

            # First restore from snapshot
            recovery_stats = {}

            for repo_name, repository in self.repositories:
                if repo_name in state:
                    logger.info(f"Restoring {repo_name} repository from snapshot")
                    await repository.restore_state(state[repo_name])

                    if hasattr(repository, 'count'):
                        count = await repository.count()
                        recovery_stats[f"{repo_name}_count"] = count

            # Then replay WAL operations to apply changes after snapshot
            if 'operations' in state and state['operations']:
                logger.info(f"Replaying {len(state['operations'])} WAL operations")

                for operation in state['operations']:
                    await self._replay_operation(operation)

            # Get final counts after WAL replay
            for repo_name, repository in self.repositories:
                if hasattr(repository, 'count'):
                    count = await repository.count()
                    recovery_stats[f"{repo_name}_count_after_wal"] = count

            # Calculate recovery time
            recovery_time = (datetime.utcnow() - start_time).total_seconds()

            recovery_stats.update({
                'recovery_time_seconds': recovery_time,
                'recovered_from_snapshot': bool([k for k in state.keys() if k != 'operations']),
                'wal_entries_replayed': len(state.get('operations', []))
            })

            logger.info(
                "System recovery complete",
                recovery_time=recovery_time,
                stats=recovery_stats
            )

            return recovery_stats

        except Exception as e:
            logger.error(f"Recovery failed: {e}")
            raise

    async def _replay_operation(self, operation: dict[str, Any]) -> None:
        """Replay a single WAL operation."""
        op_type = operation['type']
        resource_id = uuid.UUID(operation['resource_id'])
        data = operation['data']

        # Handle encoded entity format from MessagePackSerializer
        if isinstance(data, dict) and '__entity__' in data:
            # Extract the actual data from the encoded format
            actual_data = data.get('data', {})
        else:
            actual_data = data

        if op_type == 'CREATE_LIBRARY' and self.library_repository:
            # Ensure ID is set
            if 'id' not in actual_data:
                actual_data['id'] = str(resource_id)

            # Check if library already exists (from snapshot)
            existing = await self.library_repository.get(resource_id)
            if not existing:
                library = Library(**actual_data)
                # Directly add to repository without logging again
                async with self.library_repository._lock:
                    self.library_repository._libraries[library.id] = library
                    self.library_repository._name_index[library.name] = library.id
                logger.debug(f"Replayed CREATE_LIBRARY for {resource_id}")

        elif op_type == 'UPDATE_LIBRARY' and self.library_repository:
            # Apply update to existing library
            library = await self.library_repository.get(resource_id)
            if library:
                # Update library fields from data
                for key, value in actual_data.items():
                    if hasattr(library, key):
                        setattr(library, key, value)
                logger.debug(f"Replayed UPDATE_LIBRARY for {resource_id}")

        elif op_type == 'DELETE_LIBRARY' and self.library_repository:
            # Remove library
            async with self.library_repository._lock:
                if resource_id in self.library_repository._libraries:
                    library = self.library_repository._libraries[resource_id]
                    del self.library_repository._libraries[resource_id]
                    if library.name in self.library_repository._name_index:
                        del self.library_repository._name_index[library.name]
                logger.debug(f"Replayed DELETE_LIBRARY for {resource_id}")

    async def create_backup(self, description: Optional[str] = None) -> str:
        """Create a system backup."""
        logger.info("Creating system backup")

        # Collect state from all repositories
        state = {}

        for repo_name, repository in self.repositories:
            if hasattr(repository, 'get_state'):
                state[repo_name] = await repository.get_state()

        # Create snapshot
        snapshot_id = await self.persistence_manager.create_snapshot(
            state=state,
            description=description or f"Manual backup at {datetime.utcnow()}"
        )

        logger.info(f"Backup created: {snapshot_id}")
        return snapshot_id

    async def verify_consistency(self) -> dict[str, Any]:
        """Verify system consistency."""
        logger.info("Verifying system consistency")

        issues = []
        stats = {}

        # Check each repository
        for repo_name, repository in self.repositories:
            if hasattr(repository, 'verify_consistency'):
                repo_issues = await repository.verify_consistency()
                if repo_issues:
                    issues.extend(repo_issues)

            if hasattr(repository, 'count'):
                stats[f"{repo_name}_count"] = await repository.count()

        # Check WAL status
        wal_status = {
            'healthy': True,  # Would implement actual health check
            'current_sequence': -1  # Would get from WAL
        }

        result = {
            'consistent': len(issues) == 0,
            'issues': issues,
            'stats': stats,
            'wal_status': wal_status,
            'timestamp': datetime.utcnow().isoformat()
        }

        logger.info(
            "Consistency check complete",
            consistent=result['consistent'],
            issue_count=len(issues)
        )

        return result


# Global recovery service instance
_recovery_service: Optional[RecoveryService] = None


def get_recovery_service() -> RecoveryService:
    """Get or create recovery service instance."""
    global _recovery_service

    if _recovery_service is None:
        from src.infrastructure.persistence.manager import get_persistence_manager

        _recovery_service = RecoveryService(
            persistence_manager=get_persistence_manager()
        )

    return _recovery_service
