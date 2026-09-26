#!/bin/bash
set -euo pipefail
if [ "$#" -lt 3 ]; then
    echo "Usage: $0 <time-budget-seconds> <repetitions> <experiment.json> [...]" >&2
    exit 2
fi
: "${MAZE_HOME:?Set MAZE_HOME to an unpacked MAZE Linux package}"
budget=$1
repetitions=$2
shift 2
[[ $budget =~ ^[1-9][0-9]*$ && $repetitions =~ ^[1-9][0-9]*$ ]] || {
    echo "Budget and repetitions must be positive integers" >&2; exit 2;
}
# Check all identities before starting; never silently reuse an existing experiment.
names=()
configs=()
for configuration in "$@"; do
    configuration=$(realpath "$configuration")
    name=$(python3 -c '
import json, re, sys
name = json.load(open(sys.argv[1]))["name"]
if not isinstance(name, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", name):
    sys.exit("Invalid experiment name")
print(name)
' "$configuration")
    for previous in "${names[@]}"; do
        [ "$previous" != "$name" ] || { echo "Duplicate experiment name: $name" >&2; exit 1; }
    done
    [ ! -e "results_maze-${name}_${budget}" ] || {
        echo "Results already exist for $name; use a new name or working directory." >&2; exit 1;
    }
    names+=("$name")
    configs+=("$configuration")
done
for i in "${!configs[@]}"; do
    export MAZE_EXPERIMENT=${configs[$i]}
    name=${names[$i]}
    contest_generate_tests.sh "maze-$name" "$repetitions" 1 "$budget"
    contest_compute_metrics.sh "results_maze-${name}_${budget}"
done
