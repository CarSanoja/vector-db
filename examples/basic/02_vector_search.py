#!/usr/bin/env python3
"""
Basic example: Adding chunks and performing vector search.
"""

import asyncio
import numpy as np
from uuid import uuid4

from src.infrastructure.repositories.in_memory import (
    InMemoryLibraryRepository,
    InMemoryChunkRepository
)
from src.services.library_service import LibraryService
from src.services.chunk_service import ChunkService
from src.services.search_service import SearchService
from src.domain.entities.library import Library, IndexType
from src.domain.entities.chunk import Chunk


async def create_sample_embeddings(dimension: int, count: int):
    """Create sample embeddings with some structure."""
    # Create clusters of embeddings
    clusters = 3
    embeddings = []
    
    for i in range(count):
        cluster = i % clusters
        # Base vector for cluster
        base = np.random.randn(dimension) * 0.1
        # Make clusters distinguishable (but ensure we don't exceed dimension)
        cluster_start = min(cluster * 10, dimension - 10)
        cluster_end = min(cluster_start + 10, dimension)
        base[cluster_start:cluster_end] += 1.0
        
        # Add noise
        vec = base + np.random.randn(dimension) * 0.3
        # Normalize
        vec = vec / np.linalg.norm(vec)
        embeddings.append(vec.astype(np.float32))
    
    return embeddings


async def main():
    """Demonstrate vector search capabilities."""
    print("=== Vector Search Example ===\n")
    
    # Initialize repositories
    library_repo = InMemoryLibraryRepository()
    chunk_repo = InMemoryChunkRepository()
    
    # Initialize services in correct order
    # 1. LibraryService first (no dependencies on other services)
    library_service = LibraryService(library_repo)
    
    # 2. ChunkService needs LibraryService
    chunk_service = ChunkService(chunk_repo, library_service)
    
    # 3. SearchService needs LibraryService
    search_service = SearchService(chunk_repo, library_service)
    
    # Create a library
    library = await library_service.create_library(
        name="Search Demo Library",
        dimension=128,
        index_type=IndexType.HNSW,
        description="Library for search demonstration"
    )
    print(f"Created library: {library.name}\n")
    
    # Generate sample data
    num_chunks = 100
    embeddings = await create_sample_embeddings(library.dimension, num_chunks)
    
    # Add chunks with metadata
    print(f"Adding {num_chunks} chunks...")
    chunks = []
    for i, embedding in enumerate(embeddings):
        chunk = await chunk_service.create_chunk(
            library_id=library.id,
            content=f"This is sample document chunk {i}",
            embedding=embedding.tolist(),
            metadata={
                "doc_id": f"doc_{i // 10}",
                "chunk_index": i,
                "category": f"cluster_{i % 3}",
                "importance": float(np.random.rand())
            }
        )
        chunks.append(chunk)
    
    print(f"Added {len(chunks)} chunks\n")
    
    # Build index
    print("Building search index...")
    await library_service.build_index(library.id)
    
    # Perform searches
    print("\n=== Performing Searches ===\n")
    
    # Search 1: Find similar to first chunk
    query_embedding = embeddings[0]
    results = await search_service.search(
        library_id=library.id,
        embedding=query_embedding.tolist(),
        k=5
    )
    
    print("Search 1: Similar to first chunk")
    for i, result in enumerate(results):
        print(f"  {i+1}. Chunk {result.metadata.get('chunk_index', 'N/A')} from {result.metadata['doc_id']}")
        print(f"     Distance: {result.distance:.4f}")
        print(f"     Category: {result.metadata['category']}")
    
    # Search 2: With metadata filter
    print("\n\nSearch 2: Filter by category")
    filtered_results = await search_service.search(
        library_id=library.id,
        embedding=embeddings[15].tolist(),
        k=5,
        metadata_filters={"category": "cluster_0"}
    )
    
    for i, result in enumerate(filtered_results):
        print(f"  {i+1}. {result.content}")
        print(f"     Category: {result.metadata['category']}")
        print(f"     Distance: {result.distance:.4f}")


if __name__ == "__main__":
    asyncio.run(main())
