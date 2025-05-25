"""Service factory for dependency injection."""
from .service_interfaces import ILibraryService, IChunkService, ISearchService
from .stub_implementations import StubLibraryService, StubChunkService, StubSearchService


class ServiceFactory:
    """Factory for creating service instances."""
    
    _library_service: ILibraryService = None
    _chunk_service: IChunkService = None
    _search_service: ISearchService = None
    
    @classmethod
    def get_library_service(cls) -> ILibraryService:
        """Get library service instance."""
        if cls._library_service is None:
            cls._library_service = StubLibraryService()
        return cls._library_service
    
    @classmethod
    def get_chunk_service(cls) -> IChunkService:
        """Get chunk service instance."""
        if cls._chunk_service is None:
            cls._chunk_service = StubChunkService()
        return cls._chunk_service
    
    @classmethod
    def get_search_service(cls) -> ISearchService:
        """Get search service instance."""
        if cls._search_service is None:
            cls._search_service = StubSearchService()
        return cls._search_service
