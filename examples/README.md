# Vector Database Examples

This directory contains practical examples demonstrating the capabilities of the Vector Database system.

## Directory Structure

- `basic/` - Simple examples to get started
- `advanced/` - Advanced usage patterns
- `persistence/` - Persistence and recovery examples
- `api/` - REST API usage examples
- `benchmarks/` - Performance benchmarking scripts
- `utils/` - Utility scripts and helpers

## Prerequisites

```bash
# Activate virtual environment
source .venv/bin/activate

# Set PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

## Quick Start

1. Basic usage: `python examples/basic/01_create_library.py`
2. Vector search: `python examples/basic/02_vector_search.py`
3. With persistence: `python examples/persistence/01_persistent_operations.py`

## Examples Overview

### Basic Examples
- Creating libraries with different index types
- Adding and searching chunks
- Metadata filtering
- Bulk operations

### Advanced Examples
- Multi-library search
- Custom similarity metrics
- Index performance comparison
- Concurrent operations

### Persistence Examples
- Crash recovery simulation
- Backup and restore
- WAL inspection
- Snapshot management

### API Examples
- REST API client usage
- Batch processing via API
- Search with filters
- Health monitoring

### Benchmarks
- Index performance comparison
- Throughput testing
- Memory usage analysis
- Scalability tests
