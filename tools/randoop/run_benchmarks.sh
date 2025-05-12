#!/bin/bash

# Define time budgets to loop through (in seconds)
TIME_BUDGETS=(5 10 30 60)
BENCHMARK_JOB_NAME="randoop"

echo "Starting benchmark runs for various time budgets."
echo "Tool Name: $BENCHMARK_JOB_NAME"

# Make sure runtool is executable
chmod +x "./runtool"

# Loop through each time budget
for TIME_BUDGET in "${TIME_BUDGETS[@]}"; do
    echo "-----------------------------------"
    echo "Running benchmark with Time Budget: $TIME_BUDGET seconds"

    echo "Generating tests for $BENCHMARK_JOB_NAME with time budget $TIME_BUDGET"
    contest_generate_tests.sh "$BENCHMARK_JOB_NAME" 10 1 "$TIME_BUDGET" > "state_log.txt" 2> "error_log.txt"

    RESULTS_DIR="results_${BENCHMARK_JOB_NAME}_${TIME_BUDGET}"
    echo "Computing metrics for $RESULTS_DIR"
    
    # Call the metrics computation script
    # Output and error logs are made unique for each time budget
    contest_compute_metrics.sh "$RESULTS_DIR" > "state_log.txt" 2> "error_log.txt"
    
    echo "Finished benchmark for Time Budget: $TIME_BUDGET"
done

echo "-----------------------------------"
echo "All benchmarks completed for $BENCHMARK_JOB_NAME!"