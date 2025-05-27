from abc import abstractmethod
from typing import Optional, list
from uuid import UUID

from ..entities.library import Library
from .base import BaseRepository


class LibraryRepository(BaseRepository[Library]):
    """Repository interface for Library entities."""

    @abstractmethod
    async def get_by_name(self, name: str) -> Optional[Library]:
        """Get a library by name."""
        pass

    @abstractmethod
    async def list_by_index_type(self, index_type: str) -> list[Library]:
        """list libraries by index type."""
        pass

    @abstractmethod
    async def update_stats(
        self,
        id: UUID,
        total_documents: Optional[int] = None,
        total_chunks: Optional[int] = None
    ) -> Optional[Library]:
        """Update library statistics."""
        pass
