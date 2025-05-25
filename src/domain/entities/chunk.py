"""Chunk entity."""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, List, Optional
from uuid import UUID


@dataclass
class Chunk:
    """Represents a text chunk with embedding."""
    id: UUID
    library_id: UUID  # Este campo es necesario
    content: str
    embedding: List[float]
    document_id: Optional[UUID] = None
    chunk_index: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    
    def __post_init__(self):
        """Validate chunk after initialization."""
        if not self.content:
            raise ValueError("Content cannot be empty")
        if not self.embedding:
            raise ValueError("Embedding cannot be empty")
        if len(self.content) > 10000:
            raise ValueError("Content cannot exceed 10000 characters")
