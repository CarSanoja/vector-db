"""In-memory implementation of ChunkRepository."""
from copy import deepcopy
from typing import Any, Optional
from uuid import UUID

from src.core.logging import get_logger
from src.domain.entities.chunk import Chunk
from src.domain.repositories.chunk import ChunkRepository
from src.infrastructure.locks import ReadWriteLock

logger = get_logger(__name__)


class InMemoryChunkRepository(ChunkRepository):
    """In-memory implementation of ChunkRepository."""

    def __init__(self):
        self._storage: dict[UUID, Chunk] = {}
        self._lock = ReadWriteLock()
        # Additional index for document lookups
        self._document_index: dict[UUID, list[UUID]] = {}
        logger.info("Initialized in-memory chunk repository")

    async def create(self, entity: Chunk) -> Chunk:
        """Create a chunk and update indices."""
        async with self._lock.write():
            # Check if chunk already exists
            if entity.id in self._storage:
                raise ValueError(f"Chunk with id {entity.id} already exists")

            # Store the chunk
            stored_chunk = deepcopy(entity)
            self._storage[stored_chunk.id] = stored_chunk

            # Update document index
            if entity.document_id:
                if entity.document_id not in self._document_index:
                    self._document_index[entity.document_id] = []
                self._document_index[entity.document_id].append(entity.id)

            logger.info("Created chunk", chunk_id=str(stored_chunk.id))
            return deepcopy(stored_chunk)

    async def get(self, id: UUID) -> Optional[Chunk]:
        """Get a chunk by ID."""
        async with self._lock.read():
            chunk = self._storage.get(id)
            if chunk:
                return deepcopy(chunk)
            return None

    async def update(self, id: UUID, entity: Chunk) -> Optional[Chunk]:
        """Update a chunk."""
        async with self._lock.write():
            if id not in self._storage:
                return None

            # Ensure the ID matches
            entity.id = id

            # Update storage
            self._storage[id] = deepcopy(entity)
            logger.info("Updated chunk", chunk_id=str(id))
            return deepcopy(entity)

    async def delete(self, id: UUID) -> bool:
        """Delete a chunk and update indices."""
        async with self._lock.write():
            chunk = self._storage.get(id)
            if not chunk:
                return False

            # Update document index
            if chunk.document_id and chunk.document_id in self._document_index:
                self._document_index[chunk.document_id].remove(id)
                if not self._document_index[chunk.document_id]:
                    del self._document_index[chunk.document_id]

            # Delete the chunk
            del self._storage[id]
            logger.info("Deleted chunk", chunk_id=str(id))
            return True

    async def list(
        self,
        filters: Optional[dict[str, Any]] = None,
        limit: int = 100,
        offset: int = 0
    ) -> list[Chunk]:
        """list chunks with optional filtering."""
        async with self._lock.read():
            chunks = list(self._storage.values())

            # Apply filters
            if filters:
                chunks = self._apply_filters(chunks, filters)

            # Apply pagination
            start = offset
            end = offset + limit
            result = chunks[start:end]

            # Return deep copies
            return [deepcopy(chunk) for chunk in result]

    async def count(self, filters: Optional[dict[str, Any]] = None) -> int:
        """Count chunks with optional filtering."""
        async with self._lock.read():
            chunks = list(self._storage.values())

            if filters:
                chunks = self._apply_filters(chunks, filters)

            return len(chunks)

    async def create_bulk(self, chunks: list[Chunk]) -> list[Chunk]:
        """Create multiple chunks efficiently."""
        async with self._lock.write():
            created_chunks = []

            for chunk in chunks:
                if chunk.id in self._storage:
                    raise ValueError(f"Chunk with id {chunk.id} already exists")

                # Store chunk
                stored_chunk = deepcopy(chunk)
                self._storage[stored_chunk.id] = stored_chunk
                created_chunks.append(deepcopy(stored_chunk))

                # Update document index
                if chunk.document_id:
                    if chunk.document_id not in self._document_index:
                        self._document_index[chunk.document_id] = []
                    self._document_index[chunk.document_id].append(chunk.id)

            logger.info(f"Created {len(created_chunks)} chunks in bulk")
            return created_chunks

    async def get_by_document(self, document_id: UUID) -> list[Chunk]:
        """Get all chunks for a document."""
        async with self._lock.read():
            chunk_ids = self._document_index.get(document_id, [])
            chunks = []

            for chunk_id in chunk_ids:
                chunk = self._storage.get(chunk_id)
                if chunk:
                    chunks.append(deepcopy(chunk))

            # Sort by chunk_index
            chunks.sort(key=lambda x: x.chunk_index)
            return chunks

    async def get_by_library(
        self,
        library_id: UUID,
        limit: int = 100,
        offset: int = 0
    ) -> list[Chunk]:
        """Get chunks by library ID through document relationship."""
        # This would require a library-document mapping in a real implementation
        # For now, we'll filter by metadata if library_id is stored there
        filters = {"library_id": str(library_id)}
        return await self.list(filters=filters, limit=limit, offset=offset)

    async def delete_by_document(self, document_id: UUID) -> int:
        """Delete all chunks for a document."""
        async with self._lock.write():
            chunk_ids = self._document_index.get(document_id, []).copy()
            deleted_count = 0

            for chunk_id in chunk_ids:
                if chunk_id in self._storage:
                    del self._storage[chunk_id]
                    deleted_count += 1

            # Clear document index
            if document_id in self._document_index:
                del self._document_index[document_id]

            logger.info(
                f"Deleted {deleted_count} chunks for document",
                document_id=str(document_id)
            )
            return deleted_count

    async def search_by_metadata(
        self,
        library_id: UUID,
        metadata_filters: dict[str, Any],
        limit: int = 100
    ) -> list[Chunk]:
        """Search chunks by metadata filters."""
        async with self._lock.read():
            matching_chunks = []

            for chunk in self._storage.values():
                # Check library association (would need proper implementation)
                if not self._matches_library(chunk, library_id):
                    continue

                # Check metadata filters
                if self._matches_metadata(chunk.metadata, metadata_filters):
                    matching_chunks.append(deepcopy(chunk))

                    if len(matching_chunks) >= limit:
                        break

            return matching_chunks

    def _apply_filters(self, entities: list[Chunk], filters: dict[str, Any]) -> list[Chunk]:
        """Apply filters to entity list."""
        filtered = []
        for entity in entities:
            match = True
            for field, value in filters.items():
                # Check entity fields
                if hasattr(entity, field):
                    entity_value = getattr(entity, field)
                    if entity_value != value:
                        match = False
                        break
                # Check metadata fields
                elif field in entity.metadata:
                    if entity.metadata[field] != value:
                        match = False
                        break
                else:
                    match = False
                    break
            if match:
                filtered.append(entity)
        return filtered

    def _matches_library(self, chunk: Chunk, library_id: UUID) -> bool:
        """Check if chunk belongs to library (simplified)."""
        # In a real implementation, this would check through document relationships
        return chunk.metadata.get("library_id") == str(library_id)

    def _matches_metadata(
        self,
        chunk_metadata: dict[str, Any],
        filters: dict[str, Any]
    ) -> bool:
        """Check if chunk metadata matches all filters."""
        for key, value in filters.items():
            if key not in chunk_metadata:
                return False

            # Support different filter operations
            if isinstance(value, dict):
                # Advanced filtering (e.g., {"$gt": 5})
                if not self._apply_operator_filter(chunk_metadata[key], value):
                    return False
            else:
                # Simple equality
                if chunk_metadata[key] != value:
                    return False

        return True

    def _apply_operator_filter(self, field_value: Any, filter_spec: dict[str, Any]) -> bool:
        """Apply operator-based filters."""
        for operator, value in filter_spec.items():
            if operator == "$gt" and not (field_value > value):
                return False
            elif operator == "$gte" and not (field_value >= value):
                return False
            elif operator == "$lt" and not (field_value < value):
                return False
            elif operator == "$lte" and not (field_value <= value):
                return False
            elif operator == "$ne" and not (field_value != value):
                return False
            elif operator == "$in" and field_value not in value:
                return False
            elif operator == "$nin" and field_value in value:
                return False

        return True
