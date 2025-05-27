from collections import defaultdict
from dataclasses import dataclass
from typing import Optional
from uuid import UUID

import numpy as np

from src.core.logging import get_logger
from src.infrastructure.locks import ReadWriteLock

from .base import IndexConfig, VectorIndex

logger = get_logger(__name__)


@dataclass
class LSHConfig(IndexConfig):
    """Configuration for LSH index."""
    num_tables: int = 10
    key_size: int = 10
    seed: int = 42


class LSHIndex(VectorIndex):
    """Locality Sensitive Hashing index implementation."""

    def __init__(self, config: LSHConfig):
        super().__init__(config)
        self.config: LSHConfig = config
        self._lock = ReadWriteLock()

        # Initialize random hyperplanes for each table
        np.random.seed(config.seed)
        self._hyperplanes = [
            np.random.randn(config.key_size, config.dimension)
            for _ in range(config.num_tables)
        ]

        # Hash tables: table_idx -> hash_key -> set of vector IDs
        self._tables: list[dict[str, set[UUID]]] = [
            defaultdict(set) for _ in range(config.num_tables)
        ]

        # Vector storage
        self._vectors: dict[UUID, np.ndarray] = {}

        logger.info(
            "Initialized LSH index",
            dimension=config.dimension,
            num_tables=config.num_tables,
            key_size=config.key_size
        )

    def _hash_vector(self, vector: np.ndarray, table_idx: int) -> str:
        """Generate hash key for a vector in a specific table."""
        # Project vector onto hyperplanes
        projections = np.dot(self._hyperplanes[table_idx], vector)
        # Convert to binary hash
        binary_hash = (projections > 0).astype(int)
        # Convert to string key
        return ''.join(map(str, binary_hash))

    async def add(self, vector_id: UUID, vector: np.ndarray) -> None:
        """Add a vector to the index."""
        if vector.shape[0] != self.dimension:
            raise ValueError(f"Vector dimension {vector.shape[0]} != index dimension {self.dimension}")

        async with self._lock.write():
            # Store vector
            self._vectors[vector_id] = vector.copy()

            # Add to hash tables
            for table_idx in range(self.config.num_tables):
                hash_key = self._hash_vector(vector, table_idx)
                self._tables[table_idx][hash_key].add(vector_id)

            self._size = len(self._vectors)
            logger.debug("Added vector to LSH index", vector_id=str(vector_id))

    async def add_batch(self, vectors: list[tuple[UUID, np.ndarray]]) -> None:
        """Add multiple vectors efficiently."""
        async with self._lock.write():
            for vector_id, vector in vectors:
                if vector.shape[0] != self.dimension:
                    raise ValueError(f"Vector dimension {vector.shape[0]} != index dimension {self.dimension}")

                # Store vector
                self._vectors[vector_id] = vector.copy()

                # Add to hash tables
                for table_idx in range(self.config.num_tables):
                    hash_key = self._hash_vector(vector, table_idx)
                    self._tables[table_idx][hash_key].add(vector_id)

            self._size = len(self._vectors)
            logger.info(f"Added {len(vectors)} vectors to LSH index")

    async def search(
        self,
        query_vector: np.ndarray,
        k: int,
        filter_ids: Optional[list[UUID]] = None
    ) -> list[tuple[UUID, float]]:
        """Search for k nearest neighbors using LSH."""
        if query_vector.shape[0] != self.dimension:
            raise ValueError(f"Query dimension {query_vector.shape[0]} != index dimension {self.dimension}")

        async with self._lock.read():
            # Get candidate set from all tables
            candidates: set[UUID] = set()

            for table_idx in range(self.config.num_tables):
                hash_key = self._hash_vector(query_vector, table_idx)
                if hash_key in self._tables[table_idx]:
                    candidates.update(self._tables[table_idx][hash_key])

            # Apply filter if provided
            if filter_ids is not None:
                filter_set = set(filter_ids)
                candidates = candidates.intersection(filter_set)

            # Compute exact distances for candidates
            distances = []
            for candidate_id in candidates:
                if candidate_id in self._vectors:
                    distance = self._compute_distance(query_vector, self._vectors[candidate_id])
                    distances.append((candidate_id, distance))

            # Sort by distance and return top k
            distances.sort(key=lambda x: x[1])
            return distances[:k]

    async def remove(self, vector_id: UUID) -> bool:
        """Remove a vector from the index."""
        async with self._lock.write():
            if vector_id not in self._vectors:
                return False

            vector = self._vectors[vector_id]

            # Remove from hash tables
            for table_idx in range(self.config.num_tables):
                hash_key = self._hash_vector(vector, table_idx)
                if hash_key in self._tables[table_idx]:
                    self._tables[table_idx][hash_key].discard(vector_id)
                    # Clean up empty buckets
                    if not self._tables[table_idx][hash_key]:
                        del self._tables[table_idx][hash_key]

            # Remove vector
            del self._vectors[vector_id]
            self._size = len(self._vectors)

            logger.debug("Removed vector from LSH index", vector_id=str(vector_id))
            return True

    async def clear(self) -> None:
        """Clear all vectors from the index."""
        async with self._lock.write():
            self._vectors.clear()
            for table in self._tables:
                table.clear()
            self._size = 0
            logger.info("Cleared LSH index")
