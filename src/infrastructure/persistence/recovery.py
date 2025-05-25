"""Recovery service for system state restoration."""
from typing import Dict, Any, Optional
from datetime import datetime
import asyncio

from src.infrastructure.persistence.manager import PersistenceManager
from src.infrastructure.repositories.persistent_library_repository import PersistentLibraryRepository
from src.core.logging import get_logger

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
    
    async def recover_system(self) -> Dict[str, Any]:
        """Recover complete system state."""
        start_time = datetime.utcnow()
        logger.info("Starting system recovery")
        
        try:
            # Recover state from persistence
            state = await self.persistence_manager.recover_state()
            
            # Restore repositories
            recovery_stats = {}
            
            for repo_name, repository in self.repositories:
                if repo_name in state:
                    logger.info(f"Restoring {repo_name} repository")
                    await repository.restore_state(state[repo_name])
                    
                    if hasattr(repository, 'count'):
                        count = await repository.count()
                        recovery_stats[f"{repo_name}_count"] = count
            
            # Calculate recovery time
            recovery_time = (datetime.utcnow() - start_time).total_seconds()
            
            recovery_stats.update({
                'recovery_time_seconds': recovery_time,
                'recovered_from_snapshot': 'snapshot_id' in state,
                'wal_entries_replayed': state.get('operations', [])
            })
            
            logger.info(
                f"System recovery complete",
                recovery_time=recovery_time,
                stats=recovery_stats
            )
            
            return recovery_stats
            
        except Exception as e:
            logger.error(f"Recovery failed: {e}")
            raise
    
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
    
    async def verify_consistency(self) -> Dict[str, Any]:
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
            f"Consistency check complete",
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
