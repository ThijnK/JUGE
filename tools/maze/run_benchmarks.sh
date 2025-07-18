#!/bin/bash

# Define benchmark pairs (strategies and concrete-driven)
# Strategy can be comma-separated like "DFS,BFS" to interleave them
BENCHMARKS=(
    "DFS false"
    "BFS false"
    "SGS false"
    "RPS,COS false"
    "FOS false"
    "FOS,COS false"
    "DFS true"
    "BFS true"
    "FOS,COS true"
)

# Check if the time budget is provided
if [[ -z "$1" ]]; then
    echo "Error: Time budget not provided"
    echo "Usage: $0 <time_budget_in_seconds>"
    exit 1
fi

TIME_BUDGET="$1"

# Loop through each benchmark pair
for benchmark in "${BENCHMARKS[@]}"; do
    strategy=$(echo "$benchmark" | awk '{print $1}')
    concrete=$(echo "$benchmark" | awk '{print $2}')
    
    echo "-----------------------------------"
    echo "Running benchmark with strategy: $strategy, concrete: $concrete"
    echo "-----------------------------------"
    
    # Update the runtool file to set search strategy and concrete-driven mode
    cat > "./runtool" << EOF
#!/bin/bash

java -cp lib/maze_runtool-1.0.0.jar sbst.runtool.Main "$strategy" "$concrete"
EOF
    chmod +x "./runtool"
    
    concrete_name="SD"
    if [ "$concrete" == "true" ]; then
        concrete_name="CD"
    fi
    name="maze-${strategy//,/+}-${concrete_name}"
    echo "Generating tests for $name with time budget $TIME_BUDGET"
    contest_generate_tests.sh "$name" 10 1 $TIME_BUDGET > state_log.txt 2> error_log.txt

    echo "Computing metrics for $name with time budget $TIME_BUDGET" 
    contest_compute_metrics.sh results_"$name"_"$TIME_BUDGET" > state_log.txt 2> error_log.txt
    
    echo "Finished benchmark $name"
    echo "-----------------------------------"
done

# Clean up
cat > "./runtool" << EOF
#!/bin/bash

java -cp lib/maze_runtool-1.0.0.jar sbst.runtool.Main
EOF

echo "All benchmarks completed!"
