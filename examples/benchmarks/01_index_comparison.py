#!/usr/bin/env python3
"""
Benchmark: Compare performance of different index types.
"""

import asyncio
import time
from pathlib import Path
from typing import list, tuple
from uuid import uuid4

import numpy as np

try:
    from tabulate import tabulate
    TABULATE_AVAILABLE = True
except ImportError:
    TABULATE_AVAILABLE = False
    print("Note: Install tabulate for better formatting: pip install tabulate")

try:
    import matplotlib.pyplot as plt
    MATPLOTLIB_AVAILABLE = False
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    print("Note: Install matplotlib for visualization: pip install matplotlib")

from src.core.indexes.factory import IndexFactory
from src.domain.entities.library import IndexType


async def generate_dataset(n_vectors: int, dimension: int) -> tuple[list[np.ndarray], list[np.ndarray]]:
    """Generate random vectors for testing."""
    print(f"Generating {n_vectors} vectors of dimension {dimension}...")

    # Training vectors
    train_vectors = [
        np.random.randn(dimension).astype(np.float32) 
        for _ in range(n_vectors)
    ]

    train_vectors = [v / np.linalg.norm(v) for v in train_vectors]

    # Query vectors (10% of training size)
    n_queries = max(10, n_vectors // 10)
    query_vectors = [
        np.random.randn(dimension).astype(np.float32) 
        for _ in range(n_queries)
    ]
    query_vectors = [v / np.linalg.norm(v) for v in query_vectors]

    return train_vectors, query_vectors


async def benchmark_index(index_type: IndexType, vectors: list[np.ndarray], 
                         queries: list[np.ndarray], k: int = 10) -> dict:
    """Benchmark a single index type."""
    dimension = len(vectors[0])
    results = {
        "index_type": index_type.value,
        "n_vectors": len(vectors),
        "dimension": dimension,
        "n_queries": len(queries),
        "k": k
    }

    factory = IndexFactory()
    index = factory.create_index(index_type, dimension)

    print(f"\nBenchmarking {index_type.value}...")
    print("  Building index...")
    start = time.time()

    # Add vectors using async interface
    for vector in vectors:
        await index.add(uuid4(), vector)

    build_time = time.time() - start
    results["build_time"] = build_time
    print(f"  Build time: {build_time:.3f}s")

    print("  Performing searches...")
    search_times = []

    for query in queries:
        start = time.time()
        _ = await index.search(query, k)
        search_times.append(time.time() - start)

    results["avg_search_time"] = np.mean(search_times)
    results["search_throughput"] = len(queries) / sum(search_times)
    print(f"  Avg search time: {results['avg_search_time']*1000:.2f}ms")
    print(f"  Search throughput: {results['search_throughput']:.0f} queries/sec")

    return results


async def main():
    """Run index comparison benchmark."""
    print("=== Index Performance Comparison ===\n")

    configs = [
        (1000, 128),    # Small dataset
        # (5000, 128),    # Medium dataset (reduced from 10000)
        # (10000, 128),   # Large dataset (reduced from 50000)
    ]

    index_types = [IndexType.LSH, IndexType.HNSW, IndexType.KD_TREE]

    all_results = []

    for n_vectors, dimension in configs:
        print(f"\n\n--- Dataset: {n_vectors} vectors, {dimension}D ---")

        vectors, queries = await generate_dataset(n_vectors, dimension)

        for index_type in index_types:
            try:
                results = await benchmark_index(index_type, vectors, queries)
                all_results.append(results)
            except Exception as e:
                print(f"  Error benchmarking {index_type.value}: {e}")

    print("\n\n=== Summary Results ===\n")

    if TABULATE_AVAILABLE:
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
    else:
        # Simple text output
        print("Index Type | Vectors | Build Time | Avg Search | Throughput")
        print("-" * 60)
        for r in all_results:
            print(f"{r['index_type']:10} | {r['n_vectors']:7} | {r['build_time']:7.3f}s | {r['avg_search_time']*1000:7.2f}ms | {r['search_throughput']:6.0f} q/s")

    if MATPLOTLIB_AVAILABLE:
        try:
            plot_results(all_results)
        except Exception as e:
            print(f"\nError creating plots: {e}")

    print("\n✓ Benchmark complete!")


def plot_results(results):
    """Plot benchmark results."""
    # Group by dataset size
    sizes = sorted({r["n_vectors"] for r in results})
    index_types = sorted({r["index_type"] for r in results})

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))

    for idx_type in index_types:
        build_times = []
        for size in sizes:
            matching = [r for r in results 
                       if r["index_type"] == idx_type and r["n_vectors"] == size]
            if matching:
                build_times.append(matching[0]["build_time"])
            else:
                build_times.append(None)

        valid_sizes = [s for s, t in zip(sizes, build_times) if t is not None]
        valid_times = [t for t in build_times if t is not None]

        if valid_times:
            ax1.plot(valid_sizes, valid_times, marker='o', label=idx_type)

    ax1.set_xlabel('Number of Vectors')
    ax1.set_ylabel('Build Time (seconds)')
    ax1.set_title('Index Build Time Comparison')
    ax1.legend()
    ax1.grid(True)
    ax1.set_xscale('log')

    for idx_type in index_types:
        throughputs = []
        for size in sizes:
            matching = [r for r in results 
                       if r["index_type"] == idx_type and r["n_vectors"] == size]
            if matching:
                throughputs.append(matching[0]["search_throughput"])
            else:
                throughputs.append(None)

        valid_sizes = [s for s, t in zip(sizes, throughputs) if t is not None]
        valid_throughputs = [t for t in throughputs if t is not None]

        if valid_throughputs:
            ax2.plot(valid_sizes, valid_throughputs, marker='o', label=idx_type)

    ax2.set_xlabel('Number of Vectors')
    ax2.set_ylabel('Queries per Second')
    ax2.set_title('Search Throughput Comparison')
    ax2.legend()
    ax2.grid(True)
    ax2.set_xscale('log')

    plt.tight_layout()

    output_dir = Path('examples/benchmarks')
    output_dir.mkdir(exist_ok=True)
    plt.savefig(output_dir / 'index_comparison.png')
    print(f"\nPlot saved to: {output_dir / 'index_comparison.png'}")


if __name__ == "__main__":
    asyncio.run(main())
