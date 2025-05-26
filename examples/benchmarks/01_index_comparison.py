#!/usr/bin/env python3
"""
Benchmark: Compare performance of different index types.
"""

import asyncio
import time
import numpy as np
from typing import List, Tuple
import matplotlib.pyplot as plt
from tabulate import tabulate

from src.domain.entities.library import IndexType
from src.core.indexes.factory import IndexFactory
from src.core.indexes.base import VectorIndex


async def generate_dataset(n_vectors: int, dimension: int) -> Tuple[List[np.ndarray], List[np.ndarray]]:
    """Generate random vectors for testing."""
    print(f"Generating {n_vectors} vectors of dimension {dimension}...")
    
    # Training vectors
    train_vectors = [
        np.random.randn(dimension).astype(np.float32) 
        for _ in range(n_vectors)
    ]
    
    # Normalize
    train_vectors = [v / np.linalg.norm(v) for v in train_vectors]
    
    # Query vectors (10% of training size)
    n_queries = max(10, n_vectors // 10)
    query_vectors = [
        np.random.randn(dimension).astype(np.float32) 
        for _ in range(n_queries)
    ]
    query_vectors = [v / np.linalg.norm(v) for v in query_vectors]
    
    return train_vectors, query_vectors


async def benchmark_index(index_type: IndexType, vectors: List[np.ndarray], 
                         queries: List[np.ndarray], k: int = 10) -> dict:
    """Benchmark a single index type."""
    dimension = len(vectors[0])
    results = {
        "index_type": index_type.value,
        "n_vectors": len(vectors),
        "dimension": dimension,
        "n_queries": len(queries),
        "k": k
    }
    
    # Create index
    factory = IndexFactory()
    index = factory.create_index(index_type, dimension)
    
    # Build time
    print(f"\nBenchmarking {index_type.value}...")
    print("  Building index...")
    start = time.time()
    
    for i, vector in enumerate(vectors):
        index.add(i, vector)
    
    index.build()
    build_time = time.time() - start
    results["build_time"] = build_time
    print(f"  Build time: {build_time:.3f}s")
    
    # Search time
    print("  Performing searches...")
    search_times = []
    
    for query in queries:
        start = time.time()
        _ = index.search(query, k)
        search_times.append(time.time() - start)
    
    results["avg_search_time"] = np.mean(search_times)
    results["search_throughput"] = len(queries) / sum(search_times)
    print(f"  Avg search time: {results['avg_search_time']*1000:.2f}ms")
    print(f"  Search throughput: {results['search_throughput']:.0f} queries/sec")
    
    return results


async def main():
    """Run index comparison benchmark."""
    print("=== Index Performance Comparison ===\n")
    
    # Test configurations
    configs = [
        (1000, 128),    # Small dataset
        (10000, 128),   # Medium dataset
        (50000, 128),   # Large dataset
    ]
    
    index_types = [IndexType.LSH, IndexType.HNSW, IndexType.KDTREE]
    
    all_results = []
    
    for n_vectors, dimension in configs:
        print(f"\n\n--- Dataset: {n_vectors} vectors, {dimension}D ---")
        
        # Generate data
        vectors, queries = await generate_dataset(n_vectors, dimension)
        
        # Benchmark each index type
        for index_type in index_types:
            try:
                results = await benchmark_index(index_type, vectors, queries)
                all_results.append(results)
            except Exception as e:
                print(f"  Error benchmarking {index_type.value}: {e}")
    
    # Display results table
    print("\n\n=== Summary Results ===\n")
    
    table_data = []
    for r in all_results:
        table_data.append([
            r["index_type"],
            r["n_vectors"],
            f"{r['build_time']:.3f}s",
            f"{r['avg_search_time']*1000:.2f}ms",
            f"{r['search_throughput']:.0f} q/s"
        ])
    
    headers = ["Index Type", "Vectors", "Build Time", "Avg Search", "Throughput"]
    print(tabulate(table_data, headers=headers, tablefmt="grid"))
    
    # Plot results (optional - requires matplotlib)
    try:
        plot_results(all_results)
    except:
        print("\n(Install matplotlib to see performance plots)")


def plot_results(results):
    """Plot benchmark results."""
    # Group by dataset size
    sizes = sorted(set(r["n_vectors"] for r in results))
    index_types = sorted(set(r["index_type"] for r in results))
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
    
    # Build time plot
    for idx_type in index_types:
        build_times = [
            next(r["build_time"] for r in results 
                 if r["index_type"] == idx_type and r["n_vectors"] == size)
            for size in sizes
        ]
        ax1.plot(sizes, build_times, marker='o', label=idx_type)
    
    ax1.set_xlabel('Number of Vectors')
    ax1.set_ylabel('Build Time (seconds)')
    ax1.set_title('Index Build Time Comparison')
    ax1.legend()
    ax1.grid(True)
    ax1.set_xscale('log')
    
    # Search throughput plot
    for idx_type in index_types:
        throughputs = [
            next(r["search_throughput"] for r in results 
                 if r["index_type"] == idx_type and r["n_vectors"] == size)
            for size in sizes
        ]
        ax2.plot(sizes, throughputs, marker='o', label=idx_type)
    
    ax2.set_xlabel('Number of Vectors')
    ax2.set_ylabel('Queries per Second')
    ax2.set_title('Search Throughput Comparison')
    ax2.legend()
    ax2.grid(True)
    ax2.set_xscale('log')
    
    plt.tight_layout()
    plt.savefig('examples/benchmarks/index_comparison.png')
    print("\nPlot saved to: examples/benchmarks/index_comparison.png")


if __name__ == "__main__":
    asyncio.run(main())
