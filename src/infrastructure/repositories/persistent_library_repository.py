"""Persistent implementation of library repository."""
from typing import List, Optional, Dict, Any
from uuid import UUID
import asyncio

from src.domain.entities.library import Library, IndexType
from src.domain.repositories.library_repository import ILibraryRepository
from src.infrastructure.persistence.manager import get_persistence_manager
from src.infrastructure.persistence.wal.interface import OperationType
from src.infrastructure.persistence.serialization.serializers import MessagePackSerializer
from src.core.logging import get_logger

logger = get_logger(__name__)


class PersistentLibraryRepository(ILibraryRepository):
    """Library repository with persistence support."""
    
    def __init__(self):
        self._libraries: Dict[UUID, Library] = {}
        self._name_index: Dict[str, UUID] = {}
        self._lock = asyncio.Lock()
        self._persistence = get_persistence_manager()
    
    async def create(self, library: Library) -> Library:
        """Create a new library."""
        async with self._lock:
            if library.id in self._libraries:
                raise ValueError(f"Library {library.id} already exists")
            
            if library.name in self._name_index:
                raise ValueError(f"Library with name '{library.name}' already exists")
            
            # Log to WAL
            await self._persistence.log_operation(
                OperationType.CREATE_LIBRARY,
                library.id,
                MessagePackSerializer._encode_custom(library)
            )
            
            # Update in-memory state
            self._libraries[library.id] = library
            self._name_index[library.name] = library.id
            
            logger.info(f"Created library {library.id}")
            return library
    
    async def get(self, library_id: UUID) -> Optional[Library]:
        """Get library by ID."""
        return self._libraries.get(library_id)
    
    async def get_by_name(self, name: str) -> Optional[Library]:
        """Get library by name."""
        library_id = self._name_index.get(name)
        return self._libraries.get(library_id) if library_id else None
    
    async def update(self, library: Library) -> Optional[Library]:
        """Update an existing library."""
        async with self._lock:
            if library.id not in self._libraries:
                return None
            
            old_library = self._libraries[library.id]
            
            # Check name change
            if old_library.name != library.name:
                if library.name in self._name_index:
                    raise ValueError(f"Library with name '{library.name}' already exists")
                
                # Update name index
                del self._name_index[old_library.name]
                self._name_index[library.name] = library.id
            
            # Log to WAL
            await self._persistence.log_operation(
                OperationType.UPDATE_LIBRARY,
                library.id,
                MessagePackSerializer._encode_custom(library)
            )
            
            # Update in-memory state
            self._libraries[library.id] = library
            
            logger.info(f"Updated library {library.id}")
            return library
    
    async def delete(self, library_id: UUID) -> bool:
        """Delete a library."""
        async with self._lock:
            library = self._libraries.get(library_id)
            if not library:
                return False
            
            # Log to WAL
            await self._persistence.log_operation(
                OperationType.DELETE_LIBRARY,
                library_id,
                {'deleted': True}
            )
            
            # Update in-memory state
            del self._libraries[library_id]
            del self._name_index[library.name]
            
            logger.info(f"Deleted library {library_id}")
            return True
    
    async def list_all(
        self,
        index_type: Optional[IndexType] = None,
        limit: Optional[int] = None,
        offset: int = 0
    ) -> List[Library]:
        """List all libraries with optional filtering."""
        libraries = list(self._libraries.values())
        
        # Filter by index type
        if index_type:
            libraries = [lib for lib in libraries if lib.index_type == index_type]
        
        # Sort by creation date (newest first)
        libraries.sort(key=lambda x: x.created_at, reverse=True)
        
        # Apply pagination
        if offset:
            libraries = libraries[offset:]
        if limit:
            libraries = libraries[:limit]
        
        return libraries
    
    async def count(self) -> int:
        """Count total libraries."""
        return len(self._libraries)
    
    async def get_state(self) -> Dict[str, Any]:
        """Get repository state for persistence."""
        return {
            'libraries': {
                str(k): MessagePackSerializer._encode_custom(v)
                for k, v in self._libraries.items()
            },
            'name_index': {
                k: str(v) for k, v in self._name_index.items()
            }
        }
    
    async def restore_state(self, state: Dict[str, Any]) -> None:
        """Restore repository state from persistence."""
        async with self._lock:
            self._libraries.clear()
            self._name_index.clear()
            
            # Restore libraries
            if 'libraries' in state:
                for lib_id_str, lib_data in state['libraries'].items():
                    library = Library(**lib_data)
                    self._libraries[UUID(lib_id_str)] = library
            
            # Restore name index
            if 'name_index' in state:
                self._name_index = {
                    k: UUID(v) for k, v in state['name_index'].items()
                }
            
            logger.info(f"Restored {len(self._libraries)} libraries")
