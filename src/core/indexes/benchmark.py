"""Benchmarking tools for vector indexes."""
import time
from typing import Any, dict
from uuid import uuid4

import numpy as np

from .base import VectorIndex


class IndexBenchmark:
    """Benchmark different vector index implementations."""

    @staticmethod
    async def benchmark_index(
        index: VectorIndex,
        num_vectors: int,
        dimension: int,
        num_queries: int,
        k: int = 10
    ) -> dict[str, Any]:
        """Benchmark a single index implementation."""
        # Generate random vectors
        np.random.seed(42)
        vectors = [
            (uuid4(), np.random.randn(dimension).astype(np.float32))
            for _ in range(num_vectors)
        ]
        queries = [
            np.random.randn(dimension).astype(np.float32)
            for _ in range(num_queries)
        ]

        # Benchmark insertion
        start_time = time.time()
        await index.add_batch(vectors)
        insert_time = time.time() - start_time

        # Benchmark search
        search_times = []
        for query in queries:
            start_time = time.time()
            await index.search(query, k=k)
            search_times.append(time.time() - start_time)

        avg_search_time = np.mean(search_times)

        # Calculate memory usage (approximate)
        memory_usage = index.size * dimension * 4  # 4 bytes per float32

        return {
            "index_type": index.__class__.__name__,
            "num_vectors": num_vectors,
            "dimension": dimension,
            "insert_time": insert_time,
            "avg_search_time": avg_search_time,
            "search_qps": 1.0 / avg_search_time,
            "memory_usage_mb": memory_usage / (1024 * 1024),
            "vectors_per_second": num_vectors / insert_time
        }

    @staticmethod
    def print_results(results: dict[str, Any]) -> None:
        """Print benchmark results in a formatted way."""
        print(f"\n=== {results['index_type']} Benchmark Results ===")
        print(f"Vectors: {results['num_vectors']:,}")
        print(f"Dimension: {results['dimension']}")
        print(f"Insert time: {results['insert_time']:.3f}s")
        print(f"Vectors/second: {results['vectors_per_second']:.0f}")
        print(f"Avg search time: {results['avg_search_time']*1000:.2f}ms")
        print(f"Search QPS: {results['search_qps']:.0f}")
        print(f"Memory usage: {results['memory_usage_mb']:.1f}MB")
