#!/bin/bash

if [[ -z "$1" ]]; then
    echo "Error: Time budget not provided"
    echo "Usage: $0 <time_budget_in_seconds>"
    exit 1
fi

TIME_BUDGET="$1"
TOOL_NAME="evosuite"

# Make sure runtool is executable
chmod +x "./runtool"

echo "-----------------------------------"
echo "Running benchmark for $TOOL_NAME with time budget $TIME_BUDGET (seconds)"
echo "-----------------------------------"

echo "Generating tests for $TOOL_NAME with time budget $TIME_BUDGET"
contest_generate_tests.sh "$TOOL_NAME" 10 1 "$TIME_BUDGET" > "state_log.txt" 2> "error_log.txt"

RESULTS_DIR="results_${TOOL_NAME}_${TIME_BUDGET}"
echo "Computing metrics for $RESULTS_DIR"
contest_compute_metrics.sh "$RESULTS_DIR" > "state_log.txt" 2> "error_log.txt"
    
echo "-----------------------------------"
echo "Finished benchmark for $TOOL_NAME for time budget $TIME_BUDGET"
