#!/usr/bin/env python3
"""
Basic example: Creating a vector library with different index types.
"""

import asyncio

from src.domain.entities.library import IndexType
from src.infrastructure.repositories.in_memory import InMemoryLibraryRepository
from src.services.library_service.service import LibraryService


async def main():
    """Create libraries with different index types."""
    print("=== Creating Vector Libraries ===\n")

    repo = InMemoryLibraryRepository()
    service = LibraryService(repo)

    index_types = [
        (IndexType.LSH, 128, "Fast approximate search using LSH"),
        (IndexType.HNSW, 256, "High accuracy with HNSW graphs"),
        (IndexType.KD_TREE, 64, "Exact search with KD-Tree")
    ]

    for index_type, dimension, description in index_types:
        library = await service.create_library(
            name=f"Example {index_type.value} Library",
            dimension=dimension,
            index_type=index_type,
            description=description,
            metadata={
                "created_by": "example_script",
                "purpose": "demonstration"
            }
        )

        print("Created library:")
        print(f"  ID: {library.id}")
        print(f"  Name: {library.name}")
        print(f"  Type: {library.index_type.value}")
        print(f"  Dimension: {library.dimension}")
        print(f"  Description: {library.description}")
        print()

    print("\nAll libraries:")
    libraries = await service.list_libraries()
    for lib in libraries:
        print(f"- {lib.name} ({lib.index_type.value}, {lib.dimension}D)")


if __name__ == "__main__":
    asyncio.run(main())
