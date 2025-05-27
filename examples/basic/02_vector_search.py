#!/usr/bin/env python3
"""
Basic example: Adding chunks and performing vector search.
"""

import asyncio

import numpy as np

from src.domain.entities.library import IndexType
from src.infrastructure.repositories.in_memory import (
    InMemoryChunkRepository,
    InMemoryLibraryRepository,
)
from src.services.chunk_service import ChunkService
from src.services.library_service import LibraryService
from src.services.search_service import SearchService


async def create_sample_embeddings(dimension: int, count: int):
    """Create sample embeddings with some structure."""
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

    library_repo = InMemoryLibraryRepository()
    chunk_repo = InMemoryChunkRepository()

    library_service = LibraryService(library_repo)

    chunk_service = ChunkService(chunk_repo, library_service)

    search_service = SearchService(chunk_repo, library_service)

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

    print("Building search index...")
    await library_service.build_index(library.id)

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
