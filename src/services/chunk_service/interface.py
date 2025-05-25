from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from uuid import UUID

from src.domain.entities.chunk import Chunk


class IChunkService(ABC):
    """Interface for chunk service."""
    
    @abstractmethod
    async def create_chunk(
        self,
        library_id: UUID,
        content: str,
        embedding: List[float],
        document_id: Optional[UUID] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Chunk:
        """Create a new chunk."""
        pass
    
    @abstractmethod
    async def create_chunks_bulk(
        self,
        library_id: UUID,
        chunks_data: List[Dict[str, Any]]
    ) -> List[Chunk]:
        """Create multiple chunks in bulk."""
        pass
    
    @abstractmethod
    async def get_chunk(self, chunk_id: UUID) -> Optional[Chunk]:
        """Get a chunk by ID."""
        pass
    
    @abstractmethod
    async def update_chunk(
        self,
        chunk_id: UUID,
        content: Optional[str] = None,
        embedding: Optional[List[float]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[Chunk]:
        """Update a chunk."""
        pass
    
    @abstractmethod
    async def delete_chunk(self, chunk_id: UUID) -> bool:
        """Delete a chunk."""
        pass
    
    @abstractmethod
    async def get_chunks_by_document(self, document_id: UUID) -> List[Chunk]:
        """Get all chunks for a document."""
        pass
    
    @abstractmethod
    async def delete_chunks_by_document(self, document_id: UUID) -> int:
        """Delete all chunks for a document."""
        pass
    
    @abstractmethod
    async def list_chunks(
        self,
        library_id: UUID,
        limit: int = 100,
        offset: int = 0
    ) -> List[Chunk]:
        """List chunks in a library."""
        pass
