"""Library API models."""
from datetime import datetime
from typing import Any, Optional, dict, list
from uuid import UUID

from pydantic import BaseModel, Field

from src.domain.entities.library import IndexType


class LibraryCreate(BaseModel):
    """Request model for creating a library."""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    dimension: int = Field(..., gt=0, le=4096)
    index_type: IndexType = Field(default=IndexType.HNSW)
    metadata: dict[str, Any] = Field(default_factory=dict)


class LibraryUpdate(BaseModel):
    """Request model for updating a library."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    metadata: Optional[dict[str, Any]] = None


class LibraryResponse(BaseModel):
    """Response model for a library."""
    id: UUID
    name: str
    description: Optional[str]
    dimension: int
    index_type: IndexType
    total_documents: int = 0
    total_chunks: int = 0
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
            name=obj.name,
            description=obj.description,
            dimension=obj.dimension,
            index_type=obj.index_type,
            total_documents=getattr(obj, 'total_documents', 0),
            total_chunks=getattr(obj, 'total_chunks', 0),
            metadata=obj.metadata,
            created_at=obj.created_at,
            updated_at=obj.updated_at
        )


class LibraryListResponse(BaseModel):
    """Response model for library list."""
    libraries: list[LibraryResponse]
    total: int
    limit: int
    offset: int
