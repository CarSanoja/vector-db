from copy import deepcopy
from typing import Any, Generic, Optional, TypeVar, dict, list, type
from uuid import UUID

from pydantic import BaseModel

from src.core.logging import get_logger
from src.domain.repositories.base import BaseRepository
from src.infrastructure.locks import ReadWriteLock

T = TypeVar("T", bound=BaseModel)
logger = get_logger(__name__)


class InMemoryBaseRepository(BaseRepository[T], Generic[T]):
    """Base in-memory repository with thread-safe operations."""

    def __init__(self, entity_type: type[T]):
        self._entity_type = entity_type
        self._storage: dict[UUID, T] = {}
        self._lock = ReadWriteLock()
        logger.info(f"Initialized in-memory repository for {entity_type.__name__}")

    async def create(self, entity: T) -> T:
        """Create a new entity with thread safety."""
        async with self._lock.write():
            if hasattr(entity, 'id') and entity.id in self._storage:
                raise ValueError(f"Entity with id {entity.id} already exists")

            # Create a deep copy to ensure immutability
            stored_entity = deepcopy(entity)
            self._storage[stored_entity.id] = stored_entity

            logger.info(
                f"Created {self._entity_type.__name__}",
                entity_id=str(stored_entity.id)
            )
            return deepcopy(stored_entity)

    async def get(self, id: UUID) -> Optional[T]:
        """Get an entity by ID with read lock."""
        async with self._lock.read():
            entity = self._storage.get(id)
            if entity:
                return deepcopy(entity)
            return None

    async def update(self, id: UUID, entity: T) -> Optional[T]:
        """Update an entity with write lock."""
        async with self._lock.write():
            if id not in self._storage:
                return None

            # Ensure the ID matches
            if hasattr(entity, 'id'):
                entity.id = id

            self._storage[id] = deepcopy(entity)
            logger.info(
                f"Updated {self._entity_type.__name__}",
                entity_id=str(id)
            )
            return deepcopy(entity)

    async def delete(self, id: UUID) -> bool:
        """Delete an entity with write lock."""
        async with self._lock.write():
            if id in self._storage:
                del self._storage[id]
                logger.info(
                    f"Deleted {self._entity_type.__name__}",
                    entity_id=str(id)
                )
                return True
            return False

    async def list(
        self,
        filters: Optional[dict[str, Any]] = None,
        limit: int = 100,
        offset: int = 0
    ) -> list[T]:
        """list entities with optional filtering."""
        async with self._lock.read():
            entities = list(self._storage.values())

            # Apply filters
            if filters:
                entities = self._apply_filters(entities, filters)

            # Apply pagination
            start = offset
            end = offset + limit
            result = entities[start:end]

            # Return deep copies
            return [deepcopy(entity) for entity in result]

    async def count(self, filters: Optional[dict[str, Any]] = None) -> int:
        """Count entities with optional filtering."""
        async with self._lock.read():
            entities = list(self._storage.values())

            if filters:
                entities = self._apply_filters(entities, filters)

            return len(entities)

    def _apply_filters(self, entities: list[T], filters: dict[str, Any]) -> list[T]:
        """Apply filters to entity list."""
        filtered = []
        for entity in entities:
            match = True
            for field, value in filters.items():
                if hasattr(entity, field):
                    entity_value = getattr(entity, field)
                    if entity_value != value:
                        match = False
                        break
                else:
                    match = False
                    break
            if match:
                filtered.append(entity)
        return filtered

