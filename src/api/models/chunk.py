"""Chunk API models."""
from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class ChunkCreate(BaseModel):
    """Request model for creating a chunk."""
    content: str = Field(..., min_length=1, max_length=10000)
    embedding: list[float] = Field(..., min_items=1)
    document_id: Optional[UUID] = None
    chunk_index: int = Field(default=0, ge=0)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ChunkUpdate(BaseModel):
    """Request model for updating a chunk."""
    content: Optional[str] = Field(None, min_length=1, max_length=10000)
    embedding: Optional[list[float]] = Field(None, min_items=1)
    metadata: Optional[dict[str, Any]] = None


class ChunkResponse(BaseModel):
    """Response model for a chunk."""
    id: UUID
    content: str
    document_id: Optional[UUID]
    chunk_index: int
    metadata: dict[str, Any]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

    @classmethod
    def from_orm(cls, obj):
        """Create from ORM object."""
        return cls(
            id=obj.id,
            content=obj.content,
            document_id=obj.document_id,
            chunk_index=obj.chunk_index,
            metadata=obj.metadata,
            created_at=obj.created_at,
            updated_at=obj.updated_at
        )


class ChunkBulkCreate(BaseModel):
    """Request model for bulk chunk creation."""
    chunks: list[ChunkCreate]


class ChunkListResponse(BaseModel):
    """Response model for chunk list."""
    chunks: list[ChunkResponse]
    total: int
    limit: int
    offset: int
