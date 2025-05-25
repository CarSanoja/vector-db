from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime

from src.domain.entities.library import Library, IndexType
from src.domain.repositories.library import LibraryRepository
from src.core.exceptions import NotFoundError, ConflictError, ValidationError
from src.core.indexes import IndexFactory
from src.core.logging import get_logger
from .interface import ILibraryService

logger = get_logger(__name__)


class LibraryService(ILibraryService):
    """Service for managing libraries."""
    
    def __init__(self, repository: LibraryRepository):
        self.repository = repository
        self._indexes: Dict[UUID, Any] = {}  # In-memory index storage
        logger.info("Initialized LibraryService")
    
    async def create_library(
        self,
        name: str,
        dimension: int,
        index_type: IndexType,
        description: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Library:
        """Create a new library with associated vector index."""
        # Check if name already exists
        existing = await self.repository.get_by_name(name)
        if existing:
            raise ConflictError(
                f"Library with name '{name}' already exists",
                conflict_type="duplicate_name"
            )
        
        # Create library entity
        library = Library(
            name=name,
            description=description,
            index_type=index_type,
            dimension=dimension,
            metadata=metadata or {}
        )
        
        # Create vector index
        try:
            index = IndexFactory.create_index(index_type, dimension)
            self._indexes[library.id] = index
        except Exception as e:
            raise ValidationError(f"Failed to create index: {str(e)}")
        
        # Save library
        created = await self.repository.create(library)
        
        logger.info(
            "Created library",
            library_id=str(created.id),
            name=created.name,
            index_type=created.index_type.value
        )
        
        return created
    
    async def get_library(self, library_id: UUID) -> Optional[Library]:
        """Get a library by ID."""
        library = await self.repository.get(library_id)
        
        if library and library_id not in self._indexes:
            # Recreate index if not in memory
            self._indexes[library_id] = IndexFactory.create_index(
                library.index_type,
                library.dimension
            )
        
        return library
    
    async def update_library(
        self,
        library_id: UUID,
        name: Optional[str] = None,
        description: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[Library]:
        """Update library information."""
        library = await self.repository.get(library_id)
        if not library:
            raise NotFoundError("Library", str(library_id))
        
        # Check name uniqueness if changing
        if name and name != library.name:
            existing = await self.repository.get_by_name(name)
            if existing:
                raise ConflictError(
                    f"Library with name '{name}' already exists",
                    conflict_type="duplicate_name"
                )
            library.name = name
        
        if description is not None:
            library.description = description
        
        if metadata is not None:
            library.metadata.update(metadata)
        
        library.updated_at = datetime.utcnow()
        
        updated = await self.repository.update(library_id, library)
        
        logger.info("Updated library", library_id=str(library_id))
        
        return updated
    
    async def delete_library(self, library_id: UUID) -> bool:
        """Delete a library and all its contents."""
        library = await self.repository.get(library_id)
        if not library:
            return False
        
        # Clear index
        if library_id in self._indexes:
            await self._indexes[library_id].clear()
            del self._indexes[library_id]
        
        # Delete library
        deleted = await self.repository.delete(library_id)
        
        logger.info("Deleted library", library_id=str(library_id))
        
        return deleted
    
    async def list_libraries(
        self,
        index_type: Optional[IndexType] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Library]:
        """List libraries with optional filtering."""
        if index_type:
            return await self.repository.list_by_index_type(index_type)
        
        return await self.repository.list(limit=limit, offset=offset)
    
    async def get_library_by_name(self, name: str) -> Optional[Library]:
        """Get a library by name."""
        return await self.repository.get_by_name(name)
    
    def get_index(self, library_id: UUID):
        """Get the vector index for a library."""
        return self._indexes.get(library_id)