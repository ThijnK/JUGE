#!/bin/bash

# Define benchmark configurations. Each config is a tuple: (s,m,p,a).
#
#    s : search strategy or strategies (separated by comma, no space!)
#    m : true/false whether or not suite minimalization is applied
#    p : the --path-length-cov option of MAZE, e.g. 3. Use 0 to disable.
#    a : the --target-path-aging option of MAZE
#

BENCHMARKS=(
    "DFS true 0 0"
    "BFS true 0 0"
    "SGS true 0 0"
    "RPS,COS true 0 0"
    "FOS true 0 0"
    "FOS,COS true 0 0"
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
    minimize=$(echo "$benchmark" | awk '{print $2}')
    pathlengthCov=$(echo "$benchmark" | awk '{print $3}')
    pathaging=$(echo "$benchmark" | awk '{print $4}')

    echo "-----------------------------------"
    echo "Running benchmark with strategy:$strategy, minimize:$minimize, path-length-cov:$pathlengthCov, target-path-aging:$pathaging"
    echo "-----------------------------------"

    # Update the runtool file to set search strategy and concrete-driven mode
    cat > "./runtool" << EOF
#!/bin/bash

java -cp lib/maze_runtool-1.0.0.jar sbst.runtool.Main "$strategy" "$minimize" "$pathlengthCov" "$pathaging"
EOF
    chmod +x "./runtool"

    #concrete_name="SD"
    #if [ "$concrete" == "true" ]; then
    #    concrete_name="CD"
    #fi
    #name="maze-${strategy//,/+}-${concrete_name}"
    name="maze-${strategy//,/+}"
    echo "Generating tests for $name with time budget $TIME_BUDGET"
    contest_generate_tests.sh "$name" 10 1 $TIME_BUDGET > state_log.txt 2> error_log.txt

    echo "Computing metrics for $name with time budget $TIME_BUDGET"
    contest_compute_metrics.sh results_"$name"_"$TIME_BUDGET" > state_log.txt 2> error_log.txt

    echo "Finished benchmark $name"
    echo "-----------------------------------"
done

# Clean up
cp ./orig-runtool ./runtool
chmod +x ./runtool
echo "All benchmarks completed!"
