from abc import ABC, abstractmethod
from typing import Any, Optional
from uuid import UUID

from src.domain.value_objects.search import SearchResult


class ISearchService(ABC):
    """Interface for search service."""

    @abstractmethod
    async def search(
        self,
        library_id: UUID,
        embedding: list[float],
        k: int = 10,
        metadata_filters: Optional[dict[str, Any]] = None
    ) -> list[SearchResult]:
        """Search for similar chunks in a library."""
        pass

    @abstractmethod
    async def search_by_content(
        self,
        library_id: UUID,
        content: str,
        k: int = 10,
        metadata_filters: Optional[dict[str, Any]] = None
    ) -> list[SearchResult]:
        """Search using content (requires embedding generation)."""
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
