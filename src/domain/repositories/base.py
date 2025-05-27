from abc import ABC, abstractmethod
from typing import Any, Generic, Optional, TypeVar, dict, list
from uuid import UUID

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class BaseRepository(ABC, Generic[T]):
    """Abstract base repository interface."""

    @abstractmethod
    async def create(self, entity: T) -> T:
        """Create a new entity."""
        pass

    @abstractmethod
    async def get(self, id: UUID) -> Optional[T]:
        """Get an entity by ID."""
        pass

    @abstractmethod
    async def update(self, id: UUID, entity: T) -> Optional[T]:
        """Update an existing entity."""
        pass

    @abstractmethod
    async def delete(self, id: UUID) -> bool:
        """Delete an entity by ID."""
        pass

    @abstractmethod
    async def list(
        self,
        filters: Optional[dict[str, Any]] = None,
        limit: int = 100,
        offset: int = 0
    ) -> list[T]:
        """list entities with optional filters."""
        pass

    @abstractmethod
    async def count(self, filters: Optional[dict[str, Any]] = None) -> int:
        """Count entities with optional filters."""
        pass
