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
