from typing import List, Tuple, Optional, Dict, Set, Union
from uuid import UUID
from dataclasses import dataclass
import asyncio
import heapq

import numpy as np

from .base import VectorIndex, IndexConfig
from src.infrastructure.locks import ReadWriteLock
from src.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class KDTreeConfig(IndexConfig):
    """Configuration for KD-Tree index."""
    leaf_size: int = 40  # Maximum points in a leaf
    projection_dim: int = 16  # Dimension after random projection
    seed: int = 42


@dataclass
class KDNode:
    """Node in the KD-Tree."""
    # Leaf node attributes
    is_leaf: bool = True
    vector_ids: List[UUID] = None
    vectors: np.ndarray = None
    
    # Internal node attributes
    split_dim: int = -1
    split_value: float = 0.0
    left: 'KDNode' = None
    right: 'KDNode' = None
    
    # Bounding box for pruning
    min_bound: np.ndarray = None
    max_bound: np.ndarray = None


class KDTreeIndex(VectorIndex):
    """KD-Tree implementation with random projections for high dimensions."""
    
    def __init__(self, config: KDTreeConfig):
        super().__init__(config)
        self.config: KDTreeConfig = config
        self._lock = ReadWriteLock()
        
        # Random projection matrix
        np.random.seed(config.seed)
        self._projection_matrix = np.random.randn(config.projection_dim, config.dimension)
        self._projection_matrix /= np.linalg.norm(self._projection_matrix, axis=1, keepdims=True)
        
        # Storage
        self._vectors: Dict[UUID, np.ndarray] = {}
        self._projected_vectors: Dict[UUID, np.ndarray] = {}
        self._root: Optional[KDNode] = None
        
        logger.info(
            f"Initialized KD-Tree index",
            dimension=config.dimension,
            projection_dim=config.projection_dim,
            leaf_size=config.leaf_size
        )
    
    def _project_vector(self, vector: np.ndarray) -> np.ndarray:
        """Project high-dimensional vector to lower dimension."""
        return np.dot(self._projection_matrix, vector)
    
    async def add(self, vector_id: UUID, vector: np.ndarray) -> None:
        """Add a vector to the index."""
        if vector.shape[0] != self.dimension:
            raise ValueError(f"Vector dimension {vector.shape[0]} != index dimension {self.dimension}")
        
        async with self._lock.write():
            # Store original and projected vectors
            self._vectors[vector_id] = vector.copy()
            self._projected_vectors[vector_id] = self._project_vector(vector)
            self._size = len(self._vectors)
            
            # Rebuild tree (simple approach - in production, use incremental insertion)
            await self._rebuild_tree()
            
            logger.debug(f"Added vector to KD-Tree index", vector_id=str(vector_id))
    
    async def add_batch(self, vectors: List[Tuple[UUID, np.ndarray]]) -> None:
        """Add multiple vectors efficiently."""
        async with self._lock.write():
            for vector_id, vector in vectors:
                if vector.shape[0] != self.dimension:
                    raise ValueError(f"Vector dimension {vector.shape[0]} != index dimension {self.dimension}")
                
                self._vectors[vector_id] = vector.copy()
                self._projected_vectors[vector_id] = self._project_vector(vector)
            
            self._size = len(self._vectors)
            
            # Rebuild tree with all vectors
            await self._rebuild_tree()
            
            logger.info(f"Added {len(vectors)} vectors to KD-Tree index")
    
    async def _rebuild_tree(self) -> None:
        """Rebuild the entire KD-Tree."""
        if not self._projected_vectors:
            self._root = None
            return
        
        # Prepare data for tree construction
        vector_ids = list(self._projected_vectors.keys())
        vectors = np.array([self._projected_vectors[vid] for vid in vector_ids])
        
        # Build tree recursively
        self._root = self._build_tree(vector_ids, vectors, 0)
    
    def _build_tree(
        self, 
        vector_ids: List[UUID], 
        vectors: np.ndarray, 
        depth: int
    ) -> KDNode:
        """Recursively build KD-Tree."""
        n_points = len(vector_ids)
        
        # Create leaf node if few enough points
        if n_points <= self.config.leaf_size:
            node = KDNode(
                is_leaf=True,
                vector_ids=vector_ids.copy(),
                vectors=vectors.copy()
            )
            # Calculate bounds
            node.min_bound = np.min(vectors, axis=0)
            node.max_bound = np.max(vectors, axis=0)
            return node
        
        # Choose split dimension (cycle through dimensions)
        split_dim = depth % self.config.projection_dim
        
        # Find median along split dimension
        indices = np.argsort(vectors[:, split_dim])
        median_idx = n_points // 2
        split_value = vectors[indices[median_idx], split_dim]
        
        # Partition data
        left_mask = vectors[:, split_dim] < split_value
        right_mask = ~left_mask
        
        # Handle edge case where all points have same value
        if np.sum(left_mask) == 0 or np.sum(right_mask) == 0:
            # Force split in middle
            left_mask[:median_idx] = True
            left_mask[median_idx:] = False
            right_mask = ~left_mask
        
        # Create internal node
        node = KDNode(
            is_leaf=False,
            split_dim=split_dim,
            split_value=split_value
        )
        
        # Recursively build children
        left_ids = [vector_ids[i] for i in range(n_points) if left_mask[i]]
        left_vectors = vectors[left_mask]
        node.left = self._build_tree(left_ids, left_vectors, depth + 1)
        
        right_ids = [vector_ids[i] for i in range(n_points) if right_mask[i]]
        right_vectors = vectors[right_mask]
        node.right = self._build_tree(right_ids, right_vectors, depth + 1)
        
        # Calculate bounds from children
        node.min_bound = np.minimum(node.left.min_bound, node.right.min_bound)
        node.max_bound = np.maximum(node.left.max_bound, node.right.max_bound)
        
        return node
    
    async def search(
        self, 
        query_vector: np.ndarray, 
        k: int,
        filter_ids: Optional[List[UUID]] = None
    ) -> List[Tuple[UUID, float]]:
        """Search for k nearest neighbors."""
        if query_vector.shape[0] != self.dimension:
            raise ValueError(f"Query dimension {query_vector.shape[0]} != index dimension {self.dimension}")
        
        async with self._lock.read():
            if self._root is None:
                return []
            
            # Project query vector
            projected_query = self._project_vector(query_vector)
            
            # Priority queue for nearest neighbors (max heap)
            nearest = []
            
            # Priority queue for nodes to explore (min heap by distance to bounding box)
            to_explore = [(0.0, self._root)]
            
            while to_explore and (len(nearest) < k or to_explore[0][0] < -nearest[0][0]):
                _, node = heapq.heappop(to_explore)
                
                if node.is_leaf:
                    # Check all points in leaf
                    for i, vector_id in enumerate(node.vector_ids):
                        # Apply filter if provided
                        if filter_ids is not None and vector_id not in filter_ids:
                            continue
                        
                        # Compute exact distance using original vectors
                        distance = self._compute_distance(query_vector, self._vectors[vector_id])
                        
                        if len(nearest) < k:
                            heapq.heappush(nearest, (-distance, vector_id))
                        elif distance < -nearest[0][0]:
                            heapq.heapreplace(nearest, (-distance, vector_id))
                else:
                    # Internal node - explore children
                    # Determine which child to explore first
                    if projected_query[node.split_dim] < node.split_value:
                        first_child, second_child = node.left, node.right
                    else:
                        first_child, second_child = node.right, node.left
                    
                    # Always explore the closer child
                    first_dist = self._min_distance_to_box(projected_query, first_child)
                    heapq.heappush(to_explore, (first_dist, first_child))
                    
                    # Only explore second child if it could contain closer points
                    if len(nearest) < k or self._min_distance_to_box(projected_query, second_child) < -nearest[0][0]:
                        second_dist = self._min_distance_to_box(projected_query, second_child)
                        heapq.heappush(to_explore, (second_dist, second_child))
            
            # Convert to desired format and sort by distance
            result = [(vector_id, -distance) for distance, vector_id in nearest]
            result.sort(key=lambda x: x[1])
            return result
    
    def _min_distance_to_box(self, point: np.ndarray, node: KDNode) -> float:
        """Calculate minimum distance from point to node's bounding box."""
        # For each dimension, calculate distance to nearest edge of box
        distances = np.zeros_like(point)
        
        for i in range(len(point)):
            if point[i] < node.min_bound[i]:
                distances[i] = node.min_bound[i] - point[i]
            elif point[i] > node.max_bound[i]:
                distances[i] = point[i] - node.max_bound[i]
        
        return np.linalg.norm(distances)
    
    async def remove(self, vector_id: UUID) -> bool:
        """Remove a vector from the index."""
        async with self._lock.write():
            if vector_id not in self._vectors:
                return False
            
            # Remove from storage
            del self._vectors[vector_id]
            del self._projected_vectors[vector_id]
            self._size = len(self._vectors)
            
            # Rebuild tree (simple approach - in production, use lazy deletion)
            await self._rebuild_tree()
            
            logger.debug(f"Removed vector from KD-Tree index", vector_id=str(vector_id))
            return True
    
    async def clear(self) -> None:
        """Clear all vectors from the index."""
        async with self._lock.write():
            self._vectors.clear()
            self._projected_vectors.clear()
            self._root = None
            self._size = 0
            logger.info("Cleared KD-Tree index")