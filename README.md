¡Excelente idea actualizar el README principal! Un buen README es fundamental para que otros (¡y tu yo futuro!) entiendan el proyecto rápidamente.

Aquí tienes una propuesta de "lienzo" o borrador para tu README.md principal, incorporando la información que hemos discutido y las características que has implementado. Deberás ajustarlo y completarlo con los detalles específicos de tu proyecto (como URLs de repositorios, contenido exacto del Makefile, etc.).
Markdown

# Vector Database API

A REST API for indexing and querying documents within a Vector Database, specializing in storing and searching vector embeddings. This project features custom-coded indexing algorithms and is designed to be containerized using Docker.

## ✨ Features

* **RESTful API:** For managing and interacting with the vector database.
    * CRUD operations for **Libraries** (collections of documents/chunks).
    * CRUD operations for **Chunks** (text segments with embeddings) within Libraries.
    * Vector similarity search (k-NN) in specific libraries and across multiple libraries.
    * Support for **metadata filtering** during search operations.
* **Custom Vector Indexes:**
    * Implemented from scratch using Python and NumPy:
        * LSH (Locality Sensitive Hashing)
        * HNSW (Hierarchical Navigable Small Worlds)
        * KD-Tree (with random projections for high-dimensional data)
    * Allows selection of index type per library upon creation.
* **Data Model:**
    * Organized around Libraries, Documents (conceptual layer), and Chunks.
    * Chunks store text content, its vector embedding, and associated metadata.
    * Uses Pydantic for robust data validation and schema definition.
* **Persistence to Disk (Extra Point Implemented):**
    * Ensures data durability and state recovery across application restarts.
    * Utilizes a Write-Ahead Log (WAL) and snapshotting mechanism.
* **Concurrency Control:**
    * Features a custom `ReadWriteLock` and a `LockManager` with hierarchical locking to ensure data integrity and prevent race conditions during concurrent API requests and internal operations on in-memory data.
* **Dockerized Application:**
    * Fully containerized using Docker and Docker Compose for easy setup, deployment, and consistent environments.
* **Interactive API Documentation:**
    * Auto-generated via FastAPI:
        * Swagger UI: `http://localhost:8000/docs`
        * Redoc: `http://localhost:8000/redoc`
* **Comprehensive Examples:**
    * Includes Python scripts demonstrating core functionalities (basic, advanced, persistence).
    * Dedicated API client examples (`examples/api/`) showcasing interactions with all major API endpoints.
    * Runner scripts (`run_all_examples.sh`, `run_api_tests.sh`) for easy execution of examples.

## 🛠️ Tech Stack

* **Backend:** Python (3.11+)
* **API Framework:** FastAPI
* **Data Validation & Settings:** Pydantic, Pydantic-Settings
* **Dependency Management:** Poetry
* **Numerical Operations:** NumPy (core to custom index implementations)
* **Asynchronous Programming:** `asyncio`
* **Containerization:** Docker, Docker Compose
* **Logging:** Structlog (or your chosen logging library)
* **Caching/Optional Services (example):** Redis (as seen in `docker-compose.yml`)

## 🚀 Getting Started

### Prerequisites

