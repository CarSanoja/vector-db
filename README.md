# Vector Database API

A REST API for indexing and querying documents in a Vector Database.

## Quick Start

1. Install dependencies:
   ```bash
   make dev-install
   ```

2. Run the application:
   ```bash
   make run
   ```

3. Access the API documentation at http://localhost:8000/docs

## Architecture

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for detailed architecture documentation.

## Development

- Run tests: `make test`
- Format code: `make format`
- Run linting: `make lint`

## Docker

- Build image: `make docker-build`
- Run with Docker Compose: `make docker-run`
