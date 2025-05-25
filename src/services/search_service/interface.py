from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from uuid import UUID

from src.domain.value_objects.search import SearchQuery, SearchResult


class ISearchService(ABC):
    """Interface for search service."""
    
    @abstractmethod
    async def search(
        self,
        library_id: UUID,
        embedding: List[float],
        k: int = 10,
        metadata_filters: Optional[Dict[str, Any]] = None
    ) -> List[SearchResult]:
        """Search for similar chunks in a library."""
        pass
    
    @abstractmethod
    async def search_by_content(
        self,
        library_id: UUID,
        content: str,
        k: int = 10,
        metadata_filters: Optional[Dict[str, Any]] = None
    ) -> List[SearchResult]:
        """Search using content (requires embedding generation)."""
        pass
    
    @abstractmethod
    async def multi_library_search(
        self,
        library_ids: List[UUID],
        embedding: List[float],
        k: int = 10,
        metadata_filters: Optional[Dict[str, Any]] = None
    ) -> Dict[UUID, List[SearchResult]]:
        """Search across multiple libraries."""
        pass