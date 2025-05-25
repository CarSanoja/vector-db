import pytest
import numpy as np
from uuid import uuid4
import asyncio

from src.core.indexes import (
    LSHIndex, LSHConfig,
    HNSWIndex, HNSWConfig,
    KDTreeIndex, KDTreeConfig
)


class TestLSHIndex:
    """Test cases for LSH index."""
    
    @pytest.fixture
    def config(self):
        """Create LSH configuration."""
        return LSHConfig(
            dimension=8,
            num_tables=5,
            key_size=4,
            metric="euclidean"
        )
    
    @pytest.fixture
    def index(self, config):
        """Create LSH index."""
        return LSHIndex(config)
    
    @pytest.fixture
    def sample_vectors(self):
        """Create sample vectors for testing."""
        np.random.seed(42)
        vectors = []
        for i in range(10):
            vec_id = uuid4()
            vector = np.random.randn(8).astype(np.float32)
            vectors.append((vec_id, vector))
        return vectors
    
    @pytest.mark.asyncio
    async def test_add_and_search(self, index, sample_vectors):
        """Test adding vectors and searching."""
        # Add vectors
        for vec_id, vector in sample_vectors[:5]:
            await index.add(vec_id, vector)
        
        assert index.size == 5
        
        # Search for nearest neighbors
        query = sample_vectors[0][1]  # Use first vector as query
        results = await index.search(query, k=3)
        
        assert len(results) <= 3
        assert results[0][0] == sample_vectors[0][0]  # Should find itself
        assert results[0][1] == 0.0  # Distance to itself should be 0
    
    @pytest.mark.asyncio
    async def test_batch_add(self, index, sample_vectors):
        """Test batch addition of vectors."""
        await index.add_batch(sample_vectors[:5])
        assert index.size == 5
        
        # Verify all vectors are searchable
        for vec_id, vector in sample_vectors[:5]:
            results = await index.search(vector, k=1)
            assert len(results) == 1
            assert results[0][0] == vec_id
    
    @pytest.mark.asyncio
    async def test_remove(self, index, sample_vectors):
        """Test removing vectors."""
        # Add vectors
        await index.add_batch(sample_vectors[:3])
        assert index.size == 3
        
        # Remove one
        removed = await index.remove(sample_vectors[1][0])
        assert removed is True
        assert index.size == 2
        
        # Try to remove non-existent
        removed = await index.remove(uuid4())
        assert removed is False
    
    @pytest.mark.asyncio
    async def test_cosine_similarity(self):
        """Test LSH with cosine similarity metric."""
        config = LSHConfig(
            dimension=8,
            num_tables=5,
            key_size=4,
            metric="cosine"
        )
        index = LSHIndex(config)
        
        # Create normalized vectors
        vec1_id = uuid4()
        vec1 = np.array([1, 0, 0, 0, 0, 0, 0, 0], dtype=np.float32)
        
        vec2_id = uuid4()
        vec2 = np.array([0.8, 0.6, 0, 0, 0, 0, 0, 0], dtype=np.float32)
        vec2 = vec2 / np.linalg.norm(vec2)
        
        await index.add(vec1_id, vec1)
        await index.add(vec2_id, vec2)
        
        # Search - vec2 should be close to vec1 in cosine distance
        results = await index.search(vec1, k=2)
        assert len(results) == 2
        assert results[0][0] == vec1_id  # Exact match first


