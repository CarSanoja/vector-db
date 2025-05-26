#!/bin/bash

set -e 

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m' 

SCRIPT_DIR_API_TESTS="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT_API_TESTS="$(cd "$SCRIPT_DIR_API_TESTS/.." && pwd)"

EXAMPLES_API_DIR_TARGET="${SCRIPT_DIR_API_TESTS}/api" 
DEFAULT_TIMEOUT_SECONDS=45
API_BASE_URL="http://localhost:8000"

echo -e "${BLUE}=== Running Vector Database API Client Examples ===${NC}"


cd "$PROJECT_ROOT_API_TESTS"

echo -e "\n${YELLOW}Setting up Python environment...${NC}"
if [ ! -d ".venv" ]; then
    echo -e "${RED}Error: Virtual environment '.venv' not found in project root (${PROJECT_ROOT_API_TESTS}).${NC}"
    echo -e "${YELLOW}Please run 'poetry install' from the project root to create it.${NC}"
    exit 1
fi

source .venv/bin/activate
export PYTHONPATH="${PYTHONPATH}:${PROJECT_ROOT_API_TESTS}"
echo -e "${GREEN}✓ Python environment ready.${NC}"

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

run_api_example() {
    local example_script_path=$1
    local example_name=$(basename "$example_script_path")
    local timeout_duration=$2

    echo -e "\n${CYAN}--- Running API Example: ${example_name} ---${NC}"

    local output_file=$(mktemp)
    local error_file=$(mktemp)
    local pid_file=$(mktemp)

    python3 "$example_script_path" > "$output_file" 2> "$error_file" &
    local pid=$!
    echo $pid > "$pid_file"

    local elapsed=0
    while kill -0 $pid 2>/dev/null; do
        if [ $elapsed -ge $timeout_duration ]; then
            kill $pid 2>/dev/null || true
            wait $pid 2>/dev/null
            echo -e "${YELLOW}⚠️ Timed out after ${timeout_duration} seconds for ${example_name}.${NC}"
            echo -e "${RED}Error output (if any):${NC}"
            cat "$error_file"
            rm -f "$output_file" "$error_file" "$pid_file"
            return 1
        fi
        sleep 1
        ((elapsed++))
    done

    wait $pid
    local exit_code=$?

    if [ $exit_code -eq 0 ]; then
        cat "$output_file" # Show output on success
        echo -e "${GREEN}✓ Success: ${example_name}${NC}"
        rm -f "$output_file" "$error_file" "$pid_file"
        return 0
    else
        echo -e "${RED}✗ Failed: ${example_name} (Exit Code: ${exit_code})${NC}"
        echo -e "${YELLOW}Stdout:${NC}" # Show stdout even on failure
        cat "$output_file"
        echo -e "${RED}Stderr:${NC}"
        cat "$error_file"
        rm -f "$output_file" "$error_file" "$pid_file"
        return 1
    fi
}

if ! check_api_server; then
    echo -e "\n${RED}Aborting API tests as server is not available.${NC}"
    exit 1
fi

total_tests=0
passed_tests=0
failed_tests=0

if [ -n "$1" ]; then
    example_file_path_arg="$1"
    if [[ "$example_file_path_arg" != /* ]]; then 
        if [ ! -f "$example_file_path_arg" ]; then
             echo -e "${RED}Error: Specified example script '$example_file_path_arg' not found relative to project root.${NC}"
             exit 1
        fi
    elif [ ! -f "$example_file_path_arg" ]; then
        echo -e "${RED}Error: Specified example script '$example_file_path_arg' not found.${NC}"
        exit 1
    fi

    example_filename=$(basename "$example_file_path_arg")
    echo -e "${BLUE}Running single API example: ${example_filename}${NC}"
    ((total_tests++))
    if run_api_example "$example_file_path_arg" $DEFAULT_TIMEOUT_SECONDS; then
        ((passed_tests++))
    else
        ((failed_tests++))
    fi
else
    actual_examples_dir="examples/api" 

    if [ ! -d "$actual_examples_dir" ]; then
        echo -e "${RED}Error: Examples directory '${actual_examples_dir}' not found in project root.${NC}"
        echo -e "${YELLOW}Please ensure your API example Python scripts are in '${PROJECT_ROOT_API_TESTS}/${actual_examples_dir}'${NC}"
        exit 1
    fi

    echo -e "${BLUE}Running all API examples in ${actual_examples_dir}${NC}"
    for example_script in $(find "${actual_examples_dir}" -maxdepth 1 -name '*.py' | sort); do
        if [ -f "$example_script" ]; then 
            ((total_tests++))
            if run_api_example "$example_script" $DEFAULT_TIMEOUT_SECONDS; then
                ((passed_tests++))
            else
                ((failed_tests++))
            fi
        fi
    done
fi

echo -e "\n${BLUE}========================================${NC}"
echo -e "${BLUE}         API EXAMPLES SUMMARY           ${NC}"
echo -e "${BLUE}========================================${NC}"
echo -e "Total examples run: ${total_tests}"
echo -e "${GREEN}Passed: ${passed_tests}${NC}"
echo -e "${RED}Failed: ${failed_tests}${NC}"

if [ $failed_tests -eq 0 ] && [ $total_tests -gt 0 ]; then
    echo -e "\n${GREEN}✅ All API examples ran successfully!${NC}"
    exit 0
elif [ $total_tests -eq 0 ]; then
    echo -e "\n${YELLOW}🤔 No API examples were run (is '${actual_examples_dir}' empty or incorrect?).${NC}"
    exit 0
else
    echo -e "\n${RED}❌ Some API examples failed.${NC}"
    exit 1
fi