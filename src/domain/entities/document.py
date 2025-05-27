from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, validator


class Document(BaseModel):
    """Represents a document containing multiple chunks."""

    id: UUID = Field(default_factory=uuid4)
    name: str = Field(..., min_length=1, max_length=255)
    library_id: UUID
    total_chunks: int = Field(default=0, ge=0)
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    @validator('tags')
    def validate_tags(cls, v):
        """Ensure tags are unique and lowercase."""
        return list({tag.lower().strip() for tag in v if tag.strip()})

    @validator('updated_at', always=True)
    def update_timestamp(cls, v):
        """Auto-update timestamp on changes."""
        return datetime.utcnow()

    class Config:
        """Pydantic model configuration."""
        json_encoders = {
            UUID: str,
            datetime: lambda v: v.isoformat(),
        }
