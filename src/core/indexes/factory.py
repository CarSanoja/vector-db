"""Factory for creating vector indexes."""
from typing import Union

from src.domain.entities.library import IndexType
from .base import VectorIndex, IndexConfig
from .lsh import LSHIndex, LSHConfig
from .hnsw import HNSWIndex, HNSWConfig
from .kdtree import KDTreeIndex, KDTreeConfig
from src.core.config import settings


class IndexFactory:
    """Factory for creating vector index instances."""
    
    @staticmethod
    def create_index(
        index_type: IndexType,
        dimension: int,
        **kwargs
    ) -> VectorIndex:
        """Create a vector index based on type and configuration."""
        if index_type == IndexType.LSH:
            config = LSHConfig(
                dimension=dimension,
                num_tables=kwargs.get("num_tables", settings.lsh_tables),
                key_size=kwargs.get("key_size", settings.lsh_key_size),
                metric=kwargs.get("metric", "euclidean")
            )
            return LSHIndex(config)
        
        elif index_type == IndexType.HNSW:
            config = HNSWConfig(
                dimension=dimension,
                M=kwargs.get("M", settings.hnsw_m),
                ef_construction=kwargs.get("ef_construction", settings.hnsw_ef_construction),
                metric=kwargs.get("metric", "euclidean")
            )
            return HNSWIndex(config)
        
        elif index_type == IndexType.KD_TREE:
            config = KDTreeConfig(
                dimension=dimension,
                projection_dim=kwargs.get("projection_dim", min(dimension // 2, 32)),
                leaf_size=kwargs.get("leaf_size", 40),
                metric=kwargs.get("metric", "euclidean")
            )
            return KDTreeIndex(config)
        
        else:
            raise ValueError(f"Unknown index type: {index_type}")
    
    @staticmethod
    def get_default_config(index_type: IndexType, dimension: int) -> IndexConfig:
        """Get default configuration for an index type."""
        if index_type == IndexType.LSH:
            return LSHConfig(
                dimension=dimension,
                num_tables=settings.lsh_tables,
                key_size=settings.lsh_key_size
            )
        elif index_type == IndexType.HNSW:
            return HNSWConfig(
                dimension=dimension,
                M=settings.hnsw_m,
                ef_construction=settings.hnsw_ef_construction
            )
        elif index_type == IndexType.KD_TREE:
            return KDTreeConfig(
                dimension=dimension,
                projection_dim=min(dimension // 2, 32),
                leaf_size=40
            )
        else:
            raise ValueError(f"Unknown index type: {index_type}")
