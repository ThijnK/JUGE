#!/bin/bash

# Define benchmark pairs (strategies and concrete-driven)
# Strategy can be comma-separated like "DFS,BFS"
BENCHMARKS=(
  "DFS false"
  "DFS,BFS false"
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
    # Extract strategy and concrete values
    # This preserves commas in the strategy part
    strategy=$(echo "$benchmark" | awk '{print $1}')
    concrete=$(echo "$benchmark" | awk '{print $2}')
    
    echo "Running benchmark with strategy: $strategy, concrete: $concrete"
    
    # Update the runtool file
    cat > "./runtool" << EOF
#!/bin/bash

java -cp lib/maze_runtool-1.0.0.jar sbst.runtool.Main "$strategy" "$concrete"
EOF
    
    # Make sure runtool is executable
    chmod +x "./runtool"
    
    # Call the test generation script
    name="maze-${strategy//,/-}-${concrete}"
    contest_generate_tests.sh "$name" 1 1 $TIME_BUDGET
    contest_compute_metrics.sh results_"$name"_"$TIME_BUDGET" > state_log.txt 2> error_log.txt
    
    echo "Finished benchmark: $strategy $concrete"
    echo "-----------------------------------"
done

# Clean up
cat > "./runtool" << EOF
#!/bin/bash

java -cp lib/maze_runtool-1.0.0.jar sbst.runtool.Main
EOF

echo "All benchmarks completed!"