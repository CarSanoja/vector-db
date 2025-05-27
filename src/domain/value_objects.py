"""Domain value objects."""
from dataclasses import dataclass
from typing import Any, dict
from uuid import UUID


@dataclass
class SearchResult:
    """Represents a search result."""
    chunk_id: UUID
    content: str
    score: float
    distance: float
    metadata: dict[str, Any]

    class Config:
        from_attributes = True
