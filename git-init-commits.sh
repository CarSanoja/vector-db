#!/bin/bash

# Git Initialization and Commit Script for Vector Database Project
# This script creates structured commits following custom commit patterns

set -e  # Exit on error

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Function to make a commit with title and description
make_commit() {
    local type=$1
    local title=$2
    local description=$3
    
    echo -e "${BLUE}Creating commit: ${type}: ${title}${NC}"
    
    # Check if there are changes to commit
    if git diff --cached --quiet; then
        echo -e "${YELLOW}Warning: No changes staged for commit. Skipping...${NC}\n"
        return 0
    fi
    
    git commit -m "${type}: ${title}" -m "${description}" || {
        echo -e "${RED}Error: Failed to create commit${NC}"
        exit 1
    }
    
    echo -e "${GREEN}✓ Commit created successfully${NC}\n"
}

# Check if we're in the vector-database-api directory
if [ ! -f "pyproject.toml" ]; then
    echo -e "${RED}Error: This script must be run from the vector-database-api directory${NC}"
    exit 1
fi

# Initialize git repository
echo -e "${BLUE}=== Initializing Git Repository ===${NC}\n"

if [ -d ".git" ]; then
    echo -e "${YELLOW}Git repository already exists. Removing and reinitializing...${NC}"
    rm -rf .git
fi

git init
echo -e "${GREEN}✓ Git repository initialized${NC}\n"

# Configure git (optional - comment out if not needed)
git config --local user.name "Carlos Sanoja"
git config --local user.email "wuopcarlos@gmail.com"

# Commit 1: Initial project structure
echo -e "${YELLOW}Step 1/12: Creating initial project structure${NC}"
# Create .gitkeep files to track empty directories
touch src/.gitkeep tests/.gitkeep docs/.gitkeep scripts/.gitkeep
touch data/.gitkeep data/wal/.gitkeep data/snapshots/.gitkeep data/indexes/.gitkeep
# Add only the directory structure files, not the data directory itself
git add src/ tests/ docs/ scripts/ .gitignore
git add -f data/.gitkeep data/wal/.gitkeep data/snapshots/.gitkeep data/indexes/.gitkeep
make_commit "BUILD" "Initialize project directory structure" \
"Create foundational directory structure following Domain-Driven Design principles:
- src/: Source code with DDD layers (api, core, domain, infrastructure, services)
- tests/: Test suites (unit, integration, performance, e2e)
- docs/: Documentation directory for architecture and API docs
- scripts/: Utility scripts for development and deployment
- data/: Data storage directories (wal, snapshots, indexes) with .gitkeep files
- .gitignore: Standard Python gitignore configuration

This structure supports clean architecture with clear separation of concerns."

# Commit 2: Python package configuration
echo -e "${YELLOW}Step 2/12: Setting up Python package structure${NC}"
git add src/**/__init__.py tests/__init__.py
make_commit "BUILD" "Configure Python package structure" \
"Add __init__.py files to establish proper Python package hierarchy:
- Enable module imports across the application
- Define package boundaries for each architectural layer
- Support clean dependency injection patterns
- Facilitate unit testing with proper module isolation

Package structure follows PEP 420 namespace package conventions."

# Commit 3: Project dependencies and build configuration
echo -e "${YELLOW}Step 3/12: Configuring project dependencies${NC}"
git add pyproject.toml poetry.lock
make_commit "BUILD" "Add project dependencies and build configuration" \
"Configure Poetry for dependency management with pyproject.toml:
- Production dependencies: FastAPI, Pydantic, NumPy, Uvicorn
- Development dependencies: Pytest, Black, Ruff, MyPy
- Build system configuration using Poetry
- Code quality tools configuration (Black, Ruff, MyPy)
- Test configuration with pytest settings

Dependency versions are pinned for reproducible builds."

# Commit 4: Development environment configuration
echo -e "${YELLOW}Step 4/12: Setting up development environment${NC}"
git add .env.example
make_commit "BUILD" "Add environment configuration template" \
"Create .env.example with comprehensive configuration options:
- API settings (host, port, prefix)
- Database configuration (persistence, directories)
- Index algorithm parameters (LSH, HNSW, KD-Tree)
- Performance tuning (workers, batch size, cache)
- Logging configuration

Template provides sensible defaults for local development."

# Commit 5: Docker configuration
echo -e "${YELLOW}Step 5/12: Adding Docker support${NC}"
git add Dockerfile docker-compose.yml
make_commit "BUILD" "Add Docker containerization support" \
"Implement multi-stage Docker build for production deployment:
- Builder stage: Install dependencies with Poetry
- Production stage: Minimal runtime with security hardening
- Non-root user execution for security
- Health check endpoint configuration
- Volume mounts for data persistence

Docker Compose configuration includes:
- Vector database service with environment configuration
- Redis service for caching layer
- Network isolation and volume management
- Development-friendly settings with hot reload"

