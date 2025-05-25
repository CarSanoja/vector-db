from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime
import numpy as np

from src.domain.entities.chunk import Chunk
from src.domain.repositories.chunk import ChunkRepository
from src.services.library_service import ILibraryService
from src.core.exceptions import NotFoundError, ValidationError
from src.core.logging import get_logger
from .interface import IChunkService

logger = get_logger(__name__)


class ChunkService(IChunkService):
    """Service for managing chunks."""
    
    def __init__(
        self,
        repository: ChunkRepository,
        library_service: ILibraryService
    ):
        self.repository = repository
        self.library_service = library_service
        logger.info("Initialized ChunkService")
    
    async def create_chunk(
        self,
        library_id: UUID,
        content: str,
        embedding: List[float],
        document_id: Optional[UUID] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Chunk:
        """Create a new chunk and add to index."""
        # Validate library exists
        library = await self.library_service.get_library(library_id)
        if not library:
            raise NotFoundError("Library", str(library_id))
        
        # Validate embedding dimension
        if len(embedding) != library.dimension:
            raise ValidationError(
                f"Embedding dimension {len(embedding)} != library dimension {library.dimension}",
                field="embedding"
            )
        
        # Create chunk
        chunk = Chunk(
            content=content,
            embedding=embedding,
            document_id=document_id,
            metadata=metadata or {}
        )
        
        # Add metadata for library association
        chunk.metadata["library_id"] = str(library_id)
        
        # Save chunk
        created = await self.repository.create(chunk)
        
        # Add to vector index
        index = self.library_service.get_index(library_id)
        if index:
            await index.add(created.id, np.array(embedding, dtype=np.float32))
        
        # Update library stats
        await self.library_service.repository.update_stats(
            library_id,
            total_chunks=library.total_chunks + 1
        )
        
        logger.info(
            "Created chunk",
            chunk_id=str(created.id),
            library_id=str(library_id)
        )
        
        return created
    
    async def create_chunks_bulk(
        self,
        library_id: UUID,
        chunks_data: List[Dict[str, Any]]
    ) -> List[Chunk]:
        """Create multiple chunks efficiently."""
        # Validate library
        library = await self.library_service.get_library(library_id)
        if not library:
            raise NotFoundError("Library", str(library_id))
        
        # Create chunk entities
        chunks = []
        index_data = []
        
        for data in chunks_data:
            # Validate embedding dimension
            embedding = data.get("embedding", [])
            if len(embedding) != library.dimension:
                raise ValidationError(
                    f"Embedding dimension {len(embedding)} != library dimension {library.dimension}",
                    field="embedding"
                )
            
            chunk = Chunk(
                content=data["content"],
                embedding=embedding,
                document_id=data.get("document_id"),
                chunk_index=data.get("chunk_index", 0),
                metadata=data.get("metadata", {})
            )
            
            # Add library association
            chunk.metadata["library_id"] = str(library_id)
            chunks.append(chunk)
            index_data.append((chunk.id, np.array(embedding, dtype=np.float32)))
        
        # Bulk save
        created = await self.repository.create_bulk(chunks)
        
        # Bulk add to index
        index = self.library_service.get_index(library_id)
        if index:
            await index.add_batch(index_data)
        
        # Update library stats
        await self.library_service.repository.update_stats(
            library_id,
            total_chunks=library.total_chunks + len(created)
        )
        
        logger.info(
            f"Created {len(created)} chunks in bulk",
            library_id=str(library_id)
        )
        
        return created
    
    async def get_chunk(self, chunk_id: UUID) -> Optional[Chunk]:
        """Get a chunk by ID."""
        return await self.repository.get(chunk_id)
    
    async def update_chunk(
        self,
        chunk_id: UUID,
        content: Optional[str] = None,
        embedding: Optional[List[float]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[Chunk]:
        """Update a chunk and its index entry."""
        chunk = await self.repository.get(chunk_id)
        if not chunk:
            raise NotFoundError("Chunk", str(chunk_id))
        
        # Get library
        library_id = UUID(chunk.metadata.get("library_id"))
        library = await self.library_service.get_library(library_id)
        if not library:
            raise ValidationError("Associated library not found")
        
        # Update fields
        if content is not None:
            chunk.content = content
        
        if embedding is not None:
            if len(embedding) != library.dimension:
                raise ValidationError(
                    f"Embedding dimension {len(embedding)} != library dimension {library.dimension}",
                    field="embedding"
                )
            chunk.embedding = embedding
            
            # Update in index
            index = self.library_service.get_index(library_id)
            if index:
                await index.remove(chunk_id)
                await index.add(chunk_id, np.array(embedding, dtype=np.float32))
        
        if metadata is not None:
            chunk.metadata.update(metadata)
        
        chunk.updated_at = datetime.utcnow()
        
        updated = await self.repository.update(chunk_id, chunk)
        
        logger.info("Updated chunk", chunk_id=str(chunk_id))
        
        return updated
    
    async def delete_chunk(self, chunk_id: UUID) -> bool:
        """Delete a chunk and remove from index."""
        chunk = await self.repository.get(chunk_id)
        if not chunk:
            return False
        
        # Get library
        library_id = UUID(chunk.metadata.get("library_id"))
        library = await self.library_service.get_library(library_id)
        
        # Remove from index
        if library:
            index = self.library_service.get_index(library_id)
            if index:
                await index.remove(chunk_id)
        
        # Delete chunk
        deleted = await self.repository.delete(chunk_id)
        
        # Update library stats
        if library and deleted:
            await self.library_service.repository.update_stats(
                library_id,
                total_chunks=max(0, library.total_chunks - 1)
            )
        
        logger.info("Deleted chunk", chunk_id=str(chunk_id))
        
        return deleted
    
    async def get_chunks_by_document(self, document_id: UUID) -> List[Chunk]:
        """Get all chunks for a document."""
        return await self.repository.get_by_document(document_id)
    
    async def delete_chunks_by_document(self, document_id: UUID) -> int:
        """Delete all chunks for a document."""
        chunks = await self.repository.get_by_document(document_id)
        
        if not chunks:
            return 0
        
        # Get library from first chunk
        library_id = UUID(chunks[0].metadata.get("library_id"))
        library = await self.library_service.get_library(library_id)
        
        # Remove from index
        if library:
            index = self.library_service.get_index(library_id)
            if index:
                for chunk in chunks:
                    await index.remove(chunk.id)
        
        # Delete chunks
        deleted_count = await self.repository.delete_by_document(document_id)
        
        # Update library stats
        if library and deleted_count > 0:
            await self.library_service.repository.update_stats(
                library_id,
                total_chunks=max(0, library.total_chunks - deleted_count)
            )
        
        logger.info(
            f"Deleted {deleted_count} chunks for document",
            document_id=str(document_id)
        )
        
        return deleted_count
    
    async def list_chunks(
        self,
        library_id: UUID,
        limit: int = 100,
        offset: int = 0
    ) -> List[Chunk]:
        """List chunks in a library."""
        # Validate library exists
        library = await self.library_service.get_library(library_id)
        if not library:
            raise NotFoundError("Library", str(library_id))
        
        return await self.repository.get_by_library(library_id, limit, offset)

