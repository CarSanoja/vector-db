#!/bin/bash

# Vector Database Project Initialization Script
# This script sets up the complete project structure for the Vector Database REST API

set -e  # Exit on error

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== Vector Database Project Initialization ===${NC}"
echo -e "${YELLOW}Creating project structure...${NC}\n"

# Create root directory
PROJECT_NAME="vector-database-api"

# Create main directory structure
echo -e "${GREEN}✓ Creating directory structure${NC}"
mkdir -p {src,tests,docs,scripts,data}
mkdir -p src/{api,core,domain,infrastructure,services}
mkdir -p src/api/{endpoints,dependencies,middleware}
mkdir -p src/core/{indexes,algorithms,exceptions}
mkdir -p src/domain/{entities,value_objects,repositories}
mkdir -p src/infrastructure/{persistence,cache,locks}
mkdir -p src/services/{library_service,chunk_service,search_service}
mkdir -p tests/{unit,integration,performance,e2e}
mkdir -p data/{wal,snapshots,indexes}
mkdir -p docs/{api,architecture,examples}

# Create Python package files
echo -e "${GREEN}✓ Creating Python package structure${NC}"
touch src/__init__.py
touch src/api/__init__.py
touch src/api/endpoints/__init__.py
touch src/api/dependencies/__init__.py
touch src/api/middleware/__init__.py
touch src/core/__init__.py
touch src/core/indexes/__init__.py
touch src/core/algorithms/__init__.py
touch src/core/exceptions/__init__.py
touch src/domain/__init__.py
touch src/domain/entities/__init__.py
touch src/domain/value_objects/__init__.py
touch src/domain/repositories/__init__.py
touch src/infrastructure/__init__.py
touch src/infrastructure/persistence/__init__.py
touch src/infrastructure/cache/__init__.py
touch src/infrastructure/locks/__init__.py
touch src/services/__init__.py
touch src/services/library_service/__init__.py
touch src/services/chunk_service/__init__.py
touch src/services/search_service/__init__.py
touch tests/__init__.py

# Create configuration files
echo -e "${GREEN}✓ Creating configuration files${NC}"

# Create .env.example
cat > .env.example << 'EOF'
# Environment Configuration
ENV=development
DEBUG=True

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
API_PREFIX=/api/v1

# Database Configuration
PERSISTENCE_ENABLED=True
WAL_DIRECTORY=./data/wal
SNAPSHOT_DIRECTORY=./data/snapshots
INDEX_DIRECTORY=./data/indexes

# Index Configuration
DEFAULT_INDEX_TYPE=HNSW
LSH_TABLES=10
LSH_KEY_SIZE=10
HNSW_M=16
HNSW_EF_CONSTRUCTION=200

# Performance Configuration
MAX_WORKERS=4
BATCH_SIZE=1000
CACHE_SIZE=10000
CACHE_TTL=3600

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json
EOF

# Create .gitignore
cat > .gitignore << 'EOF'
# Byte-compiled / optimized / DLL files
__pycache__/
*.py[cod]
*$py.class

# Virtual Environment
venv/
env/
ENV/
.venv/

# IDE
.vscode/
.idea/
*.swp
*.swo
.DS_Store

# Environment variables
.env
.env.local

# Data files
data/
*.db
*.log
*.wal

# Test coverage
htmlcov/
.coverage
.coverage.*
coverage.xml
*.cover
.pytest_cache/

# Distribution / packaging
dist/
build/
*.egg-info/
.eggs/

# Documentation
docs/_build/
site/

# Temporary files
*.tmp
*.bak
.temp/
EOF

# Create pyproject.toml
cat > pyproject.toml << 'EOF'
[tool.poetry]
name = "vector-database-api"
version = "0.1.0"
description = "A REST API for indexing and querying documents in a Vector Database"
authors = ["Your Name <your.email@example.com>"]
readme = "README.md"
python = "^3.11"

[tool.poetry.dependencies]
python = "^3.11"
fastapi = "^0.104.0"
uvicorn = {extras = ["standard"], version = "^0.24.0"}
pydantic = "^2.4.0"
pydantic-settings = "^2.0.0"
numpy = "^1.26.0"
httpx = "^0.25.0"
python-dotenv = "^1.0.0"
structlog = "^23.2.0"
prometheus-client = "^0.18.0"
redis = "^5.0.0"
msgpack = "^1.0.7"

[tool.poetry.group.dev.dependencies]
pytest = "^7.4.0"
pytest-asyncio = "^0.21.0"
pytest-cov = "^4.1.0"
pytest-mock = "^3.12.0"
black = "^23.11.0"
ruff = "^0.1.5"
mypy = "^1.7.0"
pre-commit = "^3.5.0"
httpx = "^0.25.0"
faker = "^20.0.0"

[build-system]
requires = ["poetry-core"]
build-backend = "poetry.core.masonry.api"

[tool.black]
line-length = 88
target-version = ['py311']
include = '\.pyi?$'

[tool.ruff]
line-length = 88
select = [
    "E",  # pycodestyle errors
    "W",  # pycodestyle warnings
    "F",  # pyflakes
    "I",  # isort
    "C",  # flake8-comprehensions
    "B",  # flake8-bugbear
    "UP", # pyupgrade
]
ignore = [
    "E501",  # line too long
    "B008",  # do not perform function calls in argument defaults
    "C901",  # too complex
]

