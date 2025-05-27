from typing import Any, Optional
from uuid import UUID

import numpy as np
from pydantic import BaseModel, Field, field_validator


class SearchQuery(BaseModel):
    """Encapsulates parameters for vector similarity search."""

    embedding: list[float] = Field(..., min_items=1)
    k: int = Field(default=10, gt=0, le=1000)
    library_id: UUID
    metadata_filters: Optional[dict[str, Any]] = None

    @field_validator('embedding')
    def validate_embedding(cls, v):
        """Ensure embedding is valid."""
        if not all(isinstance(x, (int, float)) for x in v):
            raise ValueError("Embedding must contain only numbers")
        return v

    def to_numpy(self) -> np.ndarray:
        """Convert embedding to numpy array."""
        return np.array(self.embedding, dtype=np.float32)


class SearchResult(BaseModel):
    """Represents a single search result."""

    chunk_id: UUID
    content: str
    distance: float = Field(..., ge=0)
    score: float = Field(..., ge=0, le=1)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator('score')
    def validate_score(cls, v, values):
        """Calculate score from distance if not provided."""
        if 'distance' in values:
            # Convert distance to similarity score (0-1)
            return 1 / (1 + values['distance'])
        return v

    class Config:
        """Pydantic model configuration."""
        json_encoders = {
            UUID: str,
        }
