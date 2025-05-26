#!/bin/bash

set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m'

# Get script directory (examples folder)
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"

echo -e "${BLUE}=== Running All Vector Database Examples ===${NC}\n"

# Change to project root
cd "$PROJECT_ROOT"

# Setup environment
echo -e "${YELLOW}Setting up environment...${NC}"
if [ ! -d ".venv" ]; then
    echo -e "${RED}Error: Virtual environment not found${NC}"
    echo -e "${YELLOW}Please run 'poetry install' from project root${NC}"
    exit 1
fi

source .venv/bin/activate
export PYTHONPATH="${PYTHONPATH}:${PROJECT_ROOT}"
echo -e "${GREEN}✓ Environment ready${NC}\n"

# Function to run example with timeout (macOS compatible)
run_example() {
    local category=$1
    local example=$2
    local timeout_seconds=$3
    local skip_reason=$4
    
    echo -e "\n${CYAN}Running: ${category}/${example}${NC}"
    
    if [ -n "$skip_reason" ]; then
        echo -e "${YELLOW}⚠️  Skipping: ${skip_reason}${NC}"
        return 0
    fi
    
    # Create a temporary file for output
    local output_file=$(mktemp)
    local error_file=$(mktemp)
    local pid_file=$(mktemp)
    
    # Run in background with output capture
    python "examples/${category}/${example}" > "$output_file" 2> "$error_file" &
    local pid=$!
    echo $pid > "$pid_file"
    
    # Wait for process with timeout
    local elapsed=0
    while [ $elapsed -lt $timeout_seconds ]; do
        if ! kill -0 $pid 2>/dev/null; then
            # Process finished
            wait $pid
            local exit_code=$?
            
            if [ $exit_code -eq 0 ]; then
                # Success - show output
                cat "$output_file"
                echo -e "${GREEN}✓ Success${NC}"
                rm -f "$output_file" "$error_file" "$pid_file"
                return 0
            else
                # Failed
                echo -e "${RED}✗ Failed with exit code: ${exit_code}${NC}"
                echo -e "${RED}Error output:${NC}"
                cat "$error_file"
                rm -f "$output_file" "$error_file" "$pid_file"
                return 1
            fi
        fi
        
        sleep 1
        ((elapsed++))
    done
    
    # Timeout reached
    kill $pid 2>/dev/null || true
    echo -e "${YELLOW}⚠️  Timed out after ${timeout_seconds} seconds${NC}"
    rm -f "$output_file" "$error_file" "$pid_file"
    return 1
}

# Track statistics
total=0
passed=0
failed=0
skipped=0

# Create data directories for examples
mkdir -p examples/data examples/benchmarks

echo -e "${BLUE}=== Running Basic Examples ===${NC}"

# Basic examples (quick, should complete fast)
for example in examples/basic/*.py; do
    if [ -f "$example" ]; then
        ((total++))
        if run_example "basic" "$(basename $example)" 10; then
            ((passed++))
        else
            ((failed++))
        fi
    fi
done

echo -e "\n${BLUE}=== Running Advanced Examples ===${NC}"

# Advanced examples (may take longer)
for example in examples/advanced/*.py; do
    if [ -f "$example" ]; then
        ((total++))
        if run_example "advanced" "$(basename $example)" 20; then
            ((passed++))
        else
            ((failed++))
        fi
    fi
done

echo -e "\n${BLUE}=== Running Persistence Examples ===${NC}"

# Persistence examples (involve file I/O)
for example in examples/persistence/*.py; do
    if [ -f "$example" ]; then
        ((total++))
        if run_example "persistence" "$(basename $example)" 30; then
            ((passed++))
        else
            ((failed++))
        fi
    fi
done

echo -e "\n${BLUE}=== Running API Examples ===${NC}"

# API examples - check if server is running first
API_SERVER_RUNNING=false
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    API_SERVER_RUNNING=true
fi

for example in examples/api/*.py; do
    if [ -f "$example" ]; then
        ((total++))
        if [ "$API_SERVER_RUNNING" = true ]; then
            if run_example "api" "$(basename $example)" 15; then
                ((passed++))
            else
                ((failed++))
            fi
        else
            ((skipped++))
            run_example "api" "$(basename $example)" 15 "API server not running (start with: uvicorn src.main:app)"
        fi
    fi
done

echo -e "\n${BLUE}=== Running Benchmarks ===${NC}"

# Benchmarks (may take significant time)
echo -e "${YELLOW}Note: Benchmarks may take a while...${NC}"

for example in examples/benchmarks/*.py; do
    if [ -f "$example" ]; then
        ((total++))
        # Longer timeout for benchmarks
        if run_example "benchmarks" "$(basename $example)" 120; then
            ((passed++))
        else
            ((failed++))
        fi
    fi
done

echo -e "\n${BLUE}=== Checking Utilities ===${NC}"

# Utils are not run, just syntax checked
for util in examples/utils/*.py; do
    if [ -f "$util" ]; then
        echo -e "\n${CYAN}Checking: utils/$(basename $util)${NC}"
        ((total++))
        if python -m py_compile "$util" 2>/dev/null; then
            echo -e "${GREEN}✓ Valid Python syntax${NC}"
            ((passed++))
        else
            echo -e "${RED}✗ Syntax error${NC}"
            ((failed++))
        fi
    fi
done

# Cleanup
echo -e "\n${YELLOW}Cleaning up temporary data...${NC}"
rm -rf examples/data/wal examples/data/snapshots 2>/dev/null || true
echo -e "${GREEN}✓ Cleanup complete${NC}"

# Summary
echo -e "\n${BLUE}========================================${NC}"
echo -e "${BLUE}            SUMMARY REPORT              ${NC}"
echo -e "${BLUE}========================================${NC}\n"

echo -e "Total examples: ${total}"
echo -e "${GREEN}Passed: ${passed}${NC}"
echo -e "${RED}Failed: ${failed}${NC}"
echo -e "${YELLOW}Skipped: ${skipped}${NC}"

success_rate=0
if [ $total -gt 0 ]; then
    success_rate=$((passed * 100 / total))
fi

echo -e "\nSuccess rate: ${success_rate}%"

if [ $failed -eq 0 ] && [ $skipped -eq 0 ]; then
    echo -e "\n${GREEN}✅ All examples ran successfully!${NC}"
    exit 0
elif [ $failed -eq 0 ]; then
    echo -e "\n${YELLOW}⚠️  All runnable examples passed, but some were skipped${NC}"
    exit 0
else
    echo -e "\n${RED}❌ Some examples failed${NC}"
    exit 1
fi