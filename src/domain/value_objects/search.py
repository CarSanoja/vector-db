from typing import Any, Optional
from uuid import UUID

import numpy as np
from pydantic import BaseModel, Field, FieldValidationInfo, field_validator


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

    chunk_id: UUID
    content: str
    distance: float
    score: Optional[float] = None
    metadata: dict[str, Any]

    @field_validator("score", mode="before")
    def validate_score(
        cls,
        v: Optional[float],
        info: FieldValidationInfo, 
    ) -> float:
        if v is not None:
            return v
        distance = info.data.get("distance")
        if distance is None:
            raise ValueError("distance is required to compute score")

        return 1.0 / (1.0 + distance)

    @field_validator("score", mode="before")
    def calc_score(cls, v, info: FieldValidationInfo) -> float:
        if v is not None:
            return v
        distance = info.data.get("distance")
        if distance is None:
            raise ValueError("distance is required to compute score")
        return 1.0 / (1.0 + distance)

    class Config:
        """Pydantic model configuration."""
        json_encoders = {
            UUID: str,
        }
