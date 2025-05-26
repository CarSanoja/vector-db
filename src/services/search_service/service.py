from typing import List, Optional, Dict, Any
from uuid import UUID
import numpy as np
import asyncio

from src.domain.value_objects.search import SearchQuery, SearchResult
from src.domain.repositories.chunk import ChunkRepository
from src.services.library_service import ILibraryService
from src.core.exceptions import NotFoundError, ValidationError
from src.core.logging import get_logger
from .interface import ISearchService
from src.infrastructure.locks import ReadWriteLock

logger = get_logger(__name__)


class SearchService(ISearchService):
    """Service for vector similarity search."""
    
    def __init__(
        self,
        chunk_repository: ChunkRepository,
        library_service: ILibraryService
    ):
        self.chunk_repository = chunk_repository
        self.library_service = library_service
        self._search_cache: Dict[str, List[SearchResult]] = {}
        logger.info("Initialized SearchService")
    
    async def search(
        self,
        library_id: UUID,
        embedding: List[float],
        k: int = 10,
        metadata_filters: Optional[Dict[str, Any]] = None
    ) -> List[SearchResult]:
        """Search for similar chunks in a library."""
        # Validate library
        library = await self.library_service.get_library(library_id)
        if not library:
            raise NotFoundError("Library", str(library_id))
        
        # Validate embedding dimension
        if len(embedding) != library.dimension:
            raise ValidationError(
                f"Embedding dimension {len(embedding)} != library dimension {library.dimension}",
                field="embedding"
            )
        
        # Get vector index
        index = self.library_service.get_index(library_id)
        if not index:
            raise ValidationError("Library index not available")
        
        # Create search query
        query = SearchQuery(
            embedding=embedding,
            k=k,
            library_id=library_id,
            metadata_filters=metadata_filters
        )
        
        # Check cache
        cache_key = self._get_cache_key(query)
        async with self._cache_lock.read():
            if cache_key in self._search_cache:
                logger.debug("Returning cached search results")
                return self._search_cache[cache_key]
        
        # Perform vector search
        query_vector = np.array(embedding, dtype=np.float32)
        
        # Get candidate IDs from vector search
        if metadata_filters:
            # Get chunks matching metadata filters
            filtered_chunks = await self.chunk_repository.search_by_metadata(
                library_id,
                metadata_filters,
                limit=k * 10  # Get more candidates for filtering
            )
            filter_ids = [chunk.id for chunk in filtered_chunks]
            
            # Search with filter
            vector_results = await index.search(query_vector, k=k, filter_ids=filter_ids)
        else:
            # Search without filter
            vector_results = await index.search(query_vector, k=k)
        
        # Convert to search results
        results = []
        for chunk_id, distance in vector_results:
            chunk = await self.chunk_repository.get(chunk_id)
            if chunk:
                result = SearchResult(
                    chunk_id=chunk_id,
                    content=chunk.content,
                    distance=distance,
                    score=1.0 / (1.0 + distance),  # Convert distance to similarity score
                    metadata=chunk.metadata
                )
                results.append(result)
        
        # Cache results
        async with self._cache_lock.write():
            self._search_cache[cache_key] = results
        
        logger.info(
            f"Search completed",
            library_id=str(library_id),
            results_count=len(results),
            k=k
        )
        
        return results
    
    async def search_by_content(
        self,
        library_id: UUID,
        content: str,
        k: int = 10,
        metadata_filters: Optional[Dict[str, Any]] = None
    ) -> List[SearchResult]:
        """Search using content (requires embedding generation)."""
        # This would require an embedding model to convert content to vector
        # For now, raise not implemented
        raise NotImplementedError(
            "Content-based search requires embedding generation service"
        )
    
    async def multi_library_search(
        self,
        library_ids: List[UUID],
        embedding: List[float],
        k: int = 10,
        metadata_filters: Optional[Dict[str, Any]] = None
    ) -> Dict[UUID, List[SearchResult]]:
        """Search across multiple libraries."""
        # Validate all libraries exist and have same dimension
        libraries = []
        for lib_id in library_ids:
            library = await self.library_service.get_library(lib_id)
            if not library:
                raise NotFoundError("Library", str(lib_id))
            libraries.append(library)
        
        # Check dimensions match
        dimensions = set(lib.dimension for lib in libraries)
        if len(dimensions) > 1:
            raise ValidationError(
                f"Libraries have different dimensions: {dimensions}"
            )
        
        dimension = libraries[0].dimension
        if len(embedding) != dimension:
            raise ValidationError(
                f"Embedding dimension {len(embedding)} != library dimension {dimension}",
                field="embedding"
            )
        
        # Search each library concurrently
        search_tasks = []
        for library_id in library_ids:
            task = self.search(library_id, embedding, k, metadata_filters)
            search_tasks.append(task)
        
        results = await asyncio.gather(*search_tasks, return_exceptions=True)
        
        # Combine results
        search_results = {}
        for library_id, result in zip(library_ids, results):
            if isinstance(result, Exception):
                logger.error(
                    f"Search failed for library {library_id}",
                    error=str(result)
                )
                search_results[library_id] = []
            else:
                search_results[library_id] = result
        
        logger.info(
            f"Multi-library search completed",
            library_count=len(library_ids),
            total_results=sum(len(r) for r in search_results.values())
        )
        
        return search_results
    
    def _get_cache_key(self, query: SearchQuery) -> str:
        """Generate cache key for search query."""
        # Simple cache key based on library, k, and embedding hash
        embedding_hash = hash(tuple(query.embedding[:10]))  # Use first 10 values
        filters_hash = hash(str(sorted(query.metadata_filters.items()))) if query.metadata_filters else 0
        return f"{query.library_id}:{query.k}:{embedding_hash}:{filters_hash}"
    
    async def clear_cache(self) -> None:
        """Clear the search cache."""
        async with self._cache_lock.write():
            self._search_cache.clear()
            logger.info("Cleared search cache")
