#!/bin/sh
set -eu
: "${MAZE_HOME:?Set MAZE_HOME to an unpacked MAZE package matching the container architecture}"
cd "$(dirname "$0")/.."
sh tools/maze/build-adapter.sh
python3 maze_runtool/tests/verify.py
if [ "${1:-}" = --pipeline ]; then
    python3 maze_runtool/tests/pipeline.py
fi