class TestHNSWIndex:
    """Test cases for HNSW index."""
    
    @pytest.fixture
    def config(self):
        """Create HNSW configuration."""
        return HNSWConfig(
            dimension=8,
            M=4,
            ef_construction=20,
            metric="euclidean"
        )
    
    @pytest.fixture
    def index(self, config):
        """Create HNSW index."""
        return HNSWIndex(config)
    
    @pytest.fixture
    def sample_vectors(self):
        """Create sample vectors for testing."""
        np.random.seed(42)
        vectors = []
        for i in range(20):
            vec_id = uuid4()
            vector = np.random.randn(8).astype(np.float32)
            vectors.append((vec_id, vector))
        return vectors
    
    @pytest.mark.asyncio
    async def test_add_and_search(self, index, sample_vectors):
        """Test adding vectors and searching in HNSW."""
        # Add vectors
        for vec_id, vector in sample_vectors[:10]:
            await index.add(vec_id, vector)
        
        assert index.size == 10
        
        # Search for nearest neighbors
        query = sample_vectors[5][1]
        results = await index.search(query, k=5)
        
        assert len(results) <= 5
        assert results[0][0] == sample_vectors[5][0]  # Should find itself
        
        # Verify results are sorted by distance
        distances = [r[1] for r in results]
        assert distances == sorted(distances)
    
    @pytest.mark.asyncio
    async def test_hierarchical_structure(self, index, sample_vectors):
        """Test that HNSW builds hierarchical structure."""
        # Add enough vectors to create multiple layers
        await index.add_batch(sample_vectors)
        
        # Check that some nodes have multiple layers
        multi_layer_nodes = sum(
            1 for node in index._nodes.values() 
            if node.level > 0
        )
        assert multi_layer_nodes > 0
    
    @pytest.mark.asyncio
    async def test_connectivity(self, index, sample_vectors):
        """Test that all nodes are connected."""
        # Add vectors
        await index.add_batch(sample_vectors[:10])
        
        # Check connectivity at layer 0
        for node in index._nodes.values():
            assert len(node.neighbors[0]) > 0  # Each node should have neighbors
    
    @pytest.mark.asyncio
    async def test_search_with_filter(self, index, sample_vectors):
        """Test searching with ID filter."""
        # Add vectors
        await index.add_batch(sample_vectors[:10])
        
        # Search with filter
        filter_ids = [sample_vectors[i][0] for i in [2, 4, 6, 8]]
        query = sample_vectors[4][1]
        
        results = await index.search(query, k=5, filter_ids=filter_ids)
        
        # All results should be in filter set
        result_ids = [r[0] for r in results]
        assert all(rid in filter_ids for rid in result_ids)
        assert sample_vectors[4][0] in result_ids


class TestKDTreeIndex:
    """Test cases for KD-Tree index."""
    
    @pytest.fixture
    def config(self):
        """Create KD-Tree configuration."""
        return KDTreeConfig(
            dimension=16,
            projection_dim=8,
            leaf_size=5,
            metric="euclidean"
        )
    
    @pytest.fixture
    def index(self, config):
        """Create KD-Tree index."""
        return KDTreeIndex(config)
    
    @pytest.fixture
    def sample_vectors(self):
        """Create sample vectors for testing."""
        np.random.seed(42)
        vectors = []
        for i in range(20):
            vec_id = uuid4()
            vector = np.random.randn(16).astype(np.float32)
            vectors.append((vec_id, vector))
        return vectors
    
    @pytest.mark.asyncio
    async def test_add_and_search(self, index, sample_vectors):
        """Test adding vectors and searching in KD-Tree."""
        # Add vectors
        await index.add_batch(sample_vectors[:15])
        assert index.size == 15
        
        # Search for nearest neighbors
        query = sample_vectors[7][1]
        results = await index.search(query, k=5)
        
        assert len(results) <= 5
        assert results[0][0] == sample_vectors[7][0]  # Should find itself
        
        # Verify results are sorted by distance
        distances = [r[1] for r in results]
        assert distances == sorted(distances)
    
    @pytest.mark.asyncio
    async def test_tree_structure(self, index, sample_vectors):
        """Test that KD-Tree builds proper tree structure."""
        # Add vectors
        await index.add_batch(sample_vectors)
        
        # Check tree properties
        assert index._root is not None
        assert not index._root.is_leaf  # Root should be internal node with enough data
        
        # Check bounds are set
        assert index._root.min_bound is not None
        assert index._root.max_bound is not None
    
    @pytest.mark.asyncio
    async def test_random_projection(self, index):
        """Test random projection reduces dimensionality."""
        # Create high-dimensional vector
        vec = np.random.randn(16)
        projected = index._project_vector(vec)
        
        assert projected.shape[0] == 8  # Reduced to projection_dim
    
    @pytest.mark.asyncio
    async def test_incremental_add(self, index, sample_vectors):
        """Test adding vectors incrementally."""
        # Add vectors one by one
        for vec_id, vector in sample_vectors[:5]:
            await index.add(vec_id, vector)
            
            # Verify tree is rebuilt
            results = await index.search(vector, k=1)
            assert results[0][0] == vec_id
    
    @pytest.mark.asyncio
    async def test_empty_index(self, index):
        """Test searching in empty index."""
        query = np.random.randn(16)
        results = await index.search(query, k=5)
        assert len(results) == 0


