from datetime import datetime
from typing import Dict, Any, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator
import numpy as np


class Chunk(BaseModel):
    """Represents a chunk of text with its embedding and metadata."""
    
    id: UUID = Field(default_factory=uuid4)
    content: str = Field(..., min_length=1, max_length=10000)
    embedding: list[float] = Field(..., min_items=1)
    document_id: Optional[UUID] = None
    chunk_index: int = Field(default=0, ge=0)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    @field_validator('embedding')
    @classmethod
    def validate_embedding(cls, v: list[float]) -> list[float]:
        """Ensure embedding is a valid vector."""
        if not isinstance(v, list) or not all(isinstance(x, (int, float)) for x in v):
            raise ValueError("Embedding must be a list of numbers")
        return v
    
    @field_validator('updated_at', mode='before')
    @classmethod
    def update_timestamp(cls, v: Any) -> datetime:
        """Auto-update timestamp on changes."""
        return datetime.utcnow()
    
    def to_numpy(self) -> np.ndarray:
        """Convert embedding to numpy array."""
        return np.array(self.embedding, dtype=np.float32)
    
    model_config = {
        "json_encoders": {
            UUID: str,
            datetime: lambda v: v.isoformat(),
        }
    }