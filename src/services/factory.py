"""Factory for creating service instances with dependency injection."""
from typing import Optional

from src.domain.repositories.chunk import ChunkRepository
from src.domain.repositories.library import LibraryRepository
from src.infrastructure.repositories.in_memory import (
    InMemoryChunkRepository,
    InMemoryLibraryRepository,
)
from src.services.chunk_service import ChunkService, IChunkService
from src.services.library_service import ILibraryService, LibraryService
from src.services.search_service import ISearchService, SearchService


class ServiceFactory:
    """Factory for creating service instances."""

    _library_service: Optional[ILibraryService] = None
    _chunk_service: Optional[IChunkService] = None
    _search_service: Optional[ISearchService] = None

    @classmethod
    def get_library_service(
        cls,
        repository: Optional[LibraryRepository] = None
    ) -> ILibraryService:
        """Get or create library service instance."""
        if cls._library_service is None:
            repo = repository or InMemoryLibraryRepository()
            cls._library_service = LibraryService(repo)
        return cls._library_service

    @classmethod
    def get_chunk_service(
        cls,
        repository: Optional[ChunkRepository] = None,
        library_service: Optional[ILibraryService] = None
    ) -> IChunkService:
        """Get or create chunk service instance."""
        if cls._chunk_service is None:
            repo = repository or InMemoryChunkRepository()
            lib_service = library_service or cls.get_library_service()
            cls._chunk_service = ChunkService(repo, lib_service)
        return cls._chunk_service

    @classmethod
    def get_search_service(
        cls,
        chunk_repository: Optional[ChunkRepository] = None,
        library_service: Optional[ILibraryService] = None
    ) -> ISearchService:
        """Get or create search service instance."""
        if cls._search_service is None:
            chunk_repo = chunk_repository or InMemoryChunkRepository()
            lib_service = library_service or cls.get_library_service()
            cls._search_service = SearchService(chunk_repo, lib_service)
        return cls._search_service

    @classmethod
    def reset(cls) -> None:
        """Reset all service instances (useful for testing)."""
        cls._library_service = None
        cls._chunk_service = None
        cls._search_service = None
