from datetime import datetime
from typing import Any, Optional, dict, list
from uuid import UUID, uuid4

from src.core.exceptions import ConflictError
from src.domain.entities.chunk import Chunk
from src.domain.entities.library import IndexType, Library
from src.domain.value_objects import SearchResult

from .service_interfaces import IChunkService, ILibraryService, ISearchService


class StubLibraryService(ILibraryService):
    """Stub library service for testing."""

    def __init__(self):
        self._libraries: dict[UUID, Library] = {}

    async def create_library(
        self,
        name: str,
        dimension: int,
        index_type: IndexType,
        description: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None
    ) -> Library:
        """Create a new library."""
        # Check for duplicate names
        for lib in self._libraries.values():
            if lib.name == name:
                raise ConflictError(f"Library with name '{name}' already exists")

        library = Library(
            id=uuid4(),
            name=name,
            dimension=dimension,
            index_type=index_type,
            description=description,
            metadata=metadata or {},
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        self._libraries[library.id] = library
        return library

    async def get_library(self, library_id: UUID) -> Optional[Library]:
        """Get library by ID."""
        return self._libraries.get(library_id)

    async def list_libraries(
        self,
        index_type: Optional[IndexType] = None,
        limit: int = 100,
        offset: int = 0
    ) -> list[Library]:
        """list libraries."""
        libraries = list(self._libraries.values())
        if index_type:
            libraries = [lib for lib in libraries if lib.index_type == index_type]
        return libraries[offset:offset + limit]

    async def update_library(
        self,
        library_id: UUID,
        name: Optional[str] = None,
        description: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None
    ) -> Optional[Library]:
        """Update library."""
        library = self._libraries.get(library_id)
        if not library:
            return None

        if name and name != library.name:
            # Check for duplicate names
            for lib in self._libraries.values():
                if lib.name == name and lib.id != library_id:
                    raise ConflictError(f"Library with name '{name}' already exists")
            library.name = name

        if description is not None:
            library.description = description
        if metadata is not None:
            library.metadata = metadata

        library.updated_at = datetime.utcnow()
        return library

    async def delete_library(self, library_id: UUID) -> bool:
        """Delete library."""
        if library_id in self._libraries:
            del self._libraries[library_id]
            return True
        return False


class StubChunkService(IChunkService):
    """Stub chunk service for testing."""

    def __init__(self):
        self._chunks: dict[UUID, Chunk] = {}
        self._library_chunks: dict[UUID, list[UUID]] = {}

    async def create_chunk(
        self,
        library_id: UUID,
        content: str,
        embedding: list[float],
        document_id: Optional[UUID] = None,
        metadata: Optional[dict[str, Any]] = None
    ) -> Chunk:
        """Create a chunk."""
        chunk = Chunk(
            id=uuid4(),
            library_id=library_id,
            content=content,
            embedding=embedding,
            document_id=document_id,
            chunk_index=0,
            metadata=metadata or {},
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )

        self._chunks[chunk.id] = chunk
        if library_id not in self._library_chunks:
            self._library_chunks[library_id] = []
        self._library_chunks[library_id].append(chunk.id)

        return chunk

    async def create_chunks_bulk(
        self,
        library_id: UUID,
        chunks_data: list[dict[str, Any]]
    ) -> list[Chunk]:
        """Create multiple chunks."""
        chunks = []
        for data in chunks_data:
            chunk = await self.create_chunk(
                library_id=library_id,
                content=data["content"],
                embedding=data["embedding"],
                document_id=data.get("document_id"),
                metadata=data.get("metadata", {})
            )
            chunks.append(chunk)
        return chunks

    async def get_chunk(self, chunk_id: UUID) -> Optional[Chunk]:
        """Get chunk by ID."""
        return self._chunks.get(chunk_id)

    async def list_chunks(
        self,
        library_id: UUID,
        limit: int = 100,
        offset: int = 0
    ) -> list[Chunk]:
        """list chunks in library."""
        chunk_ids = self._library_chunks.get(library_id, [])
        chunks = [self._chunks[cid] for cid in chunk_ids if cid in self._chunks]
        return chunks[offset:offset + limit]

    async def update_chunk(
        self,
        chunk_id: UUID,
        content: Optional[str] = None,
        embedding: Optional[list[float]] = None,
        metadata: Optional[dict[str, Any]] = None
    ) -> Optional[Chunk]:
        """Update chunk."""
        chunk = self._chunks.get(chunk_id)
        if not chunk:
            return None

        if content is not None:
            chunk.content = content
        if embedding is not None:
            chunk.embedding = embedding
        if metadata is not None:
            chunk.metadata = metadata

        chunk.updated_at = datetime.utcnow()
        return chunk

    async def delete_chunk(self, chunk_id: UUID) -> bool:
        """Delete chunk."""
        chunk = self._chunks.get(chunk_id)
        if not chunk:
            return False

        del self._chunks[chunk_id]
        if chunk.library_id in self._library_chunks:
            self._library_chunks[chunk.library_id].remove(chunk_id)

        return True


class StubSearchService(ISearchService):
    """Stub search service for testing."""

    async def search(
        self,
        library_id: UUID,
        embedding: list[float],
        k: int = 10,
        metadata_filters: Optional[dict[str, Any]] = None
    ) -> list[SearchResult]:
        """Search for similar chunks."""
        # Return empty results for now
        return []

    async def multi_library_search(
        self,
        library_ids: list[UUID],
        embedding: list[float],
        k: int = 10,
        metadata_filters: Optional[dict[str, Any]] = None
    ) -> dict[UUID, list[SearchResult]]:
        """Search across multiple libraries."""
        return {lib_id: [] for lib_id in library_ids}
