#!/usr/bin/env python3

import asyncio
from typing import Any

import httpx
import numpy as np


class VectorDBClient:
    """Simple client for Vector Database REST API."""

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.client = httpx.AsyncClient()

    async def close(self):
        await self.client.aclose()

    async def health_check(self) -> dict[str, Any]:
        """Check API health."""
        response = await self.client.get(f"{self.base_url}/health")
        response.raise_for_status()
        return response.json()

    async def create_library(self, name: str, dimension: int, 
                           index_type: str = "HNSW") -> dict[str, Any]:
        """Create a new library."""
        response = await self.client.post(
            f"{self.base_url}/api/v1/libraries",
            json={
                "name": name,
                "dimension": dimension,
                "index_type": index_type,
                "description": "Created via API client"
            }
        )
        response.raise_for_status()
        return response.json()

    async def add_chunk(self, library_id: str, content: str, 
                       embedding: list[float], metadata: dict[str, Any] = None) -> dict[str, Any]:
        """Add a chunk to a library."""
        response = await self.client.post(
            f"{self.base_url}/api/v1/libraries/{library_id}/chunks",
            json={
                "content": content,
                "embedding": embedding,
                "metadata": metadata or {}
            }
        )
        response.raise_for_status()
        return response.json()

    async def search(self, library_id: str, embedding: list[float], 
                    k: int = 10, metadata_filters: dict[str, Any] = None) -> dict[str, Any]:
        """Search for similar chunks."""
        response = await self.client.post(
            f"{self.base_url}/api/v1/libraries/{library_id}/search",
            json={
                "embedding": embedding,
                "k": k,
                "metadata_filters": metadata_filters
            }
        )
        response.raise_for_status()
        return response.json()


async def main():
    """Demonstrate REST API usage."""
    print("=== REST API Client Example ===\n")

    client = VectorDBClient()

    try:
        print("1. Checking API health...")
        health = await client.health_check()
        print(f"   Status: {health['status']}")
        print(f"   Version: {health['version']}")

        print("\n2. Creating library...")
        library = await client.create_library(
            name="API Example Library",
            dimension=128,
            index_type="HNSW"
        )
        library_id = library["id"]
        print(f"   Created library: {library['name']}")
        print(f"   ID: {library_id}")

        print("\n3. Adding chunks...")
        texts = [
            "The quick brown fox jumps over the lazy dog",
            "Machine learning is transforming technology",
            "Vector databases enable semantic search",
            "Python is a versatile programming language",
            "Natural language processing is fascinating"
        ]

        for i, text in enumerate(texts):
            embedding = np.random.randn(128).tolist()

            await client.add_chunk(
                library_id=library_id,
                content=text,
                embedding=embedding,
                metadata={"index": i, "category": "demo"}
            )
            print(f"   Added chunk {i+1}: {text[:30]}...")

        print("\n4. Performing search...")
        query_embedding = np.random.randn(128).tolist()
        results = await client.search(
            library_id=library_id,
            embedding=query_embedding,
            k=3
        )

        print(f"   Found {len(results['results'])} results:")
        print(f"   Query time: {results['query_time_ms']:.2f}ms")

        for i, result in enumerate(results['results']):
            print(f"\n   Result {i+1}:")
            print(f"   - Content: {result['content']}")
            print(f"   - Distance: {result['distance']:.4f}")
            print(f"   - Metadata: {result['metadata']}")

    except httpx.HTTPError as e:
        print(f"\nError: {e}")
        print("Make sure the API server is running: uvicorn src.main:app --reload")
    finally:
        await client.close()


if __name__ == "__main__":
    print("Note: This example requires the API server to be running.")
    print("Start it with: uvicorn src.main:app --reload\n")
    asyncio.run(main())