* Python 3.11+ installed.
* Poetry installed (see [Poetry documentation](https://python-poetry.org/docs/#installation)).
* Docker and Docker Compose installed.
* `make` utility (optional, for using Makefile shortcuts).

### 1. Local Development Setup

a.  **Clone the repository:**
    ```bash
    git clone <your-repository-url>
    cd vector-database-api
    ```

b.  **Install dependencies using Poetry:**
    Your `Makefile` likely provides a command for this (as per your current README draft). If using Poetry directly:
    ```bash
    poetry install --all-extras # Or specify groups if you have them
    ```
    Or using your Makefile:
    ```bash
    make dev-install
    ```

c.  **Environment Variables:**
    Create a `.env` file in the project root (you can copy from an `.env.example` if one is provided). Populate it with necessary configurations:
    ```env
    # Example .env content
    ENV=development
    LOG_LEVEL=INFO
    PERSISTENCE_ENABLED=true
    # API_PREFIX=/api/v1 # If you configure it via settings
    # COHERE_API_KEY=your_key_here # If examples using Cohere need it
    ```

### 2. Running the Application

#### Option A: Locally with Uvicorn
   Activate your Poetry environment (`poetry shell` or `source .venv/bin/activate`) and then run:
   ```bash
   uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
   ```

Or using your Makefile (from your current README draft):
Bash

make run

Option B: Using Docker Compose (Recommended for a full environment including services like Redis)

From the project root:
Bash

docker compose up --build

Or using your Makefile (from your current README draft):
Bash

make docker-run

The API will be available at http://localhost:8000.
3. Access API Documentation

Once the server is running, explore the interactive API documentation:

    Swagger UI: http://localhost:8000/docs
    Redoc: http://localhost:8000/redoc

🧪 Running Tests and Examples

For example scripts that run locally (not hitting the API), activate the Poetry environment first.
Unit and Integration Tests

Run the automated test suite (typically Pytest):
Bash

make test

Core Logic & Feature Examples

These scripts demonstrate internal functionalities. The runner script handles environment setup.
Bash

# From the project root
./examples/run_all_examples.sh

API Client Examples

These scripts interact with the live API endpoints. The API server must be running. The runner script handles Python environment setup.
Bash

# From the project root
./examples/run_api_tests.sh

To run a specific API example (e.g., for libraries):
Bash

./examples/run_api_tests.sh examples/api/01_manage_libraries.py

API Example with Real Cohere Embeddings

This script demonstrates creating and searching with embeddings generated via the Cohere API.
The API server must be running, and your COHERE_API_KEY must be set in your .env file or environment.
Bash

# From the project root
./examples/run_cohere_example.sh

Example Showcase: Using Real Embeddings with Cohere

The examples/api/04_cohere_real_embeddings.py script (executed via ./examples/run_cohere_example.sh) demonstrates a full workflow:

* Connecting to the Cohere API to generate vector embeddings for sample text.
* Creating a library in your Vector DB API with dimensions matching the Cohere embeddings.
* Adding the texts and their corresponding Cohere embeddings as chunks to your library via API.
* Generating a query embedding for a sample question using Cohere.
* Searching your library with this query embedding.

```
=== Running Cohere Real Embeddings API Example ===
Changed directory to project root: /path/to/vector-db
...
✓ Python environment ready.
...
✓ API server is responsive.
...
✓ COHERE_API_KEY environment variable appears to be available for the script.
...
--- Running Python Example: 04_cohere_real_embeddings.py ---
...
========== STARTING COHERE REAL EMBEDDINGS API EXAMPLE ==========

========== CREATING LIBRARY: COHERE-DEMO-LIB-... (DIMENSION: 384) ==========
Status Code: 201
{
  "id": "b9ddb9e4-4fd6-43fe-9326-955673976ea2",
  "name": "Cohere-Demo-Lib-83d25a",
  "dimension": 384,
  "index_type": "HNSW",
  ...
  "created_at": "2025-05-26T04:15:49.687882",
  "updated_at": "2025-05-26T04:15:49.690407"
}
Generating embeddings with Cohere for 5 text(s) (model: embed-english-light-v3.0, type: search_document)...
Embeddings generated successfully.

========== ADDING 5 CHUNKS IN BULK TO LIBRARY: B9DDB9E4-4FD6-43FE-9326-955673976EA2 ==========
Status Code: 201
[
  {
    "id": "c283924a-0d73-48c9-9231-f4a85d6e7df6",
    "content": "The vibrant city of Barcelona is known for its unique architecture and lively atmosphere.",
    ...
  },
  ...
]

========== TRIGGERING INDEX BUILD FOR LIBRARY: B9DDB9E4-4FD6-43FE-9326-955673976EA2 ==========
Status Code: 202
{
  "message": "Index rebuild initiated",
  "library_id": "b9ddb9e4-4fd6-43fe-9326-955673976ea2",
  "status": "pending"
}
Waiting briefly to allow potential indexing or propagation...
Generating embeddings with Cohere for 1 text(s) (model: embed-english-light-v3.0, type: search_query)...
Embeddings generated successfully.

========== SEARCHING IN LIBRARY: B9DDB9E4-4FD6-43FE-9326-955673976EA2 (TOP 3 RESULTS) ==========
Status Code: 200
{
  "results": [], // Note: Search results depend heavily on query, indexed content, and embedding model.
  "query_time_ms": 0.0050067901611328125,
  "total_found": 0
}

========== SEARCH RESULTS FOR QUERY: "WHAT ARE SOME FAMOUS SPANISH FOODS AND LANDMARKS?" ==========
No search results found.

✓ Cohere Real Embeddings API Example completed successfully!

========== DELETING LIBRARY (CLEANUP): B9DDB9E4-4FD6-43FE-9326-955673976EA2 ==========
Status Code: (204)
...
========== EXAMPLE FLOW FINISHED ==========
```

🏗️ Project Structure Overview

```
.
├── Dockerfile            # Defines the Docker image for the application
├── docker-compose.yml    # Manages multi-container application (app, redis, etc.)
├── Makefile              # Shortcuts for common development tasks
├── poetry.lock           # Poetry lock file for deterministic dependencies
├── pyproject.toml        # Project metadata and dependencies for Poetry
├── README.md             # This main project README file
├── .env                  # Local environment variables (gitignored)
├── .env.example          # Template for .env file (if provided)
├── data/                 # (Created by app/Docker) For persistent data (WAL, snapshots)
├── docs/
│   └── ARCHITECTURE.md   # Detailed architecture documentation
├── examples/             # Example scripts and runners
│   ├── api/              # API client examples (01_manage_libraries.py, etc.)
│   ├── basic/            # Basic feature demonstrations
│   ├── advanced/         # Advanced feature demonstrations
│   ├── persistence/      # Persistence mechanism examples
│   ├── benchmarks/       # Performance benchmark scripts
│   ├── utils/            # Utility scripts
│   ├── run_all_examples.sh # Runner for core examples
│   └── run_api_tests.sh    # Runner for API client examples
├── src/                  # Application source code
│   ├── api/              # FastAPI specific code: endpoints, API models, middleware
│   ├── core/             # Core application logic: custom indexes, config, exceptions
│   ├── domain/           # Domain entities, repository interfaces, value objects
│   ├── infrastructure/   # Concrete implementations: repositories, persistence, locks
│   └── services/         # Service layer orchestrating business logic
├── tests/                # Unit and integration tests (e.g., using Pytest)
└── ...                   # Other project files (.gitignore, linting configs, etc.)
```

🛠️ Development Workflow

Common development commands (often available via Makefile):

    Install/Update Dependencies: make dev-install (or poetry install)
    Run Application Locally: make run (or uvicorn src.main:app --reload)
    Run Linters & Formatters:
        Format code: make format (e.g., Black, Ruff format)
        Check for linting issues: make lint (e.g., Ruff, Mypy)
    Run Tests: make test

🐳 Docker Operations

* Build Docker Image: make docker-build (or docker compose build vector-db)
* Run Application with Docker Compose: make docker-run (or docker compose up)
* Stop Docker Compose Services: make docker-stop (or docker compose down)
* View Logs: docker compose logs -f vector-db

🔑 Key Design Choices & Constraints Met

* Custom Indexing Algorithms: Vector indexes (LSH, HNSW, KD-Tree) are implemented from scratch using Python and NumPy, adhering to the constraint of not using pre-built external vector search libraries. (Detailed explanations in docs/ARCHITECTURE.md).
* Concurrency Control: A custom ReadWriteLock and LockManager with hierarchical locking manage concurrent access to shared resources, crucial for in-memory operations and preventing data races. (Design explained in docs/ARCHITECTURE.md).
* Persistence Layer: Implemented persistence with Write-Ahead Logging (WAL) and snapshotting for data durability (Extra Point). (Design explained in docs/ARCHITECTURE.md).
* Service-Oriented Architecture: Logic is layered (API -> Services -> Repositories/Domain) for better separation of concerns and testability.
* Typed & Pythonic Code: Emphasis on static typing and Pythonic conventions.

🏛️ Architecture

For an in-depth understanding of the system's architecture, components, data flow, and detailed design decisions (including indexing algorithms, persistence, and concurrency strategies), please refer to:
docs/ARCHITECTURE.md