from __future__ import annotations

import asyncio
import builtins
from typing import Any, Optional
from uuid import UUID

from src.core.logging import get_logger
from src.domain.entities.library import Library
from src.domain.repositories.library import (
    LibraryRepository,  # Changed from ILibraryRepository
)
from src.infrastructure.persistence.manager import get_persistence_manager
from src.infrastructure.persistence.serialization.serializers import (
    MessagePackSerializer,
)
from src.infrastructure.persistence.wal.interface import OperationType

logger = get_logger(__name__)


class PersistentLibraryRepository(LibraryRepository):  # Changed from ILibraryRepository
    """Library repository with persistence support."""

    def __init__(self):
        self._libraries: dict[UUID, Library] = {}
        self._name_index: dict[str, UUID] = {}
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

    async def get_or_create(self, library: Library) -> tuple[Library, bool]:
        async with self._lock:
            existing = await self.get_by_name(library.name)
            if existing:
                return existing, False

            created = await self.create(library)
            return created, True

    async def get(self, id: UUID) -> Library | None:
        """Get library by ID."""
        return self._libraries.get(id)

    async def get_by_name(self, name: str) -> Library | None:
        """Get library by name."""
        library_id = self._name_index.get(name)
        return self._libraries.get(library_id) if library_id else None

    async def update(self, id: UUID, entity: Library) -> Library | None:
        """Update an existing library."""
        async with self._lock:
            if id not in self._libraries:
                return None

            old_library = self._libraries[id]

            # Check name change
            if old_library.name != entity.name:
                if entity.name in self._name_index:
                    raise ValueError(f"Library with name '{entity.name}' already exists")

                # Update name index
                del self._name_index[old_library.name]
                self._name_index[entity.name] = entity.id

            # Log to WAL
            await self._persistence.log_operation(
                OperationType.UPDATE_LIBRARY,
                entity.id,
                MessagePackSerializer._encode_custom(entity)
            )

            # Update in-memory state
            self._libraries[id] = entity

            logger.info(f"Updated library {id}")
            return entity

    async def delete(self, id: UUID) -> bool:
        """Delete a library."""
        async with self._lock:
            library = self._libraries.get(id)
            if not library:
                return False

            # Log to WAL
            await self._persistence.log_operation(
                OperationType.DELETE_LIBRARY,
                id,
                {'deleted': True}
            )

            # Update in-memory state
            del self._libraries[id]
            del self._name_index[library.name]

            logger.info(f"Deleted library {id}")
            return True

    async def list(
        self,
        filters: dict[str, Any] | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> builtins.list[Library]:
        """Alias de list_all para cumplir la ABC."""
        return await self.list_all(filters=filters, limit=limit, offset=offset)

    async def list_all(
        self,
        filters: dict[str, Any] | None = None,
        limit: int = 100,
        offset: int = 0
    ) -> list[Library]:
        """list all libraries with optional filtering."""
        libraries = list(self._libraries.values())

        # Apply filters if provided
        if filters:
            if 'index_type' in filters:
                index_type = filters['index_type']
                libraries = [lib for lib in libraries if lib.index_type == index_type]

        # Sort by creation date (newest first)
        libraries.sort(key=lambda x: x.created_at, reverse=True)

        # Apply pagination
        if offset:
            libraries = libraries[offset:]
        if limit:
            libraries = libraries[:limit]

        return libraries

    async def list_by_index_type(self, index_type: str) -> list[Library]:
        """list libraries by index type."""
        return await self.list_all(filters={'index_type': index_type})

    async def update_stats(
        self,
        id: UUID,
        total_documents: int | None = None,
        total_chunks: int | None = None
    ) -> Library | None:
        """Update library statistics."""
        library = self._libraries.get(id)
        if not library:
            return None

        # Update stats
        if total_documents is not None:
            library.total_documents = total_documents
        if total_chunks is not None:
            library.total_chunks = total_chunks

        # Use regular update to persist
        return await self.update(id, library)

    async def count(self, filters: dict[str, Any] | None = None) -> int:
        """Count total libraries."""
        if filters:
            libraries = await self.list_all(filters=filters, limit=10000)
            return len(libraries)
        return len(self._libraries)

    async def get_state(self) -> dict[str, Any]:
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

    async def restore_state(self, state: dict[str, Any]) -> None:
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
