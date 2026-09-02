# MAZE Benchmarking

This document describes the benchmarking setup for the [MAZE tool](https://github.com/ThijnK/maze) using the JUGE framework and how to run the benchmarks.

A set of classes is provided for benchmarking. They are located in the [`benchmarks_maze`](/infrastructure/benchmarks_maze/README.md) directory. Results and raw data from the benchmarking are provided as separate zips, attached to Releases of this repository. The benchmarking to obtain that data is completely replicable using the Docker setup in this repository.
Instructions on how to replicate the benchmarks are provided below.
Instructions to run a single benchmark are also provided, in case you want to test the tool with a different configuration, different search strategies, or on a different set of benchmarks.

Included in this benchmark framework are several other Java testing tools which you can run for comparison: Randoop, T3, Evosuite, and Kex. Randoom and T3 are random testing tools. Evosuite uses search algorithms (evolutionary and local search). Kex uses symb olic execution. **Note:** their deployment can be found in the directory [tools](./tools). Each tool's sub-directory there (e.g. maze, or randoop) contains the binary of the tool along with an implementation of the tool-side of JUGE benchmarking protocol. If you are curious how this protocol is implemented, you can check the source code in the directory `toolname_runtool`. The implementation would call the tool executable, passing to it some configuration; so it is also the place to inspect what the exact configuration used on each tool.


## Prerequisites

- Docker installed on your machine
- Docker daemon running

## Replicating MAZE benchmarking

To replicate the benchmarking of MAZE, follow these steps:

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
   This limits the container to 2 CPUs and 4GB of RAM, which is the configuration we used when we ran the benchmarking for MAZE.
   To run the benchmarks for other tools, simply change the volume path to the tool folder you want to benchmark.
4. Inside the container, run the benchmarks:

   ```sh
    cd /home/maze
    ./run_benchmarks.sh <time-budget-seconds>
   ```

   This will run MAZE on the aforementioned [benchmark set](/infrastructure/benchmarks_maze/README.md) for the specified time budget, using different search strategy combinations listed below. Symbolic-driven mode is used.
   10 runs will be performed for each search strategy, and the results will be stored in a folder named `results_maze_<time-budget-seconds>`.
   The search strategies are:

   - Symbolic-driven DFS
   - Symbolic-driven BFS
   - Symbolic-driven SGS
   - Symbolic-driven RPS+COS
   - Symbolic-driven FOS
   - Symbolic-driven FOS+COS

   We used 10s and 60s time budget.

5. After the benchmarks are completed, you can compute the final scores:
   ```sh
   contest_transcript_single.sh ./
   score.sh results.tmp ./score
   ```
   This will create a score folder with the results of the benchmarks, including the Friedman test results, p-values, scores, and rankings.
   If in the previous step you ran the benchmarks with 10s and 60s time budgets, the resulting scores should correspond to the ones we obtained in our benchmarking.
   Additional metrics and plots used in the evaluation are all derived from the raw data in the `results.tmp` file, or from results from a subset of strategies.

For further instructions on how to run benchmarks using different MAZE configurations, or different benchmark sets, see the next section.

## Running a single benchmark

The above instruction will run the benchmarking for various MAZE strategies. If you just one to benchmark a single strategy, follow these steps below.

1. Go to the folder `./tools/maze`. Copy the script file `orig-runtool` to `runtool`. Edit the resulting file `runtool`: you can change the current call `java -cp lib/maze_runtool-1.0.0.jar sbst.runtool.Main` to add several positional arguments, as explained in the comment part of the script. E.g. you can specify which strategy and other settings you want to benchmark. E.g. you can choose DFS or BFS as the strategy.
 The search strategy option is the same as expected by the MAZE cli, described in the [MAZE documentation](https://github.com/ThijnK/maze).

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

   This runs the MAZE tool with the setting that was in the script file `runtool` that you made in step-1. Other settings are specified in the source code of [MAZE Runtool (Java)](/maze_runtool/src/main/java/sbst/runtool/MazeTool.java) file.
   That file is where the cli arguments are passed to MAZE.
   However, for quick changes to e.g. the search strategy or whether you want to apply minimalization, you can edit the aforementioned [`runtool`](/tools/maze/runtool) script.
   The script is what will be called when you run `contest_generate_tests.sh`.

   This will create a folder called `results_maze_<time-budget-seconds>` in the current directory, containing the generated tests for the benchmark subjects.

1. To compute the metrics (coverage, mutation analysis, etc.) run the following command:
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

This benchmarking framework is designed to benchmark any Java unit test generation tool, not just MAZE.
As already mentioned, you can run benchmarks for other tools by changing the volume path in the `docker run` command to the tool folder you want to benchmark. The following other tools are already packaged within this framework: Randoop, T3, EvoSuite, and Kex. They were used in our benchmarking. For convenience, a `run_benchmarks.sh` script is provided in the `tools` folder for EvoSuite, Randoop, and Kex, which runs the tool (generates tests) and compute the metrics in one go.

Specific note for Kex: while the `run_benchmarks.sh` script accepts a time budget as an argument, the Kex tool itself requires the time budget to be set in the [`kex.ini`](/tools/kex/lib/kex-0.0.11/kex.ini) file (the `timeLimit` property in the concolic section, on line 110), so make sure to update that file with the time budget you want to use before running the benchmarks.

**What if I want to add other tools?** Other tools can be benchmarked by implementing JUGE runtool-protocol. See JUGE; see JUGE [./README.md](docs/USERGUIDE.md) for the user guide and [./DEVELOPERS.md](docs/CONTRIBUTORGUIDE.md) for the contributor guide.

## Extending or changing the benchmark set

The target classes that form the benchmark subjects are placed in the `/var/benchmarks` directory of the container. These are copied from the benchmark subjects in [`benchmarks_maze`](/infrastructure/benchmarks_maze/README.md) directory. If you wish add more subjects, you can add them (Java source and compiled class files) to the zip there. If you want to use a completely new benchmark set, you can create and zip it in the structure similar to the zip in `benchmarks_maze`.
Edit the [Dockerfile](Dockerfile) to copy the new zip to the `/var/benchmarks` directory in the container (you may also need to edit the [.dockerignore](.dockerignore) file to avoid excluding the folder with your benchmarks).

**IMPORTANT:** keep in mind that subjects should be compiled in Java-8 so they can be instrumented by Jacoco for coverage measurement and targetted by PIT for mutation test.

## Changes to JUGE framework

The following changes were made to the JUGE framework to support the Maze tool:

- Upgraded the ubuntu base image to `ubuntu:22.04` from `ubuntu:20.04`.
- Added JDK 21 installation to the Dockerfile, as Maze targets Java 21 rather than Java 8.
- Added Z3 installation to the Dockerfile, as Maze requires Z3.
- Added a runtool implementation for Maze according to the format required by the JUGE framework.
- Added a runtool implementation for Kex according to the format required by the JUGE framework.
- Added a runtool implementation for T3 according to the format required by the JUGE framework.
- Other minor changes to fix issues with the framework or make things easier to use.

The benchmark subjects were added in the `benchmarks_maze` directory, see the [README](/infrastructure/benchmarks_maze/README.md) in that directory for details. If you want to put in other subjects, keep in mind that they should be compiled in Java-8 so they can be instrumented by Jacoco for coverage measurement and targetted by PIT for mutation test. Possibly some higher version of Java would also work (to compile the subjects), I haven't checked. In general, keep in mind what the requirement of Jacoco, PIT, and the testing tools you use for comparison with regards to the needed Java version.