[tool.mypy]
python_version = "3.11"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true
disallow_incomplete_defs = true
check_untyped_defs = true
disallow_untyped_decorators = true
no_implicit_optional = true
warn_redundant_casts = true
warn_unused_ignores = true
warn_no_return = true
warn_unreachable = true
strict_equality = true

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
addopts = [
    "--strict-markers",
    "--tb=short",
    "--cov=src",
    "--cov-report=term-missing",
    "--cov-report=html",
    "--cov-report=xml",
    "-vv",
]
EOF

# Create Dockerfile
cat > Dockerfile << 'EOF'
# Multi-stage build for optimal image size
FROM python:3.11-slim as builder

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    POETRY_VERSION=1.7.0 \
    POETRY_HOME="/opt/poetry" \
    POETRY_VIRTUALENVS_CREATE=false

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN curl -sSL https://install.python-poetry.org | python3 -
ENV PATH="$POETRY_HOME/bin:$PATH"

# Set working directory
WORKDIR /app

# Copy dependency files
COPY pyproject.toml poetry.lock* ./

# Install dependencies
RUN poetry install --no-interaction --no-ansi --no-root --only main

# Production stage
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH"

# Create non-root user
RUN useradd -m -u 1000 appuser && \
    mkdir -p /app/data && \
    chown -R appuser:appuser /app

# Set working directory
WORKDIR /app

# Copy Python dependencies from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY --chown=appuser:appuser . .

# Switch to non-root user
USER appuser

# Create data directories
RUN mkdir -p data/wal data/snapshots data/indexes

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8000/health')"

# Run the application
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
EOF

# Create docker-compose.yml
cat > docker-compose.yml << 'EOF'
version: '3.8'

services:
  vector-db:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: vector-database-api
    ports:
      - "8000:8000"
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
    environment:
      - ENV=development
      - PERSISTENCE_ENABLED=true
      - LOG_LEVEL=INFO
    env_file:
      - .env
    restart: unless-stopped
    networks:
      - vector-db-network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

  redis:
    image: redis:7-alpine
    container_name: vector-db-redis
    ports:
      - "6379:6379"
    volumes:
      - redis-data:/data
    networks:
      - vector-db-network
    restart: unless-stopped
    command: redis-server --appendonly yes

networks:
  vector-db-network:
    driver: bridge

volumes:
  redis-data:
    driver: local
EOF

# Create Makefile
cat > Makefile << 'EOF'
.PHONY: help install dev-install lint format test test-cov run docker-build docker-run clean

# Default target
.DEFAULT_GOAL := help

# Help target
help:
	@echo "Vector Database API - Available commands:"
	@echo "  make install      - Install production dependencies"
	@echo "  make dev-install  - Install development dependencies"
	@echo "  make lint         - Run linting checks"
	@echo "  make format       - Format code with black"
	@echo "  make test         - Run tests"
	@echo "  make test-cov     - Run tests with coverage"
	@echo "  make run          - Run the application locally"
	@echo "  make docker-build - Build Docker image"
	@echo "  make docker-run   - Run with Docker Compose"
	@echo "  make clean        - Clean temporary files"

# Install dependencies
install:
	poetry install --only main

dev-install:
	poetry install
	pre-commit install

# Code quality
lint:
	poetry run ruff check src tests
	poetry run mypy src

format:
	poetry run black src tests
	poetry run ruff check --fix src tests

# Testing
test:
	poetry run pytest

test-cov:
	poetry run pytest --cov=src --cov-report=html --cov-report=term

# Running
run:
	poetry run uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

# Docker
docker-build:
	docker build -t vector-database-api:latest .

docker-run:
	docker-compose up -d

docker-down:
	docker-compose down

docker-logs:
	docker-compose logs -f

# Cleaning
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -rf .coverage htmlcov .pytest_cache
	rm -rf dist build *.egg-info
EOF

# Create pre-commit configuration
cat > .pre-commit-config.yaml << 'EOF'
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.5.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files
      - id: check-merge-conflict

  - repo: https://github.com/psf/black
    rev: 23.11.0
    hooks:
      - id: black
        language_version: python3.11

  - repo: https://github.com/charliermarsh/ruff-pre-commit
    rev: v0.1.5
    hooks:
      - id: ruff
        args: [--fix]

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.7.0
    hooks:
      - id: mypy
        additional_dependencies: [types-all]
        args: [--ignore-missing-imports]
EOF

# Create poetry.lock placeholder
touch poetry.lock

# Create main application file
cat > src/main.py << 'EOF'
"""Main application entry point for Vector Database API."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.api import health, libraries, chunks, search
from src.core.config import settings

# Create FastAPI application
app = FastAPI(
    title="Vector Database API",
    description="REST API for indexing and querying documents in a Vector Database",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router, tags=["health"])
app.include_router(libraries.router, prefix="/api/v1", tags=["libraries"])
app.include_router(chunks.router, prefix="/api/v1", tags=["chunks"])
app.include_router(search.router, prefix="/api/v1", tags=["search"])

@app.on_event("startup")
async def startup_event():
    """Initialize application on startup."""
    print("Vector Database API starting up...")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on application shutdown."""
    print("Vector Database API shutting down...")
EOF

# Create a simple README
cat > README.md << 'EOF'
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
EOF

# Make scripts executable
chmod +x scripts/*

echo -e "\n${GREEN}✓ Project structure created successfully!${NC}"
echo -e "${BLUE}Project location: $(pwd)${NC}"
echo -e "\n${YELLOW}Next steps:${NC}"
echo -e "1. cd $PROJECT_NAME"
echo -e "2. poetry install"
echo -e "3. make run"
echo -e "\n${GREEN}Happy coding! 🚀${NC}"