from datetime import datetime
from enum import Enum
from typing import Dict, Any, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator


class IndexType(str, Enum):
    """Supported vector index types."""
    LSH = "LSH"
    HNSW = "HNSW"
    KD_TREE = "KD_TREE"


class Library(BaseModel):
    """Represents a library containing documents and vector index."""
    
    id: UUID = Field(default_factory=uuid4)
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    index_type: IndexType = IndexType.HNSW
    dimension: int = Field(..., gt=0, le=4096)
    total_documents: int = Field(default=0, ge=0)
    total_chunks: int = Field(default=0, ge=0)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    @field_validator('dimension')
    @classmethod
    def validate_dimension(cls, v: int) -> int:
        """Ensure dimension is reasonable for vector operations."""
        if v <= 0 or v > 4096:
            raise ValueError("Dimension must be between 1 and 4096")
        return v
    
    @field_validator('updated_at', mode='before')
    @classmethod
    def update_timestamp(cls, v: Any) -> datetime:
        """Auto-update timestamp on changes."""
        return datetime.utcnow()
    
    model_config = {
        "json_encoders": {
            UUID: str,
            datetime: lambda v: v.isoformat(),
        }
    }