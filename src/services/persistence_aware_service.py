"""Base class for services with persistence support."""
import uuid
from abc import ABC
from typing import Any

from src.core.logging import get_logger
from src.infrastructure.persistence.manager import get_persistence_manager
from src.infrastructure.persistence.wal.interface import OperationType
from src.infrastructure.repositories.persistent_library_repository import (
    PersistentLibraryRepository,
)

logger = get_logger(__name__)


class PersistenceAwareService(ABC):
    """Base class for services that need persistence."""

    def __init__(self):
        self._persistence = get_persistence_manager()

    async def log_create(
        self,
        resource_type: str,
        resource_id: uuid.UUID,
        data: dict[str, Any]
    ) -> int:
        """Log a create operation."""
        operation_type = getattr(OperationType, f"CREATE_{resource_type.upper()}")
        return await self._persistence.log_operation(
            operation_type,
            resource_id,
            data
        )

    async def log_update(
        self,
        resource_type: str,
        resource_id: uuid.UUID,
        data: dict[str, Any]
    ) -> int:
        """Log an update operation."""
        operation_type = getattr(OperationType, f"UPDATE_{resource_type.upper()}")
        return await self._persistence.log_operation(
            operation_type,
            resource_id,
            data
        )

    async def log_delete(
        self,
        resource_type: str,
        resource_id: uuid.UUID
    ) -> int:
        """Log a delete operation."""
        operation_type = getattr(OperationType, f"DELETE_{resource_type.upper()}")
        return await self._persistence.log_operation(
            operation_type,
            resource_id,
            {'deleted': True}
        )




class PersistentServiceFactory:
    """Factory for creating services with persistence."""

    _library_repository = None

    @classmethod
    def get_library_repository(cls) -> PersistentLibraryRepository:
        """Get persistent library repository."""
        if cls._library_repository is None:
            cls._library_repository = PersistentLibraryRepository()
        return cls._library_repository

    @classmethod
    async def initialize(cls):
        """Initialize all services and recover state."""
        from src.infrastructure.persistence.recovery import get_recovery_service

        # Initialize persistence manager
        persistence = get_persistence_manager()
        await persistence.initialize()

        # Create repositories
        library_repo = cls.get_library_repository()

        # Setup recovery service
        recovery = get_recovery_service()
        recovery.library_repository = library_repo
        recovery.repositories = [('libraries', library_repo)]

        # Recover state
        await recovery.recover_system()

    @classmethod
    async def shutdown(cls):
        """Shutdown services and persist state."""
        from src.infrastructure.persistence.recovery import get_recovery_service

        # Create final backup
        recovery = get_recovery_service()
        await recovery.create_backup("Shutdown backup")

        # Shutdown persistence
        persistence = get_persistence_manager()
        await persistence.shutdown()
