#!/bin/bash

# authors: Juan Galeotti and Urko Rueda (2016)

if [ $# -ne 1 ]
then
        echo "Results folder is expected"
        echo "example: contest_compute_metrics.sh /home/randoop_4h/results_Randoop_60sec"
        exit 0;
fi

script_dir=$(cd -- "$(dirname -- "$0")" && pwd)
RESULTS_DIR=$1
RESULTS_DIRNAME=$(basename "$RESULTS_DIR")
BUDGET=${RESULTS_DIRNAME##*_}
TOOLNAME=${RESULTS_DIRNAME#results_}
TOOLNAME=${TOOLNAME%_*}
failed=0
for f in "$RESULTS_DIR"/*_*; do
    [ -d "$f" ] || continue
    case "$TOOLNAME" in
      maze|maze-*)
        if ! python3 "$script_dir/maze_validate_generation.py" "$f"; then
            failed=1
            continue
        fi
        ;;
    esac
    FOLDER_NAME=$(basename "$f")
    if [ -d "$f/metrics" ]; then
        case "$TOOLNAME" in
          maze|maze-*)
            if [ ! -f "$f/metrics/COMPUTATION_FINISHED.txt" ]; then
                echo "Incomplete metrics already exist: $f/metrics" >&2
                failed=1
            fi
            ;;
        esac
        continue
    fi
    SUT_ID=${FOLDER_NAME%_*}
    RUN_ID=${FOLDER_NAME##*_}
	# contest tool specific code
	if [ $TOOLNAME == "t3" ]; then
		# T3 tool: trdir patch
		rm -rf trdir
		cp -R $RESULTS_DIR/$FOLDER_NAME/trdir trdir
	fi

    TESTCASES_FOLDER=$f/temp/testcases
    case "$TOOLNAME" in
      maze|maze-*) TESTCASES_FOLDER=$f/temp/maze-tests ;;
    esac
    command=contest_run_benchmark_tool.sh
    if [[ $SUT_ID == *ERRORPRONE* ]]; then
        command=contest_run_benchmark_tool_on_error-prone.sh
    fi
    rm -f transcript.csv
    if ! "$command" "$TOOLNAME" "$SUT_ID" . "$RUN_ID" "$BUDGET" --only-compute-metrics "$TESTCASES_FOLDER"; then
        echo "Metrics computation failed for $f" >&2
        failed=1
        continue
    fi
    if [ ! -s transcript.csv ] || [ ! -d temp ]; then
        echo "Metrics did not produce fresh output for $f" >&2
        failed=1
        continue
    fi
    METRICS_FOLDER=$f/metrics
    mkdir -p "$METRICS_FOLDER"
    if ! cp transcript.csv "$f/" || ! mv temp transcript.csv "$METRICS_FOLDER/"; then
        failed=1
        continue
    fi
    for log in log.txt log_detailed.txt *.log; do
        [ ! -f "$log" ] || mv "$log" "$METRICS_FOLDER/"
    done
	# contest tool specific code
	if [ $TOOLNAME == "t3" ]; then
		# T3 tool: trdir patch
		rm -rf trdir
	fi

	touch "$METRICS_FOLDER/COMPUTATION_FINISHED.txt"
	echo "Processing of folder $f has finished"
done

exit "$failed"
