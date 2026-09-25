#!/bin/bash

# author: Urko Rueda (2018)
script_dir=$(cd -- "$(dirname -- "$0")" && pwd)
failed=0

if [ $# -ne 4 ]
then
        echo "Usage <tool-name> <runs-number> <runs-start-from> <time-budget (seconds)>"
        echo "example: contest_generate_tests.sh myToolName 6 7 60"
        exit 2;
fi

# Contest benchmarks (CUTs)
BENCH_HOME=${BENCH_HOME:-/var/benchmarks}
CONF=$BENCH_HOME/conf/benchmarks.list

# Get SUTS from the configuration file
# Names must be capitalized, and optionally followed by a hyphen and number
BENCH_SUTS=$(cat "$CONF" | grep -E "([A-Z]+(-[0-9]+)?=)+" | awk -F'=' '{print $1}')
if [ -z "$BENCH_SUTS" ]; then
    echo "No benchmark subjects found in $CONF" >&2
    exit 1
fi
echo "Benchmark SUTs: $BENCH_SUTS"

RESULTS_DIR=results_$1_$4
mkdir -p "$RESULTS_DIR"
runstop=$(( $2 + $3 ))
for ((RUN=$3; RUN<runstop; RUN++)); do
    echo "RUN: $RUN"
    for SUT in $BENCH_SUTS; do
        SUT_RUN_DIR=$RESULTS_DIR/${SUT}_$RUN
        if [ -d "$SUT_RUN_DIR" ]; then
            echo "Folder $SUT_RUN_DIR already exists. Skipping"
            case "$1" in
              maze|maze-*) python3 "$script_dir/maze_validate_generation.py" "$SUT_RUN_DIR" || failed=1 ;;
            esac
            continue
        fi

        mkdir -p "$SUT_RUN_DIR"
        >&2 echo "Running SUT = $SUT; RUN = $RUN at $(date)"
        case "$1" in
          maze|maze-*)
            export JUGE_MAZE_BATCH_ID=$(python3 -c 'import uuid; print(uuid.uuid4())')
            printf '%s\n' "$JUGE_MAZE_BATCH_ID" > "$SUT_RUN_DIR/maze-batch-id.txt"
            ;;
        esac
        if [[ $SUT == *ERRORPRONE* ]]; then
            contest_run_benchmark_tool_on_error-prone.sh "$1" "$SUT" . "$RUN" "$4" --only-generate-tests
        else
            contest_run_benchmark_tool.sh "$1" "$SUT" . "$RUN" "$4" --only-generate-tests
        fi
        generation_exit=$?
        case "$1" in
          maze|maze-*) printf '%s\n' "$generation_exit" > "$SUT_RUN_DIR/maze-process-exit.txt" ;;
        esac
        >&2 echo "... moving run results to: $SUT_RUN_DIR at $(date)"

        # Allow processes to release their output files before archiving them.
        sleep 2
        for log in log.txt log_detailed.txt transcript.csv *.log; do
            [ ! -f "$log" ] || mv "$log" "$SUT_RUN_DIR"
        done
        for attempt in 1 2 3; do
            if mv temp "$SUT_RUN_DIR" 2>/dev/null; then
                break
            fi
            >&2 echo "Failed to move temp directory (attempt $attempt), retrying in 1 second..."
            sleep 1
        done
        if [ "$1" = t3 ]; then
            mv trdir "$SUT_RUN_DIR"
        fi

        case "$1" in
          maze|maze-*)
            if ! python3 "$script_dir/maze_validate_generation.py" "$SUT_RUN_DIR" --generation; then
                touch "$SUT_RUN_DIR/GENERATION_FAILED.txt"
                failed=1
                continue
            fi
            ;;
        esac
        touch "$SUT_RUN_DIR/GENERATION_FINISHED.txt"
    done
done

exit "$failed"
