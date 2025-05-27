from abc import abstractmethod
from typing import Any
from uuid import UUID

from ..entities.chunk import Chunk
from .base import BaseRepository


class ChunkRepository(BaseRepository[Chunk]):
    """Repository interface for Chunk entities."""

    @abstractmethod
    async def create_bulk(self, chunks: list[Chunk]) -> list[Chunk]:
        """Create multiple chunks in a single operation."""
        pass

    @abstractmethod
    async def get_by_document(self, document_id: UUID) -> list[Chunk]:
        """Get all chunks for a document."""
        pass

    @abstractmethod
    async def get_by_library(
        self,
        library_id: UUID,
        limit: int = 100,
        offset: int = 0
    ) -> list[Chunk]:
        """Get chunks by library ID."""
        pass

    @abstractmethod
    async def delete_by_document(self, document_id: UUID) -> int:
        """Delete all chunks for a document."""
        pass

    @abstractmethod
    async def search_by_metadata(
        self,
        library_id: UUID,
        metadata_filters: dict[str, Any],
        limit: int = 100
    ) -> list[Chunk]:
        """Search chunks by metadata filters."""
        pass
