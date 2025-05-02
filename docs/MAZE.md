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
   With a limit of 2 CPUs and 4GB of RAM:
   ```sh
   docker run -v %cd%\tools\maze:/home/maze --name=JUGE -it --cpus=2 --memory=4g junitcontest/infrastructure:latest
   ```
1. Inside the container, run the Maze tool:
   ```sh
    cd /home/maze
    contest_generate_tests.sh maze <number-of-runs> <first-run-number> <time-budget-seconds>
   ```

## Computing metrics

1. Compute metrics:
   ```sh
   contest_compute_metrics.sh results_maze_<time-budget-seconds> > state_log.txt 2> error_log.txt
   ```
   Creates the `metrics` subfolder in the folders of each benchmark subject in the `results_maze_<time-budget-seconds>` folder.
1. Archive interesting files:
   ```sh
   taresults.sh
   ```
   Creates a zip file containing all the `transcript.csv` files in the `results_maze_<time-budget-seconds>` folder as a "backup" of the results.
1. Combine metrics:
   ```sh
   contest_transcript_single.sh results_maze_<time-budget-seconds>
   ```
   Creates a `results.tmp` file with all metrics in a single file.
   You can change "results*maze*<time-budget-seconds>" to "./" to combine all metrics from different results folders.
1. Compute the score:
   ```sh
   score.sh results.tmp <output-folder>
   ```
   Creates a `detailed_score.csv` and `score_per_subject.csv` file with the scores for each benchmark subject in the `results_maze_<time-budget-seconds>` folder.
   Score calculations are described in the [README](/infrastructure/README) file in the `infrastructure` folder.
   It also performs a statistical analysis of the scores if multiple tools (or multiple runs of the same tool with different names) are present in the `results.tmp` file.

## Script

A script, `run_benchmarks.sh`, is provided in the [`tools/maze`](/tools/maze/run_benchmarks.sh) directory to automate the process of running the benchmarks on MAZE using different search strategies.
The script takes care of generating tests and computing the metrics.
After that, you still have to manually follow the steps under "Computing metrics", starting from step 2, to combine and analyze results.
Note that the script will create multiple results folders, so in step 3, you would use the command `contest_transcript_single.sh ./` to combine all metrics from different results folders.
Running the `score.sh` scripts thereafter will perform a friedman test and provide rankings for the different strategies.
