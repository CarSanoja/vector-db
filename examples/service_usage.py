"""Example of using the service layer."""
import asyncio
import numpy as np
from uuid import uuid4

from src.services import ServiceFactory
from src.domain.entities.library import IndexType


async def main():
    """Demonstrate service layer usage."""
    # Get service instances
    library_service = ServiceFactory.get_library_service()
    chunk_service = ServiceFactory.get_chunk_service()
    search_service = ServiceFactory.get_search_service()
    
    # Create a library
    print("Creating library...")
    library = await library_service.create_library(
        name="Document Collection",
        dimension=128,
        index_type=IndexType.HNSW,
        description="Example document collection"
    )
    print(f"Created library: {library.name} (ID: {library.id})")
    
    # Add some chunks
    print("\nAdding chunks...")
    chunks_data = []
    for i in range(10):
        embedding = np.random.randn(128).tolist()
        chunks_data.append({
            "content": f"This is document chunk {i}",
            "embedding": embedding,
            "metadata": {"doc_id": i // 3, "position": i % 3}
        })
    
    chunks = await chunk_service.create_chunks_bulk(
        library_id=library.id,
        chunks_data=chunks_data
    )
    print(f"Added {len(chunks)} chunks")
    
    # Search for similar chunks
    print("\nSearching for similar chunks...")
    query_embedding = np.random.randn(128).tolist()
    results = await search_service.search(
        library_id=library.id,
        embedding=query_embedding,
        k=5
    )
    
    print(f"Found {len(results)} similar chunks:")
    for i, result in enumerate(results):
        print(f"  {i+1}. {result.content} (score: {result.score:.3f})")
    
    # Search with metadata filter
    print("\nSearching with metadata filter...")
    filtered_results = await search_service.search(
        library_id=library.id,
        embedding=query_embedding,
        k=3,
        metadata_filters={"doc_id": 1}
    )
    
    print(f"Found {len(filtered_results)} chunks from doc_id=1")
    
    # Clean up
    print("\nCleaning up...")
    await library_service.delete_library(library.id)
    print("Library deleted")


if __name__ == "__main__":
    asyncio.run(main())
