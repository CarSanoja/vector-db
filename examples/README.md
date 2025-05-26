# Vector Database Examples

This directory contains practical examples demonstrating the capabilities and usage of the Vector Database system.

## Directory Structure

- `basic/` - Simple examples to get started with core vector database operations.
- `advanced/` - Demonstrations of advanced usage patterns and features.
- `persistence/` - Examples focusing on data persistence and recovery mechanisms.
- `api/` - Client-side examples showcasing REST API interactions for managing libraries, chunks, and performing searches. (Contains `01_manage_libraries.py`, `02_manage_chunks.py`, `03_search_operations.py`, etc.)
- `benchmarks/` - Scripts for performance benchmarking of different aspects of the system.
- `utils/` - Utility scripts and helpers, possibly for generating test data or embeddings.

## Prerequisites

Before running any Python examples directly, ensure you have set up your environment:

1.  **Install Dependencies:** Make sure all project dependencies are installed using Poetry from the project root:
    ```bash
    poetry install
    ```
2.  **Activate Virtual Environment:** From the project root, activate the Poetry virtual environment:
    ```bash
    source .venv/bin/activate
    ```
    (Alternatively, you can run scripts via `poetry run python examples/path/to/script.py`)

**Note:** The provided runner scripts (`run_all_examples.sh`, `run_api_tests.sh`) handle environment activation and `PYTHONPATH` setup automatically when run from the `examples/` directory or project root as intended.

## Running Examples

It's recommended to use the provided runner scripts for a comprehensive execution and summary.

### Running All Core Examples
This script runs basic, advanced, persistence, benchmark examples, and checks utils.
```bash
# From the project root:
./examples/run_all_examples.sh

    Benchmarks may take a while. The timeout for benchmarks can be adjusted within the script.
    API examples run by this script might be limited; use run_api_tests.sh for full API example coverage.

Running API Client Examples (Recommended for API testing)

This script is dedicated to running the more detailed API client examples found in examples/api/.
Bash

# From the project root:
./examples/run_api_tests.sh

To run a specific API example:
Bash

# From the project root:
./examples/run_api_tests.sh examples/api/01_manage_libraries.py

Important for API Examples: The Vector Database API server must be running for these examples to work. You can start it using:
Bash

# In a separate terminal, from the project root, after activating .venv:
uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload

Or by using Docker:
Bash

# From the project root:
docker compose up --build

Running Individual Examples

You can also run individual Python scripts directly (ensure environment is activated):
Bash

# From the project root, after activating .venv:
python examples/basic/01_create_library.py
python examples/api/01_manage_libraries.py

Examples Overview
Basic Examples (basic/)

    Creating libraries with different index types (LSH, HNSW, KD-Tree).
    Adding individual chunks with embeddings.
    Performing vector similarity searches.
    Using metadata in chunks.

Advanced Examples (advanced/)

    Searching across multiple libraries simultaneously.
    (Potentially: Custom similarity metrics, advanced index configurations, concurrent operations if specific examples are added)

Persistence Examples (persistence/)

    Demonstrating data persistence across server restarts.
    Simulation of crash recovery using Write-Ahead Log (WAL) and snapshots.
    (Potentially: Backup and restore operations, WAL/snapshot inspection utilities if added)

API Client Examples (api/)

These examples use httpx to interact with the live REST API:

    Library Management:
        Creating, retrieving, listing, updating, and deleting libraries.
        Triggering the (conceptual) index rebuild endpoint.
    Chunk Management:
        Creating individual chunks within a library.
        Bulk creation of chunks.
        Retrieving, listing, updating, and deleting chunks.
    Search Operations:
        Performing k-NN vector searches within a specific library.
        Applying metadata filters to narrow down search results.
        Executing searches across multiple specified libraries.
    Health Monitoring: Checking the /health endpoint (implicitly done by run_api_tests.sh).
    (Future Enhancement Suggestion in examples): Demonstrating usage with real embeddings generated via Cohere API.

Benchmarks (benchmarks/)

    Comparing performance (build time, search speed) of different implemented index types (LSH, HNSW, KD-Tree).
    (Potentially: Throughput testing under load, memory usage analysis, scalability tests if expanded)

Utilities (utils/)

    (Content to be detailed based on actual utility scripts, e.g., embedding generation helpers if any are added).