class TestIndexComparison:
    """Compare different index implementations."""
    
    @pytest.fixture
    def vectors(self):
        """Create test vectors."""
        np.random.seed(42)
        vectors = []
        for i in range(100):
            vec_id = uuid4()
            vector = np.random.randn(32).astype(np.float32)
            vectors.append((vec_id, vector))
        return vectors
    
    @pytest.mark.asyncio
    async def test_accuracy_comparison(self, vectors):
        """Compare search accuracy across indexes."""
        # Create indexes
        lsh = LSHIndex(LSHConfig(dimension=32, num_tables=10, key_size=8))
        hnsw = HNSWIndex(HNSWConfig(dimension=32, M=8, ef_construction=50))
        kdtree = KDTreeIndex(KDTreeConfig(dimension=32, projection_dim=16, leaf_size=10))
        
        # Add same vectors to all indexes
        test_vectors = vectors[:50]
        for index in [lsh, hnsw, kdtree]:
            await index.add_batch(test_vectors)
        
        # Create a new query vector that's NOT in the index
        np.random.seed(123)
        query_vector = np.random.randn(32).astype(np.float32)
        k = 10
        
        lsh_results = await lsh.search(query_vector, k=k)
        hnsw_results = await hnsw.search(query_vector, k=k)
        kdtree_results = await kdtree.search(query_vector, k=k)
        
        # All should return some results
        assert len(lsh_results) > 0, "LSH returned no results"
        assert len(hnsw_results) > 0, "HNSW returned no results"
        assert len(kdtree_results) > 0, "KD-Tree returned no results"
        
        # Results should be sorted by distance
        for name, results in [("LSH", lsh_results), ("HNSW", hnsw_results), ("KD-Tree", kdtree_results)]:
            distances = [r[1] for r in results]
            assert distances == sorted(distances), f"{name} results not sorted by distance"
        
        # Test with a vector that IS in the index
        test_idx = 10
        test_id = test_vectors[test_idx][0]
        test_vector = test_vectors[test_idx][1]
        
        lsh_results2 = await lsh.search(test_vector, k=5)
        hnsw_results2 = await hnsw.search(test_vector, k=5)
        kdtree_results2 = await kdtree.search(test_vector, k=5)
        
        # Check if the vector finds itself (or at least very close vectors)
        lsh_min_dist = min(r[1] for r in lsh_results2) if lsh_results2 else float('inf')
        hnsw_min_dist = min(r[1] for r in hnsw_results2) if hnsw_results2 else float('inf')
        kdtree_min_dist = min(r[1] for r in kdtree_results2) if kdtree_results2 else float('inf')
        
        # All should find very close vectors (distance < 0.1)
        assert lsh_min_dist < 0.1, f"LSH min distance too large: {lsh_min_dist}"
        assert hnsw_min_dist < 0.1, f"HNSW min distance too large: {hnsw_min_dist}"
        assert kdtree_min_dist < 0.1, f"KD-Tree min distance too large: {kdtree_min_dist}"
        
        # Basic sanity check: all indexes should work and return sorted results
        print(f"\nAccuracy test passed:")
        print(f"  LSH: {len(lsh_results)} results, min dist for self-search: {lsh_min_dist:.6f}")
        print(f"  HNSW: {len(hnsw_results)} results, min dist for self-search: {hnsw_min_dist:.6f}")
        print(f"  KD-Tree: {len(kdtree_results)} results, min dist for self-search: {kdtree_min_dist:.6f}")