# Commit 6: Development tooling
echo -e "${YELLOW}Step 6/12: Configuring development tools${NC}"
git add Makefile
make_commit "BUILD" "Add Makefile for common development tasks" \
"Create Makefile with standard development commands:
- install/dev-install: Dependency management
- lint/format: Code quality enforcement
- test/test-cov: Test execution with coverage
- run: Local development server
- docker-build/docker-run: Container operations
- clean: Cleanup temporary files

Provides consistent interface for development workflow."

# Commit 7: Code quality configuration
echo -e "${YELLOW}Step 7/12: Setting up code quality tools${NC}"
git add .pre-commit-config.yaml
make_commit "BUILD" "Configure pre-commit hooks for code quality" \
"Establish automated code quality checks with pre-commit:
- Trailing whitespace and EOF fixes
- YAML and merge conflict detection
- Black formatting (88 char line length)
- Ruff linting with comprehensive rule set
- MyPy type checking with strict configuration

Ensures consistent code style and catches issues early."

# Commit 8: Application entry point
echo -e "${YELLOW}Step 8/12: Creating main application${NC}"
git add src/main.py
make_commit "FEAT" "Implement FastAPI application entry point" \
"Create main FastAPI application with core functionality:
- FastAPI app initialization with metadata
- CORS middleware for cross-origin requests
- Router registration for modular endpoints
- Startup/shutdown event handlers
- API documentation endpoints (/docs, /redoc)

Follows FastAPI best practices for application structure."

# Commit 9: Documentation
echo -e "${YELLOW}Step 9/12: Adding project documentation${NC}"
git add README.md
make_commit "FEAT" "Add initial project documentation" \
"Create README with essential project information:
- Project overview and purpose
- Quick start instructions
- Development workflow commands
- Architecture documentation reference
- Docker deployment instructions

Provides clear onboarding for new developers."

# Commit 10: Architecture documentation
echo -e "${YELLOW}Step 10/12: Adding architecture documentation${NC}"
git add docs/ARCHITECTURE.md
make_commit "FEAT" "Add comprehensive architecture documentation" \
"Document complete system architecture and design decisions:
- System overview with layered architecture
- Domain model with entities and value objects
- Detailed indexing algorithm implementations
- Concurrency design with thread safety
- Service layer architecture patterns
- API design following REST principles
- Persistence layer with WAL and snapshots
- Performance optimization strategies
- Security and monitoring considerations
- Testing strategy and deployment architecture

Serves as technical reference for implementation."

# Commit 11: Initialization script
echo -e "${YELLOW}Step 11/12: Adding project initialization script${NC}"
# Check if file exists before adding
if [ -f "init-project.sh" ]; then
    git add init-project.sh
    make_commit "BUILD" "Add project initialization script" \
"Create comprehensive initialization script that:
- Generates complete directory structure
- Creates all configuration files
- Sets up Python package structure
- Initializes development environment
- Provides clear setup instructions

Enables quick project setup for new developers."
else
    echo -e "${YELLOW}Skipping: init-project.sh not found${NC}\n"
fi

# Commit 12: Git automation script
echo -e "${YELLOW}Step 12/12: Adding git commit automation${NC}"
# The script itself should be in the parent directory or current directory
if [ -f "git-init-commits.sh" ]; then
    git add git-init-commits.sh
elif [ -f "../git-init-commits.sh" ]; then
    cp ../git-init-commits.sh .
    git add git-init-commits.sh
fi

if [ -f "git-init-commits.sh" ]; then
    make_commit "BUILD" "Add git initialization and commit script" \
"Implement automated git workflow script that:
- Initializes git repository
- Creates structured commits following custom commit format
- Documents each initialization step
- Maintains consistent commit message format
- Provides clear commit history for project setup

Uses FEAT/FIX/DEBUG/TEST/BUILD commit type convention."
else
    echo -e "${YELLOW}Skipping: git-init-commits.sh not found${NC}\n"
fi

# Create initial tag
echo -e "${BLUE}Creating initial version tag${NC}"
git tag -a v0.1.0 -m "Initial project setup

- Complete project structure with DDD architecture
- Docker containerization support
- Development tooling configuration
- Comprehensive documentation
- Code quality automation
- FastAPI application scaffold"

echo -e "${GREEN}✓ Tag v0.1.0 created${NC}\n"

# Summary
echo -e "${GREEN}=== Git Initialization Complete ===${NC}"
echo -e "${BLUE}Repository initialized with 12 structured commits${NC}"
echo -e "\n${YELLOW}Commit Summary:${NC}"
git log --oneline --decorate

echo -e "\n${YELLOW}Next steps:${NC}"
echo -e "1. Review commit history: git log"
echo -e "2. Set remote origin: git remote add origin <repository-url>"
echo -e "3. Push to remote: git push -u origin main --tags"
echo -e "\n${GREEN}Happy coding! 🚀${NC}"