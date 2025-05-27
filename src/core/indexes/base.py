from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, list, tuple
from uuid import UUID

import numpy as np


@dataclass
class IndexConfig:
    """Base configuration for vector indexes."""
    dimension: int
    metric: str = "euclidean"  # euclidean, cosine, dot


class VectorIndex(ABC):
    """Abstract base class for vector indexes."""

    def __init__(self, config: IndexConfig):
        self.config = config
        self.dimension = config.dimension
        self.metric = config.metric
        self._size = 0

    @abstractmethod
    async def add(self, vector_id: UUID, vector: np.ndarray) -> None:
        """Add a vector to the index."""
        pass

    @abstractmethod
    async def add_batch(self, vectors: list[tuple[UUID, np.ndarray]]) -> None:
        """Add multiple vectors to the index."""
        pass

    @abstractmethod
    async def search(
        self,
        query_vector: np.ndarray,
        k: int,
        filter_ids: Optional[list[UUID]] = None
    ) -> list[tuple[UUID, float]]:
        """Search for k nearest neighbors."""
        pass

    @abstractmethod
    async def remove(self, vector_id: UUID) -> bool:
        """Remove a vector from the index."""
        pass

    @abstractmethod
    async def clear(self) -> None:
        """Clear all vectors from the index."""
        pass

    @property
    def size(self) -> int:
        """Return the number of vectors in the index."""
        return self._size

    def _compute_distance(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """Compute distance between two vectors based on metric."""
        if self.metric == "euclidean":
            return float(np.linalg.norm(vec1 - vec2))
        elif self.metric == "cosine":
            # Cosine distance = 1 - cosine similarity
            norm1 = np.linalg.norm(vec1)
            norm2 = np.linalg.norm(vec2)
            if norm1 == 0 or norm2 == 0:
                return 1.0
            return float(1 - np.dot(vec1, vec2) / (norm1 * norm2))
        elif self.metric == "dot":
            # Negative dot product (so larger dot product = smaller distance)
            return float(-np.dot(vec1, vec2))
        else:
            raise ValueError(f"Unknown metric: {self.metric}")
