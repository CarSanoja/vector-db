"""Domain value objects."""
from dataclasses import dataclass
from typing import Dict, Any
from uuid import UUID


@dataclass
class SearchResult:
    """Represents a search result."""
    chunk_id: UUID
    content: str
    score: float
    distance: float
    metadata: Dict[str, Any]
    
    class Config:
        from_attributes = True
