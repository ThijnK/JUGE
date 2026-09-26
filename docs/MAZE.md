# Benchmarking MAZE

JUGE runs the benchmark subjects, repetitions, coverage measurement, and mutation
analysis. MAZE remains a separate package: this repository's adapter launches it
with a named experiment configuration. External strategies and heuristics use the
same path as shipped strategies; no launcher or Java source edits are necessary.

## Prepare the environment

Use the published [MAZE v1.2.0 package](https://github.com/ThijnK/maze/releases/tag/v1.2.0).
Download it separately; MAZE does not need to be copied into this repository or
built from source.

The full JUGE image currently targets Linux x86-64: it uses Java 8 for the legacy
coverage/mutation tools and Java 21 for MAZE. On an Apple Silicon Mac, build and run
it with `--platform linux/amd64`, and select MAZE's **amd64** archive. You do not
need Java or Z3 installed on the host.

From the JUGE checkout, download and verify the package in a sibling directory:

```sh
mkdir -p ../maze-packages
(
  cd ../maze-packages
  curl --fail --location --remote-name https://github.com/ThijnK/maze/releases/download/v1.2.0/maze-1.2.0-linux-amd64.tar.gz
  curl --fail --location --remote-name https://github.com/ThijnK/maze/releases/download/v1.2.0/maze-1.2.0-linux-amd64.tar.gz.sha256
  shasum -a 256 -c maze-1.2.0-linux-amd64.tar.gz.sha256 &&
    tar -xzf maze-1.2.0-linux-amd64.tar.gz
)
MAZE_PACKAGE="$(cd ../maze-packages/maze-1.2.0-linux-amd64 && pwd)"
```

Keep that directory for future runs. Build and start JUGE from the same shell:

```sh
docker build --platform linux/amd64 -t juge-maze .
docker run --rm -it --platform linux/amd64 --cpus=2 --memory=4g \
  -v "$PWD:/juge" -v "$MAZE_PACKAGE:/opt/maze:ro" \
  -v /absolute/path/to/research:/research \
  -e MAZE_HOME=/opt/maze -w /juge juge-maze bash
```

Inside the container, compile the adapter against the selected package:

```sh
export PATH="$MAZE_JAVA_HOME/bin:$PATH"
sh tools/maze/build-adapter.sh
cd tools/maze
```

The build produces `lib/maze-adapter.jar`. MAZE's JAR supplies the JSON dependency;
the adapter does not compile against MAZE's engine classes. The Docker build also
rebuilds JUGE's benchmark runner from source, so its timeout handling cannot lag
behind a checked-in binary.

## Describe an experiment

An experiment file names the variant, chooses an execution mode, and supplies
MAZE arguments. For example, `/research/depth-symbolic.json`:

```json
{
  "name": "depth-symbolic",
  "mode": "symbolic",
  "arguments": [
    "--plugin", "research.jar",
    "--search-config", "search.json",
    "--minimization=true", "--max-depth=400", "--max-array-size=10"
  ]
}
```

Paths in `arguments` are relative to the **experiment file's directory**. Use
MAZE's existing search JSON in `search.json`, including constructor options,
heuristic combinations, and repeated strategy instances. Each occurrence remains
separate. Repeat `--plugin` for dependencies. Build the research JAR against
`/opt/maze/maze.jar`; the [MAZE author guide](https://github.com/ThijnK/maze/blob/main/docs/search-extensions.md)
provides complete examples.

For a shipped baseline, use `"arguments": ["--strategy", "BFS", ...]` instead.
Copy an experiment and set `"mode": "concrete"` to compare the other execution mode.
Give different variants different names. Two example baseline files are supplied
under `tools/maze/experiments/`.

JUGE supplies the classpath, target class, output directory, time budget, mode,
JUnit 4 format, and summary export. Those settings, their short aliases, help,
version, and argument-response files cannot be passed through `arguments`.
Other options are validated by MAZE. Unknown experiment fields are rejected.
The old positional settings and `orig-runtool` editing workflow have been removed.

## Run and score experiments

From `tools/maze`, with the environment above:

```sh
./run_benchmarks.sh 10 10 experiments/bfs-symbolic.json /research/depth-symbolic.json
contest_transcript_single.sh .
score.sh results.tmp score
```

The first two arguments are seconds per class and repetition count. Each named
experiment gets `results_maze-<name>_<budget>/`, with one subdirectory per subject
and repetition. The script runs generation and metrics for each configuration.
Duplicate names and existing result directories are rejected before starting.
Repeat the command with budget `60` for a separate comparison. Keep all engine
settings consistent across variants except those being compared.

For individual stages:

```sh
export MAZE_EXPERIMENT=/research/depth-symbolic.json
contest_generate_tests.sh maze-depth-symbolic 10 1 10
contest_compute_metrics.sh results_maze-depth-symbolic_10
contest_transcript_single.sh results_maze-depth-symbolic_10
score.sh results.tmp score
```

Keep `MAZE_HOME`, `MAZE_EXPERIMENT`, and `MAZE_JAVA_HOME` available when computing
metrics. Score output includes `detailed_score.csv`, `score_per_subject.csv`, and
statistical comparisons; see the [infrastructure documentation](../infrastructure/README).
Aggregating `.` includes completed experiments from multiple budgets and tools.

### Completion and failures

Each generation attempt has a new batch identity. JUGE archives each class’s tests
and timing separately, and computes metrics from working copies of those archives.
The adapter creates a fresh
output directory for every MAZE invocation, requires exit status zero and a
matching `completed` record, then publishes the Java tests for JUGE. Logs and
partial output remain under `temp/maze-run-*/` for diagnosis. The batch record
includes the exact experiment arguments, MAZE JAR hash, invocation identities,
and hashes of the MAZE records (which contain plugin identities and search options).

`GENERATION_FINISHED.txt` is written only after a successful JUGE process and a
complete matching batch. Failure creates `GENERATION_FAILED.txt` and a nonzero
script exit. Metrics and transcript aggregation independently verify completion;
stale records, changed records or archived tests, unsuccessful processes, and
incomplete metrics are excluded. Failed experiments do not contribute zero-coverage scores. Inspect
failures before comparing experiments with missing repetitions.

### Historical benchmark results

The original study used symbolic DFS, BFS, SGS, RPS+COS, FOS, and FOS+COS, with
minimization enabled, path-length coverage `0`, target-path aging `0`, maximum
depth `400`, maximum array size `10`, normal floating-point constraints, and
explicit division-by-zero checks. It used ten repetitions at 10 and 60 seconds,
with two CPUs and 4 GiB of memory.

Results and raw data are attached to this repository's releases. To reproduce
those historical results, use the corresponding historical MAZE/JUGE revisions.
The current adapter uses the new CLI and allows new comparisons; changes to MAZE
can affect results, so a current run should not be described as an exact replay of
an old release.

## Validate the integration

The development image includes Java 21 for MAZE, Java 8 for JUGE's legacy metric
tools, and Python. It runs on either Linux architecture supported by MAZE. Build
it and check the adapter without downloading dependencies during the test:

```sh
docker build -f maze_runtool/Dockerfile -t juge-maze-check .
docker run --rm --network none -v "$PWD:/juge" \
  -v /absolute/path/to/unpacked-maze:/opt/maze:ro -e MAZE_HOME=/opt/maze \
  juge-maze-check sh maze_runtool/verify.sh
```

Select a package matching this container's architecture: on Apple Silicon, use
the **arm64** release asset for this development image. The full image described
earlier still requires **amd64**. The checks compile
separate extensions, exercise built-in/strategy/heuristic/composed configurations
in both modes, compile and run generated JUnit suites, and exercise multi-class
protocol handling and rejection of failed/stale experiments.

To also run the actual JUGE generation, JaCoCo coverage, PIT mutation analysis,
and transcript aggregation, first build the runner and populate a Maven cache:

```sh
docker run --rm -v "$PWD:/juge" -v juge-maven:/root/.m2 juge-maze-check sh -c '
  mvn -B -ntp -N install &&
  mvn -B -ntp -f runtool/pom.xml install &&
  mvn -B -ntp -f benchmarktool/pom.xml package'
docker run --rm --network none -v "$PWD:/juge" -v juge-maven:/root/.m2 \
  -v /absolute/path/to/unpacked-maze:/opt/maze:ro -e MAZE_HOME=/opt/maze \
  juge-maze-check sh maze_runtool/verify.sh --pipeline
```

This checks two target classes for each of six configurations: a shipped baseline,
an external strategy, and an external heuristic in both modes. Each must produce
compilable suites, positive coverage and mutation scores, and a separate transcript
row for each class. A failing extension must never reach metrics or aggregation.
Failed checks retain their working files under `maze_runtool/target/`.

These development-image checks exercise the real runner and metric libraries.
The full Linux x86-64 image has also been checked separately with the published
MAZE v1.2.0 package: BFS symbolic, an external strategy, and BFS concrete ran over
BinarySearch and TriangleClassifier with a five-second budget and one repetition.
All six results produced compilable tests, positive coverage and mutation metrics,
and R scoring outputs, including comparison reports and final rankings. This ran
with two CPUs and 4 GiB of memory under emulation on Apple Silicon.

That smoke test establishes the setup works; it does not validate the full corpus
or provide a statistically meaningful comparison of strategies.

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
- Added Z3 installation to the Dockerfile, for the original MAZE setup; packaged MAZE now supplies its own native libraries.
- Added a runtool implementation for Maze according to the format required by the JUGE framework.
- Added a runtool implementation for Kex according to the format required by the JUGE framework.
- Added a runtool implementation for T3 according to the format required by the JUGE framework.
- Other minor changes to fix issues with the framework or make things easier to use.

The benchmark subjects were added in the `benchmarks_maze` directory, see the [README](/infrastructure/benchmarks_maze/README.md) in that directory for details. If you want to put in other subjects, keep in mind that they should be compiled in Java-8 so they can be instrumented by Jacoco for coverage measurement and targetted by PIT for mutation test. Possibly some higher version of Java would also work (to compile the subjects), I haven't checked. In general, keep in mind what the requirement of Jacoco, PIT, and the testing tools you use for comparison with regards to the needed Java version.

## Coverage and mutation controls

Benchmark runners can select coverage-only measurement or full mutation
enumeration with these opt-in JVM properties:

- `-Dsbst.benchmark.skipMutation=true` skips PIT for coverage-only runs. Mutation
  fields in those transcripts are placeholders, not measured zero scores.
- `-Dsbst.benchmark.allMutants=true` disables the legacy half/third sampling for
  subjects with more than 200/400 mutants. PIT's default mutator set is unchanged.

Both default to false, preserving existing commands. JUGE's effective mutation
denominator still excludes ignored mutants; retain the generated and ignored
counts from `mutation_results.txt` alongside the transcript denominator.
