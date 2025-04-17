# Maze benchmarking

This document describes the benchmarking setup for the [Maze tool](https://github.com/ThijnK/maze) using the JUGE framework.
It details the changes made to the JUGE framework to facilitate benchmarking the Maze tool, the objectives of the benchmarking, and the process to run the benchmarks.

## Changes

The following changes were made to the JUGE framework to support the Maze tool:

- Upgraded the ubuntu base image to `ubuntu:22.04` from `ubuntu:20.04`.
- Added JDK 21 installation to the Dockerfile, as Maze targets Java 21 rather than Java 8.
- Added Z3 installation to the Dockerfile, as Maze requires Z3.
- Added a runtool implementation for Maze according to the format required by the JUGE framework.

The benchmark subjects were added in the `benchmarks_maze` directory, see the [README](/infrastructure/benchmarks_maze/README.md) in that directory for details.

## Running the benchmarks

The steps to run the benchmarks are much the same as in the [User Guide](USERGUIDE.md), but are repeated here for clarity:

1. Package the JUGE framework to build the benchmark tools:
   ```sh
   mvn package
   ```
1. Build the Docker image:
   ```sh
   docker build -f Dockerfile -t junitcontest/infrastructure:latest .
   ```
1. Run a docker image, specifying a volume to share the tool folder for Maze between the host and the container:
   ```sh
   docker run -v $(pwd)/tools/maze:/home/maze --name=JUGE -it junitcontest/infrastructure:latest
   ```
   Or, on Windows:
   ```sh
   docker run -v %cd%\tools\maze:/home/maze --name=JUGE -it junitcontest/infrastructure:latest
   ```
1. Inside the container, run the Maze tool:
   ```sh
    cd /home/maze
    contest_generate_tests.sh maze <number-of-runs> <first-run-number> <time-budget-seconds>
   ```
1. Compute metrics:
   ```sh
   contest_compute_metrics.sh results_maze_<time-budget-seconds> > state_log.txt 2> error_log.txt
   ```
