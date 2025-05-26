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
from src.services import LibraryService, ChunkService, SearchService
from src.domain.entities.library import Library, IndexType
from src.domain.entities.chunk import Chunk
from src.core.indexes.factory import IndexFactory


async def create_sample_embeddings(dimension: int, count: int):
    """Create sample embeddings with some structure."""
    # Create clusters of embeddings
    clusters = 3
    embeddings = []
    
    for i in range(count):
        cluster = i % clusters
        # Base vector for cluster
        base = np.random.randn(dimension) * 0.1
        base[cluster * 10:(cluster + 1) * 10] += 1.0  # Make clusters distinguishable
        
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
    
    # Initialize services
    library_service = LibraryService(library_repo)
    chunk_service = ChunkService(chunk_repo, library_repo)
    search_service = SearchService(chunk_repo, library_repo, IndexFactory())
    
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
                "chunk_index": i % 10,
                "category": f"cluster_{i % 3}",
                "importance": np.random.rand()
            }
        )
        chunks.append(chunk)
    
    print(f"Added {len(chunks)} chunks\n")
    
    # Build index
    print("Building search index...")
    await search_service.build_index(library.id)
    
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
        print(f"  {i+1}. Chunk {result.chunk.chunk_index} from {result.chunk.metadata['doc_id']}")
        print(f"     Distance: {result.distance:.4f}")
        print(f"     Category: {result.chunk.metadata['category']}")
    
    # Search 2: With metadata filter
    print("\n\nSearch 2: Filter by category")
    filtered_results = await search_service.search(
        library_id=library.id,
        embedding=embeddings[15].tolist(),
        k=5,
        metadata_filters={"category": "cluster_0"}
    )
    
    for i, result in enumerate(filtered_results):
        print(f"  {i+1}. {result.chunk.content}")
        print(f"     Category: {result.chunk.metadata['category']}")
        print(f"     Distance: {result.distance:.4f}")


if __name__ == "__main__":
    asyncio.run(main())
