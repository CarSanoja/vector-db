"""Service interfaces."""
from abc import ABC, abstractmethod
from typing import Any, Optional
from uuid import UUID

from src.domain.entities.chunk import Chunk
from src.domain.entities.library import IndexType, Library
from src.domain.value_objects import SearchResult


class ILibraryService(ABC):
    """Library service interface."""

    @abstractmethod
    async def create_library(
        self,
        name: str,
        dimension: int,
        index_type: IndexType,
        description: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None
    ) -> Library:
        """Create a new library."""
        pass

    @abstractmethod
    async def get_library(self, library_id: UUID) -> Optional[Library]:
        """Get library by ID."""
        pass

    @abstractmethod
    async def list_libraries(
        self,
        index_type: Optional[IndexType] = None,
        limit: int = 100,
        offset: int = 0
    ) -> list[Library]:
        """list libraries."""
        pass

    @abstractmethod
    async def update_library(
        self,
        library_id: UUID,
        name: Optional[str] = None,
        description: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None
    ) -> Optional[Library]:
        """Update library."""
        pass

    @abstractmethod
    async def delete_library(self, library_id: UUID) -> bool:
        """Delete library."""
        pass


class IChunkService(ABC):
    """Chunk service interface."""

    @abstractmethod
    async def create_chunk(
        self,
        library_id: UUID,
        content: str,
        embedding: list[float],
        document_id: Optional[UUID] = None,
        metadata: Optional[dict[str, Any]] = None
    ) -> Chunk:
        """Create a chunk."""
        pass

    @abstractmethod
    async def create_chunks_bulk(
        self,
        library_id: UUID,
        chunks_data: list[dict[str, Any]]
    ) -> list[Chunk]:
        """Create multiple chunks."""
        pass

    @abstractmethod
    async def get_chunk(self, chunk_id: UUID) -> Optional[Chunk]:
        """Get chunk by ID."""
        pass

    @abstractmethod
    async def list_chunks(
        self,
        library_id: UUID,
        limit: int = 100,
        offset: int = 0
    ) -> list[Chunk]:
        """list chunks in library."""
        pass

    @abstractmethod
    async def update_chunk(
        self,
        chunk_id: UUID,
        content: Optional[str] = None,
        embedding: Optional[list[float]] = None,
        metadata: Optional[dict[str, Any]] = None
    ) -> Optional[Chunk]:
        """Update chunk."""
        pass

    @abstractmethod
    async def delete_chunk(self, chunk_id: UUID) -> bool:
        """Delete chunk."""
        pass


class ISearchService(ABC):
    """Search service interface."""

    @abstractmethod
    async def search(
        self,
        library_id: UUID,
        embedding: list[float],
        k: int = 10,
        metadata_filters: Optional[dict[str, Any]] = None
    ) -> list[SearchResult]:
        """Search for similar chunks."""
        pass

    @abstractmethod
    async def multi_library_search(
        self,
        library_ids: list[UUID],
        embedding: list[float],
        k: int = 10,
        metadata_filters: Optional[dict[str, Any]] = None
    ) -> dict[UUID, list[SearchResult]]:
        """Search across multiple libraries."""
        pass
