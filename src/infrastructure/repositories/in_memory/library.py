from copy import deepcopy
from datetime import datetime
from typing import Optional
from uuid import UUID

from src.domain.entities.library import Library
from src.domain.repositories.library import LibraryRepository

from .base import InMemoryBaseRepository


class InMemoryLibraryRepository(InMemoryBaseRepository[Library], LibraryRepository):
    """In-memory implementation of LibraryRepository."""

    def __init__(self):
        super().__init__(Library)

    async def get_by_name(self, name: str) -> Optional[Library]:
        """Get a library by name."""
        async with self._lock.read():
            for library in self._storage.values():
                if library.name == name:
                    return deepcopy(library)
            return None

    async def list_by_index_type(self, index_type: str) -> list[Library]:
        """list libraries by index type."""
        async with self._lock.read():
            libraries = [
                deepcopy(library)
                for library in self._storage.values()
                if library.index_type == index_type
            ]
            return libraries

    async def update_stats(
        self,
        id: UUID,
        total_documents: Optional[int] = None,
        total_chunks: Optional[int] = None
    ) -> Optional[Library]:
        """Update library statistics."""
        async with self._lock.write():
            library = self._storage.get(id)
            if not library:
                return None

            # Create a copy for modification
            updated_library = deepcopy(library)

            if total_documents is not None:
                updated_library.total_documents = total_documents
            if total_chunks is not None:
                updated_library.total_chunks = total_chunks

            # Trigger timestamp update
            updated_library.updated_at = datetime.utcnow()

            self._storage[id] = updated_library
            return deepcopy(updated_library)
