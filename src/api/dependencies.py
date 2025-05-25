from typing import Annotated

from fastapi import Depends, HTTPException, status

from src.services import ServiceFactory, ILibraryService, IChunkService, ISearchService
from src.api.models.common import PaginationParams


def get_library_service() -> ILibraryService:
    """Get library service instance."""
    return ServiceFactory.get_library_service()


def get_chunk_service() -> IChunkService:
    """Get chunk service instance."""
    return ServiceFactory.get_chunk_service()


def get_search_service() -> ISearchService:
    """Get search service instance."""
    return ServiceFactory.get_search_service()


# Type aliases for dependency injection
LibraryServiceDep = Annotated[ILibraryService, Depends(get_library_service)]
ChunkServiceDep = Annotated[IChunkService, Depends(get_chunk_service)]
SearchServiceDep = Annotated[ISearchService, Depends(get_search_service)]
PaginationDep = Annotated[PaginationParams, Depends()]