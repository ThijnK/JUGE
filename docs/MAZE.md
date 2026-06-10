# MAZE Benchmarking

This document describes the benchmarking setup for the [MAZE tool](https://github.com/ThijnK/maze) using the JUGE framework and how to run the benchmarks.

MAZE was benchmarked on two sets of benchmarks: a synthetic benchmark set and an open source benchmark set.
The synthetic benchmark set is located in the [`benchmarks_maze`](/infrastructure/benchmarks_maze/README.md) directory.
The thesis that introduced MAZE used 10 benchmark subjects, and this was later extended to 20 subjects for the paper.
The open source benchmark set is the same as the one used in the Java Test Case Generation Track of the SBFT Tool Competition 2024, which is located in the [`benchmarks_12th`](/infrastructure/benchmarks_12th/README.md) directory.

All raw data and scripts used in the evaluation are available in the [/maze_benchmarks](/maze_benchmarks/README.md) directory.

The benchmarking to obtain that data is completely replicable using the Docker setup in this repository.
Instructions on how to replicate the benchmarks are provided below.
Instructions to run a single benchmark are also provided, in case you want to test the tool with a different configuration or on a different set of benchmarks.

## Prerequisites

- Docker installed on your machine
- Docker daemon running

## Replicating the benchmarks

To replicate the benchmarks, follow these steps:

1. Clone this repository:
   ```sh
   git clone https://github.com/ThijnK/JUGE
   ```
2. Build the Docker image:
   ```sh
   docker build -f Dockerfile -t junitcontest/infrastructure:latest .
   ```
3. Run a container, specifying a volume to share the tool folder for MAZE between the host and the container:
   ```sh
   docker run -v $(pwd)/tools/maze:/home/maze --name=JUGE -it --cpus=2 --memory=4g junitcontest/infrastructure:latest
   ```
   Or, on Windows:
   ```sh
   docker run -v %cd%\tools\maze:/home/maze --name=JUGE -it --cpus=2 --memory=4g junitcontest/infrastructure:latest
   ```
   This limits the container to 2 CPUs and 4GB of RAM, which is the configuration used in the benchmarks for MAZE.
   To run the benchmarks for other tools, simply change the volume path to the tool folder you want to benchmark.
4. Inside the container, run the benchmarks:

   ```sh
    cd /home/maze
    ./run_benchmarks.sh <time-budget-seconds>
   ```

   This will run MAZE on the [synthetic benchmark set](/infrastructure/benchmarks_maze/README.md) for the specified time budget, using nine different search strategy combinations.
   10 runs will be performed for each search strategy, and the results will be stored in a folder named `results_maze_<time-budget-seconds>`.
   The search strategies are:

   - Symbolic-driven DFS
   - Symbolic-driven BFS
   - Symbolic-driven SGS
   - Symbolic-driven RPS+COS
   - Symbolic-driven FOS
   - Symbolic-driven FOS+COS
   - Concrete-driven DFS
   - Concrete-driven BFS
   - Concrete-driven FOS+COS

   The benchmarks for MAZE were run with the following time budgets: 5s, 10s, 30s, 60s.
   You can rerun this command with these time budgets to replicate the benchmarks.

   If you are running benchmarks for other tools, use `cd /home/<tool-folder>` to change to the tool folder you want to benchmark.
   For EvoSuite, Randoop, and Kex (the tools MAZE was compared against), a `run_benchmarks.sh` script is provided that works similarly to the one for MAZE, running the tool and computing the metrics in one go.
   Other tools can be benchmarked by creating a similar script that runs the tool and computes the metrics, or by following the separate steps in the next section below.

   Specific note for Kex: while the `run_benchmarks.sh` script accepts a time budget as an argument, the Kex tool itself requires the time budget to be set in the [`kex.ini`](/tools/kex/lib/kex-0.0.11/kex.ini) file (the `timeLimit` property in the concolic section, on line 110), so make sure to update that file with the time budget you want to use before running the benchmarks.

5. After the benchmarks are completed, you can compute the final scores:
   ```sh
   contest_transcript_single.sh ./
   score.sh results.tmp ./score
   ```
   This will create a score folder with the results of the benchmarks, including the Friedman test results, p-values, scores, and rankings.
   If in the previous step you ran the benchmarks with all four time bdugets (5s, 10s, 30s, 60s), the resulting scores will match the ones used in the evaluation of MAZE.
   Additional metrics and plots used in the evaluation are all derived from the raw data in the `results.tmp` file, or from results from a subset of strategies.

For further instructions on how to run benchmarks using different MAZE configurations, or different benchmark sets, see the next section.

## Running a single benchmark

Follow these steps to run a single benchmark, using the default configuration of the MAZE tool (symbolic-driven DFS):

1. Build the Docker image:
   ```sh
   docker build -f Dockerfile -t junitcontest/infrastructure:latest .
   ```
1. Run a container, specifying a volume to share the tool folder for MAZE between the host and the container:
   ```sh
   docker run -v $(pwd)/tools/maze:/home/maze --name=JUGE -it junitcontest/infrastructure:latest
   ```
   Or, on Windows:
   ```sh
   docker run -v %cd%\tools\maze:/home/maze --name=JUGE -it junitcontest/infrastructure:latest
   ```
   To limit the container to 2 CPUs and 4GB of RAM, which is the configuration used in the benchmarks for MAZE, you can use the following command:
   ```sh
   docker run -v %cd%\tools\maze:/home/maze --name=JUGE -it --cpus=2 --memory=4g junitcontest/infrastructure:latest
   ```
   Again, you can change the volume path to the tool folder you want to benchmark.
1. Inside the container, run the Maze tool:

   ```sh
    cd /home/maze
    contest_generate_tests.sh maze <number-of-runs> <first-run-number> <time-budget-seconds>
   ```

   This runs the MAZE tool with the configuration specified in the [MAZE Runtool`](/maze_runtool/src/main/java/sbst/runtool/MazeTool.java) file.
   That file is where the cli arguments are passed to MAZE.
   However, for quick changes to either the search strategy or whether to run in concrete-driven mode, you can edit the [`runtool`](/tools/maze/runtool) script in the `tools/maze` directory.
   The `runtool` script is what will be called when you run `contest_generate_tests.sh`.
   Inside that script, you can change the current call `java -cp lib/maze_runtool-1.0.0.jar sbst.runtool.Main` to add two positional arguments, the first for the search strategy and the second for the concrete-driven option:

   ```sh
   java -cp lib/maze_runtool-1.0.0.jar sbst.runtool.Main <search-strategy> <true/false>
   ```

   The search strategy option is the same as expected by the MAZE cli, described in the [MAZE documentation](https://github.com/ThijnK/maze?tab=readme-ov-file#command-line-options).

   This runs the tool on the benchmark subjects in the `/var/benchmarks` directory of the container, which contains the benchmark subjects in [`benchmarks_maze`](/infrastructure/benchmarks_maze/README.md) directory.
   If you wish to use a different benchmark set, you can add them and edit the [Dockerfile](Dockerfile) to copy them to the `/var/benchmarks` directory instead of the `benchmarks_maze` directory (you may also need to edit the [.dockerignore](.dockerignore) file to avoid excluding the folder with your benchmarks).

This will create a folder called `results_maze_<time-budget-seconds>` in the current directory, containing the generated tests for the benchmark subjects.
To compute the metrics (coverage, mutation analysis, etc.) and the scores, follow these steps:

1. Inside the container, run the following command to compute the metrics:
   ```sh
   contest_compute_metrics.sh results_maze_<time-budget-seconds>
   ```
   This will create a `metrics` subfolder in the folders of each benchmark subject in the `results_maze_<time-budget-seconds>` folder.
1. Combine metrics:
   ```sh
   contest_transcript_single.sh results_maze_<time-budget-seconds>
   ```
   This will create a `results.tmp` file with all metrics in a single file.
   You can change `results_maze_<time-budget-seconds>` to `./` to combine all metrics from different results folders.
1. Compute the score:
   ```sh
   score.sh results.tmp <output-folder>
   ```
   Creates a `detailed_score.csv` and `score_per_subject.csv` file with the scores for each benchmark subject in the `results_maze_<time-budget-seconds>` folder.
   Score calculations are described in the [README](/infrastructure/README) file in the `infrastructure` folder.
   It also performs a statistical analysis of the scores if multiple tools (or multiple runs of the same tool with different names) are present in the `results.tmp` file.

## Benchmarking other tools

This repository is designed to benchmark any Java unit test generation tool, not just MAZE.
As already mentioned, you can run benchmarks for other tools by changing the volume path in the `docker run` command to the tool folder you want to benchmark.
In the benchmarks used for MAZE, EvoSuite, Randoop, and Kex were also benchmarked.
For convenience, a `run_benchmarks.sh` script is provided in the `tools` folder for both EvoSuite, Randoop, and Kex, which runs the tool (generates tests) and compute the metrics in one go.

## Changes to JUGE framework

The following changes were made to the JUGE framework to support the Maze tool:

- Upgraded the ubuntu base image to `ubuntu:22.04` from `ubuntu:20.04`.
- Added JDK 21 installation to the Dockerfile, as Maze targets Java 21 rather than Java 8.
- Added Z3 installation to the Dockerfile, as Maze requires Z3.
- Added a runtool implementation for Maze according to the format required by the JUGE framework.
- Added a runtool implementation for Kex according to the format required by the JUGE framework.
- Other minor changes to fix issues with the framework or make things easier to use.

The benchmark subjects were added in the `benchmarks_maze` directory, see the [README](/infrastructure/benchmarks_maze/README.md) in that directory for details. If you want to put in other subjects, keep in mind that they should be compiled in Java-8 so they can be instrumented by Jacoco for coverage measurement and targetted by PIT for mutation test. Possibly some higher version of Java would also work (to compile the subjects), I haven't checked. In general, keep in mind what the requirement of Jacoco, PIT, and the testing tools you use for comparison with regards to the needed Java version.
