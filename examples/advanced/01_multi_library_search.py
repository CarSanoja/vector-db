#!/usr/bin/env python3
"""
Advanced example: Search across multiple libraries simultaneously.
"""

import asyncio
import numpy as np
from typing import List, Dict, Any
from uuid import uuid4

from src.infrastructure.repositories.in_memory import (
    InMemoryLibraryRepository,
    InMemoryChunkRepository
)
from src.services.library_service import LibraryService
from src.services.chunk_service import ChunkService
from src.services.search_service import SearchService
from src.domain.entities.library import Library, IndexType


async def create_themed_library(
    name: str,
    theme: str,
    library_service: LibraryService,
    chunk_service: ChunkService,
    dimension: int = 128
) -> Library:
    """Create a library with themed content."""
    
    # Create library
    library = await library_service.create_library(
        name=name,
        dimension=dimension,
        index_type=IndexType.HNSW,
        metadata={"theme": theme}
    )
    
    # Add themed chunks
    theme_contents = {
        "technology": [
            "Artificial intelligence is reshaping industries",
            "Cloud computing enables scalable solutions",
            "Blockchain technology ensures data integrity",
            "Quantum computing promises exponential speedup",
            "IoT devices connect the physical and digital worlds"
        ],
        "science": [
            "DNA sequencing reveals genetic mysteries",
            "Climate change requires urgent action",
            "Black holes bend spacetime around them",
            "Vaccines protect against infectious diseases",
            "Renewable energy sources reduce carbon emissions"
        ],
        "literature": [
            "Shakespeare's plays explore human nature",
            "Poetry captures emotions in verse",
            "Novels transport readers to new worlds",
            "Short stories pack meaning into brief narratives",
            "Classic literature endures through generations"
        ]
    }
    
    contents = theme_contents.get(theme, ["Generic content"] * 5)
    
    for i, content in enumerate(contents):
        # Generate embeddings with theme bias
        embedding = np.random.randn(dimension).astype(np.float32)
        
        # Add theme-specific signal (ensure we don't exceed dimension)
        if theme == "technology" and dimension >= 10:
            embedding[0:10] += 0.5
        elif theme == "science" and dimension >= 20:
            embedding[10:20] += 0.5
        elif theme == "literature" and dimension >= 30:
            embedding[20:30] += 0.5
            
        # Normalize
        embedding = embedding / np.linalg.norm(embedding)
        
        await chunk_service.create_chunk(
            library_id=library.id,
            content=content,
            embedding=embedding.tolist(),
            metadata={
                "theme": theme,
                "index": i
            }
        )
    
    return library


async def main():
    """Demonstrate multi-library search."""
    print("=== Multi-Library Search Example ===\n")
    
    # Initialize repositories
    library_repo = InMemoryLibraryRepository()
    chunk_repo = InMemoryChunkRepository()
    
    # Initialize services in correct order
    library_service = LibraryService(library_repo)
    chunk_service = ChunkService(chunk_repo, library_service)
    search_service = SearchService(chunk_repo, library_service)
    
    # Create themed libraries
    print("Creating themed libraries...")
    
    tech_lib = await create_themed_library(
        "Technology Library", "technology", 
        library_service, chunk_service
    )
    print(f"✓ Created {tech_lib.name}")
    
    science_lib = await create_themed_library(
        "Science Library", "science",
        library_service, chunk_service
    )
    print(f"✓ Created {science_lib.name}")
    
    lit_lib = await create_themed_library(
        "Literature Library", "literature",
        library_service, chunk_service
    )
    print(f"✓ Created {lit_lib.name}")
    
    # Build indexes
    print("\nBuilding indexes...")
    for lib in [tech_lib, science_lib, lit_lib]:
        await library_service.build_index(lib.id)
    
    # Perform multi-library searches
    print("\n=== Multi-Library Search Results ===\n")
    
    # Create query embeddings with different biases
    queries = [
        ("Technology-biased query", [0.5] * 10 + [0.0] * 118),
        ("Science-biased query", [0.0] * 10 + [0.5] * 10 + [0.0] * 108),
        ("Literature-biased query", [0.0] * 20 + [0.5] * 10 + [0.0] * 98),
        ("Neutral query", np.random.randn(128).tolist())
    ]
    
    for query_name, query_embedding in queries:
        # Normalize
        norm = np.linalg.norm(query_embedding)
        if norm > 0:
            query_embedding = (np.array(query_embedding) / norm).tolist()
        
        print(f"\n{query_name}:")
        
        # Search across all libraries
        all_results = []
        
        for lib in [tech_lib, science_lib, lit_lib]:
            results = await search_service.search(
                library_id=lib.id,
                embedding=query_embedding,
                k=2
            )
            
            for result in results:
                # Add library name to result for display
                result_with_lib = {
                    'library_name': lib.name,
                    'content': result.content,
                    'distance': result.distance,
                    'metadata': result.metadata
                }
                all_results.append(result_with_lib)
        
        # Sort by distance
        all_results.sort(key=lambda x: x['distance'])
        
        # Display top 5 results across all libraries
        for i, result in enumerate(all_results[:5]):
            print(f"  {i+1}. [{result['library_name']}] {result['content'][:50]}...")
            print(f"     Distance: {result['distance']:.4f}")


if __name__ == "__main__":
    asyncio.run(main())
