from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime

from src.domain.entities.library import Library, IndexType
from src.domain.repositories.library import LibraryRepository
from src.core.exceptions import NotFoundError, ConflictError, ValidationError
from src.core.indexes.factory import IndexFactory 
from src.core.indexes.base import VectorIndex 
from src.core.logging import get_logger
from .interface import ILibraryService 

logger = get_logger(__name__)


class LibraryService(ILibraryService):
    """Service for managing libraries."""

    def __init__(self, repository: LibraryRepository):
        self.repository = repository
        self._indexes: Dict[UUID, VectorIndex] = {} 
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
        existing = await self.repository.get_by_name(name)
        if existing:
            raise ConflictError(
                f"Library with name '{name}' already exists",
                conflict_type="duplicate_name"
            )

        library = Library(
            name=name,
            description=description,
            index_type=index_type,
            dimension=dimension,
            metadata=metadata or {}
        )

        try:
            index_instance = IndexFactory.create_index(index_type, dimension)
            self._indexes[library.id] = index_instance
        except Exception as e:
            logger.error(f"Failed to create index for library {library.name}: {e}", exc_info=True)
            raise ValidationError(f"Failed to create index: {str(e)}")

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
            logger.warning(f"Index for library {library_id} not found in memory cache. Recreating.")
            try:
                index_instance = IndexFactory.create_index(
                    library.index_type,
                    library.dimension
                )
                self._indexes[library_id] = index_instance
            except Exception as e:
                logger.error(f"Failed to recreate index for library {library_id}: {e}", exc_info=True)
        return library

    def get_index(self, library_id: UUID) -> Optional[VectorIndex]:
        """Get the vector index for a library."""
        index = self._indexes.get(library_id)
        if not index:
            logger.warning(f"Attempted to get index for library {library_id}, but it was not found in memory.")
        return index

    async def build_index(self, library_id: UUID) -> None:
        """
        Builds or finalizes the vector index for the given library.
        This is typically called after adding a significant number of chunks.
        """
        logger.info(f"Attempting to build index for library_id: {library_id}")
        library = await self.get_library(library_id) 
        if not library:
            raise NotFoundError("Library", str(library_id))

        index_instance = self.get_index(library_id)
        if not index_instance:
            logger.error(f"Index instance for library {library_id} not found when trying to build.")
            raise ValidationError(f"Index not available for library {library_id}. Cannot build.")

        if hasattr(index_instance, 'build') and callable(getattr(index_instance, 'build')):
            logger.info(f"Calling build() on index for library {library_id} (type: {library.index_type.value})")
            try:
                await index_instance.build()
                logger.info(f"Successfully built index for library {library_id}")
            except Exception as e:
                logger.error(f"Error building index for library {library_id}: {e}", exc_info=True)
                raise RuntimeError(f"Failed to build index for library {library_id}: {str(e)}")
        elif hasattr(index_instance, 'train') and callable(getattr(index_instance, 'train')):
            logger.info(f"Calling train() on index for library {library_id} (type: {library.index_type.value})")
            try:
                await index_instance.train() 
                logger.info(f"Successfully trained index for library {library_id}")
            except Exception as e:
                logger.error(f"Error training index for library {library_id}: {e}", exc_info=True)
                raise RuntimeError(f"Failed to train index for library {library_id}: {str(e)}")
        else:
            logger.info(
                f"Index type {library.index_type.value} for library {library_id} "
                f"does not have an explicit build() or train() method, or it builds automatically."
            )

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

        if name and name != library.name:
            existing = await self.repository.get_by_name(name)
            if existing and existing.id != library_id: 
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
            logger.warning(f"Attempted to delete non-existent library: {library_id}")
            return False

        if library_id in self._indexes:
            index_instance = self._indexes[library_id]
            if hasattr(index_instance, 'clear') and callable(getattr(index_instance, 'clear')):
                try:
                    index_instance.clear() 
                except Exception as e:
                    logger.error(f"Error clearing index for library {library_id} during deletion: {e}", exc_info=True)
            del self._indexes[library_id]
            logger.info(f"Removed index for library {library_id} from memory.")

        deleted = await self.repository.delete(library_id)
        if deleted:
            logger.info("Deleted library from repository", library_id=str(library_id))
        else:
            logger.warning(f"Failed to delete library {library_id} from repository, it might have been already deleted.")
        return deleted

    async def list_libraries(
        self,
        index_type: Optional[IndexType] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Library]:
        """List libraries with optional filtering."""
        if index_type:
            return await self.repository.list_by_index_type(index_type, limit=limit, offset=offset)
        else:
            return await self.repository.list(limit=limit, offset=offset)

    async def get_library_by_name(self, name: str) -> Optional[Library]:
        """Get a library by name."""
        library = await self.repository.get_by_name(name)
        if library and library.id not in self._indexes:
            logger.warning(f"Index for library {library.name} (ID: {library.id}) not found in memory cache. Recreating.")
            try:
                index_instance = IndexFactory.create_index(
                    library.index_type,
                    library.dimension
                )
                self._indexes[library.id] = index_instance
            except Exception as e:
                logger.error(f"Failed to recreate index for library {library.name}: {e}", exc_info=True)
        return library