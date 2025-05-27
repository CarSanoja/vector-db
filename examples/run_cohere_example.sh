#!/bin/bash

set -e 

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m' 


SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

COHERE_EXAMPLE_SCRIPT_PATH="examples/api/04_cohere_real_embeddings.py" # Relative to PROJECT_ROOT
DEFAULT_TIMEOUT_SECONDS=90 
API_BASE_URL="http://localhost:8000"

echo -e "${BLUE}=== Running Cohere Real Embeddings API Example ===${NC}"


cd "$PROJECT_ROOT"
echo -e "\n${YELLOW}Changed directory to project root: $(pwd)${NC}"

echo -e "\n${YELLOW}Setting up Python environment...${NC}"

source .venv/bin/activate
export PYTHONPATH="${PYTHONPATH}:${PROJECT_ROOT}"
echo -e "${GREEN}✓ Python environment ready.${NC}"

if ! command -v poetry &> /dev/null; then
    echo -e "${RED}Error: 'poetry' command not found.${NC}"
    echo -e "${YELLOW}Please install Poetry and ensure it's in your PATH.${NC}"
    echo -e "${YELLOW}See https://python-poetry.org/docs/#installation${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Poetry command found.${NC}"


echo -e "\n${YELLOW}Ensuring Python dependencies are installed/updated using 'poetry install'...${NC}"
if poetry install --no-root; then 
    echo -e "${GREEN}✓ Poetry dependencies are up to date.${NC}"
else
    echo -e "${RED}✗ 'poetry install' failed. Please check your pyproject.toml and Poetry setup.${NC}"
    exit 1
fi


echo -e "\n${YELLOW}Activating virtual environment...${NC}"

if [ ! -d ".venv" ]; then
    echo -e "${RED}Error: Virtual environment '.venv' not found in project root even after 'poetry install'.${NC}"
    echo -e "${YELLOW}This script expects Poetry to create a '.venv' directory in the project root.${NC}"
    echo -e "${YELLOW}You might need to configure Poetry: 'poetry config virtualenvs.in-project true'${NC}"
    echo -e "${YELLOW}Or, if your venv is elsewhere, you'll need to activate it manually before this script.${NC}"
    exit 1
fi

source .venv/bin/activate
export PYTHONPATH="${PROJECT_ROOT}:${PYTHONPATH}" 
echo -e "${GREEN}✓ Python virtual environment activated and PYTHONPATH set.${NC}"


check_api_server() {
    echo -e "\n${YELLOW}Checking if API server is running at ${API_BASE_URL}/health...${NC}"
    if curl --output /dev/null --silent --fail "${API_BASE_URL}/health"; then
        echo -e "${GREEN}✓ API server is responsive.${NC}"
        return 0
    else
        echo -e "${RED}✗ API server not responding or /health endpoint not found (or returns an error status).${NC}"
        echo -e "${YELLOW}Please ensure the API server is running. Example: uvicorn src.main:app --host 0.0.0.0 --port 8000${NC}"
        echo -e "${YELLOW}Or use: docker compose up --build${NC}"
        return 1
    fi
}

check_cohere_api_key() {
    echo -e "\n${YELLOW}Checking for COHERE_API_KEY environment variable...${NC}"
    if [ -f ".env" ]; then
        echo -e "${YELLOW}Found .env file, attempting to source it for this check...${NC}"
        export $(grep -v '^#' .env | xargs -0) > /dev/null 2>&1 || true
    fi

    if [[ -z "$COHERE_API_KEY" ]]; then
        echo -e "${RED}✗ COHERE_API_KEY environment variable is not set (or not found in .env file for this bash check).${NC}"
        echo -e "${YELLOW}The Python script requires this key to generate embeddings with Cohere.${NC}"
        echo -e "${YELLOW}Please ensure it's set in your .env file (which the Python script reads) or exported directly.${NC}"
        return 1 
    else
        echo -e "${GREEN}✓ COHERE_API_KEY environment variable appears to be available for the script.${NC}"
        return 0
    fi
}


if ! check_api_server; then
    echo -e "\n${RED}Aborting Cohere example as API server is not available.${NC}"
    exit 1
fi

if ! check_cohere_api_key; then
    echo -e "\n${RED}Aborting Cohere example as COHERE_API_KEY is not configured or detected by this script.${NC}"
    exit 1
fi

if [ ! -f "$COHERE_EXAMPLE_SCRIPT_PATH" ]; then
    echo -e "${RED}Error: Cohere example Python script not found at '${COHERE_EXAMPLE_SCRIPT_PATH}'.${NC}"
    exit 1
fi

echo -e "\n${CYAN}--- Running Python Example: $(basename "$COHERE_EXAMPLE_SCRIPT_PATH") ---${NC}"
echo -e "${YELLOW}Timeout for this script is ${DEFAULT_TIMEOUT_SECONDS} seconds.${NC}"

output_file=$(mktemp)
error_file=$(mktemp)
pid_file=$(mktemp)

python3 "$COHERE_EXAMPLE_SCRIPT_PATH" > "$output_file" 2> "$error_file" &
pid=$!
echo $pid > "$pid_file"

elapsed=0
success=false
while kill -0 $pid 2>/dev/null; do
    if [ $elapsed -ge $DEFAULT_TIMEOUT_SECONDS ]; then
        kill -TERM $pid 2>/dev/null || true 
        sleep 1 
        if kill -0 $pid 2>/dev/null ; then
           kill -KILL $pid 2>/dev/null || true 
        fi
        wait $pid 2>/dev/null
        echo -e "\n${RED}✗ FAILED (Timed Out): $(basename "$COHERE_EXAMPLE_SCRIPT_PATH") timed out after ${DEFAULT_TIMEOUT_SECONDS} seconds.${NC}"
        if [ -s "$error_file" ]; then
            echo -e "${YELLOW}Stderr from script:${NC}"
            cat "$error_file"
        fi
        if [ -s "$output_file" ]; then
            echo -e "${YELLOW}Stdout from script:${NC}"
            cat "$output_file"
        fi
        rm -f "$output_file" "$error_file" "$pid_file"
        exit 1
    fi
    sleep 1
    ((elapsed++))
done

wait $pid
exit_code=$?

if [ $exit_code -eq 0 ]; then
    echo -e "\n${GREEN}--- Script Output ---${NC}"
    cat "$output_file"
    echo -e "\n${GREEN}✓ SUCCESS: $(basename "$COHERE_EXAMPLE_SCRIPT_PATH") completed successfully.${NC}"
    success=true
else
    echo -e "\n${RED}--- Script Output (StdOut) ---${NC}"
    cat "$output_file"
    echo -e "\n${RED}--- Script Error Output (StdErr) ---${NC}"
    cat "$error_file"
    echo -e "\n${RED}✗ FAILED: $(basename "$COHERE_EXAMPLE_SCRIPT_PATH") failed with exit code ${exit_code}.${NC}"
fi

rm -f "$output_file" "$error_file" "$pid_file"

if $success; then
    exit 0
else
    exit 1
fi