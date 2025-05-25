from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from uuid import UUID

from src.domain.entities.library import Library, IndexType


class ILibraryService(ABC):
    """Interface for library service."""
    
    @abstractmethod
    async def create_library(
        self,
        name: str,
        dimension: int,
        index_type: IndexType,
        description: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Library:
        """Create a new library."""
        pass
    
    @abstractmethod
    async def get_library(self, library_id: UUID) -> Optional[Library]:
        """Get a library by ID."""
        pass
    
    @abstractmethod
    async def update_library(
        self,
        library_id: UUID,
        name: Optional[str] = None,
        description: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[Library]:
        """Update library information."""
        pass
    
    @abstractmethod
    async def delete_library(self, library_id: UUID) -> bool:
        """Delete a library and all its contents."""
        pass
    
    @abstractmethod
    async def list_libraries(
        self,
        index_type: Optional[IndexType] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Library]:
        """List libraries with optional filtering."""
        pass
    
    @abstractmethod
    async def get_library_by_name(self, name: str) -> Optional[Library]:
        """Get a library by name."""
        pass