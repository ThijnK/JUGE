#!/bin/sh
set -eu
: "${MAZE_HOME:?Set MAZE_HOME to an unpacked MAZE Linux package}"
repo=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
mkdir -p "$repo/maze_runtool/target" "$repo/tools/maze/lib"
classes=$(mktemp -d "$repo/maze_runtool/target/adapter-classes.XXXXXX")
trap 'rm -rf "$classes"' EXIT HUP INT TERM
# The release JAR supplies the JSON reader, so this needs only the JDK.
javac --release 8 -cp "$MAZE_HOME/maze.jar" -d "$classes" \
    "$repo"/maze_runtool/src/main/java/sbst/runtool/*.java
jar --create --file "$repo/tools/maze/lib/maze-adapter.jar" -C "$classes" .
