import heapq
import random
from dataclasses import dataclass, field
from typing import Optional, dict, list, set, tuple
from uuid import UUID

import numpy as np

from src.core.logging import get_logger
from src.infrastructure.locks import ReadWriteLock

from .base import IndexConfig, VectorIndex

logger = get_logger(__name__)


@dataclass
class HNSWConfig(IndexConfig):
    """Configuration for HNSW index."""
    M: int = 16  # Number of bi-directional links per node
    ef_construction: int = 200  # Size of dynamic candidate list
    max_M: int = field(init=False)  # Maximum number of connections
    max_M0: int = field(init=False)  # Maximum number of connections for layer 0
    ml: float = field(init=False)  # Normalization factor for level assignment
    seed: int = 42

    def __post_init__(self):
        self.max_M = self.M
        self.max_M0 = self.M * 2
        self.ml = 1 / np.log(2.0)


@dataclass
class HNSWNode:
    """Node in the HNSW graph."""
    vector_id: UUID
    vector: np.ndarray
    level: int
    neighbors: dict[int, set[UUID]] = field(default_factory=dict)

    def __post_init__(self):
        # Initialize neighbor sets for each level
        for layer in range(self.level + 1):
            if layer not in self.neighbors:
                self.neighbors[layer] = set()


class HNSWIndex(VectorIndex):
    """Hierarchical Navigable Small World index implementation."""

    def __init__(self, config: HNSWConfig):
        super().__init__(config)
        self.config: HNSWConfig = config
        self._lock = ReadWriteLock()

        # Graph structure
        self._nodes: dict[UUID, HNSWNode] = {}
        self._entry_point: Optional[UUID] = None

        # Random number generator
        self._rng = random.Random(config.seed)

        logger.info(
            "Initialized HNSW index",
            dimension=config.dimension,
            M=config.M,
            ef_construction=config.ef_construction
        )

    def _get_random_level(self) -> int:
        """Select level for a new node."""
        level = 0
        while self._rng.random() < 0.5:
            level += 1
        return level

    async def add(self, vector_id: UUID, vector: np.ndarray) -> None:
        """Add a vector to the index."""
        if vector.shape[0] != self.dimension:
            raise ValueError(f"Vector dimension {vector.shape[0]} != index dimension {self.dimension}")

        async with self._lock.write():
            await self._add_internal(vector_id, vector)

    async def _add_internal(self, vector_id: UUID, vector: np.ndarray) -> None:
        """Internal method to add a vector (assumes lock is held)."""
        if vector_id in self._nodes:
            raise ValueError(f"Vector {vector_id} already exists in index")

        # Create new node
        level = self._get_random_level()
        node = HNSWNode(vector_id=vector_id, vector=vector.copy(), level=level)
        self._nodes[vector_id] = node
        self._size = len(self._nodes)

        # If first node, set as entry point
        if self._entry_point is None:
            self._entry_point = vector_id
            return

        # Find nearest neighbors at all layers
        self._search_layer(vector, self._entry_point, 1, 0)

        # Insert at all layers
        for lc in range(level + 1):
            candidates = []
            M = self.config.max_M if lc > 0 else self.config.max_M0

            # Find nearest neighbors at layer lc
            if lc == 0:
                # Use more extensive search at layer 0
                candidates = self._search_layer(vector, self._entry_point, self.config.ef_construction, 0)
            else:
                candidates = self._search_layer(vector, self._entry_point, M, lc)

            # Select M nearest neighbors
            M_nearest = self._get_nearest_from_candidates(candidates, M)

            # Add bidirectional links
            for neighbor_id, _ in M_nearest:
                node.neighbors[lc].add(neighbor_id)
                neighbor_node = self._nodes[neighbor_id]

                # Only add reverse link if neighbor has this layer
                if lc <= neighbor_node.level:
                    if lc not in neighbor_node.neighbors:
                        neighbor_node.neighbors[lc] = set()
                    neighbor_node.neighbors[lc].add(vector_id)

                    # Prune neighbor's connections if needed
                    max_neighbors = self.config.max_M if lc > 0 else self.config.max_M0
                    if len(neighbor_node.neighbors[lc]) > max_neighbors:
                        self._prune_connections(neighbor_id, lc, max_neighbors)

    def _search_layer(
        self,
        query: np.ndarray,
        entry_id: UUID,
        num_closest: int,
        layer: int
    ) -> list[tuple[UUID, float]]:
        """Search for nearest neighbors at a specific layer."""
        visited = set()
        candidates = []
        w = []

        # Initialize with entry point
        entry_dist = self._compute_distance(query, self._nodes[entry_id].vector)
        heapq.heappush(candidates, (-entry_dist, entry_id))
        heapq.heappush(w, (entry_dist, entry_id))
        visited.add(entry_id)

        while candidates:
            current_dist, current_id = heapq.heappop(candidates)
            current_dist = -current_dist

            # If this is farther than our worst nearest, we're done
            if current_dist > w[0][0]:
                break

            # Check neighbors
            current_node = self._nodes[current_id]
            if layer in current_node.neighbors and current_node.neighbors[layer]:
                for neighbor_id in current_node.neighbors[layer]:
                    if neighbor_id not in visited:
                        visited.add(neighbor_id)
                        neighbor_dist = self._compute_distance(query, self._nodes[neighbor_id].vector)

                        if neighbor_dist < w[0][0] or len(w) < num_closest:
                            heapq.heappush(candidates, (-neighbor_dist, neighbor_id))
                            heapq.heappush(w, (neighbor_dist, neighbor_id))

                            # Remove worst if we have too many
                            if len(w) > num_closest:
                                heapq.heappop(w)

        # Convert from (distance, id) to (id, distance) format
        return [(node_id, dist) for dist, node_id in w]

    def _get_nearest_from_candidates(
        self,
        candidates: list[tuple[UUID, float]],
        M: int
    ) -> list[tuple[UUID, float]]:
        """Select M nearest neighbors from candidates using heuristic."""
        # Sort by distance
        candidates.sort(key=lambda x: x[1])
        return candidates[:M]

    def _prune_connections(self, node_id: UUID, layer: int, max_neighbors: int) -> None:
        """Prune excess connections for a node."""
        node = self._nodes[node_id]
        neighbors = list(node.neighbors[layer])

        # Calculate distances to all neighbors
        neighbor_dists = []
        for neighbor_id in neighbors:
            dist = self._compute_distance(node.vector, self._nodes[neighbor_id].vector)
            neighbor_dists.append((neighbor_id, dist))

        # Sort by distance and keep only max_neighbors
        neighbor_dists.sort(key=lambda x: x[1])
        new_neighbors = set(n[0] for n in neighbor_dists[:max_neighbors])

        # Remove pruned connections
        for neighbor_id in neighbors:
            if neighbor_id not in new_neighbors:
                node.neighbors[layer].discard(neighbor_id)
                self._nodes[neighbor_id].neighbors[layer].discard(node_id)

    async def add_batch(self, vectors: list[tuple[UUID, np.ndarray]]) -> None:
        """Add multiple vectors efficiently."""
        async with self._lock.write():
            for vector_id, vector in vectors:
                await self._add_internal(vector_id, vector)
            logger.info(f"Added {len(vectors)} vectors to HNSW index")

    async def search(
        self,
        query_vector: np.ndarray,
        k: int,
        filter_ids: Optional[list[UUID]] = None
    ) -> list[tuple[UUID, float]]:
        """Search for k nearest neighbors."""
        if query_vector.shape[0] != self.dimension:
            raise ValueError(f"Query dimension {query_vector.shape[0]} != index dimension {self.dimension}")

        async with self._lock.read():
            if self._entry_point is None:
                return []

            # Start from entry point
            entry_node = self._nodes[self._entry_point]
            current_nearest = [(self._entry_point,
                              self._compute_distance(query_vector, entry_node.vector))]

            # Search from top layer to layer 0
            for layer in range(entry_node.level, -1, -1):
                current_nearest = self._search_layer(
                    query_vector,
                    current_nearest[0][0],  # Start from nearest found so far
                    1 if layer > 0 else max(self.config.ef_construction, k),
                    layer
                )

            # Apply filter if provided
            if filter_ids is not None:
                filter_set = set(filter_ids)
                current_nearest = [(id, dist) for id, dist in current_nearest if id in filter_set]

            # Sort and return top k
            current_nearest.sort(key=lambda x: x[1])
            return current_nearest[:k]

    async def remove(self, vector_id: UUID) -> bool:
        """Remove a vector from the index."""
        async with self._lock.write():
            if vector_id not in self._nodes:
                return False

            node = self._nodes[vector_id]

            # Remove all connections
            for layer in range(node.level + 1):
                for neighbor_id in node.neighbors.get(layer, set()).copy():
                    # Remove bidirectional link
                    self._nodes[neighbor_id].neighbors[layer].discard(vector_id)

            # Remove node
            del self._nodes[vector_id]
            self._size = len(self._nodes)

            # Update entry point if needed
            if vector_id == self._entry_point:
                self._entry_point = next(iter(self._nodes.keys())) if self._nodes else None

            logger.debug("Removed vector from HNSW index", vector_id=str(vector_id))
            return True

    async def clear(self) -> None:
        """Clear all vectors from the index."""
        async with self._lock.write():
            self._nodes.clear()
            self._entry_point = None
            self._size = 0
            logger.info("Cleared HNSW index")
