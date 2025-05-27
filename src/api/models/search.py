"""Search API models."""
from typing import Any, Optional, dict, list
from uuid import UUID

from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    """Request model for vector search."""
    embedding: list[float] = Field(..., min_items=1)
    k: int = Field(default=10, gt=0, le=1000)
    metadata_filters: Optional[dict[str, Any]] = None


class SearchResult(BaseModel):
    """Single search result."""
    chunk_id: UUID
    content: str
    score: float
    distance: float
    metadata: dict[str, Any]

    class Config:
        from_attributes = True

    @classmethod
    def from_orm(cls, obj):
        """Create from ORM object."""
        return cls(
            chunk_id=obj.chunk_id,
            content=obj.content,
            score=obj.score,
            distance=obj.distance,
            metadata=obj.metadata
        )


class SearchResponse(BaseModel):
    """Response model for search results."""
    results: list[SearchResult]
    query_time_ms: float
    total_found: int


class MultiSearchRequest(BaseModel):
    """Request model for multi-library search."""
    library_ids: list[UUID] = Field(..., min_items=1)
    embedding: list[float] = Field(..., min_items=1)
    k: int = Field(default=10, gt=0, le=1000)
    metadata_filters: Optional[dict[str, Any]] = None


class MultiSearchResponse(BaseModel):
    """Response model for multi-library search."""
    results: dict[UUID, list[SearchResult]]
    query_time_ms: float
    total_found: int
