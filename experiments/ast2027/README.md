# AST 2027 experiments

Reproduce the MAZE search-strategy and tool-comparison experiments with this
JUGE fork. The host requires Docker and Python 3.9+.

The engine is checksum-pinned **MAZE 1.2.2**. The runner uses Linux AMD64 for all
four tools (emulated on ARM hosts), two CPUs and 4 GiB per sequential run. Read
[methodology and limitations](docs/methodology.md) before interpreting results.

## Prepare and check

From the JUGE repository root, choose fresh output directories:

```sh
python3 tools/seeded/provision.py --output "$PWD/local/ast2027/tools"
python3 experiments/ast2027/bench.py prepare \
  --results "$PWD/results/ast2027" --purpose production \
  --tools "$PWD/local/ast2027/tools/tools.json"
```

Provisioning downloads pinned upstream releases/source and builds the seeded
adapters. Preparation builds JUGE, downloads the MAZE package, compiles the frozen
subjects with Java 8, and freezes tool binaries, scripts, configuration, hashes
and the container image identity. Existing directories are not overwritten.

Use the copied runner for subsequent commands:

```sh
RESULTS="$PWD/results/ast2027"
RUNNER="$RESULTS/suite/bench.py"
python3 "$RUNNER" smoke --results "$RESULTS" --experiment A
python3 "$RUNNER" smoke --results "$RESULTS" --experiment B
```

A preflight checks 34 runs: every strategy and two seeds on BinarySearch, BFS on
all subjects at 10 seconds, and a MAZE mutation-measurement run. B checks 16 runs:
two subjects, two seeds, all four tools at 60 seconds. These runs are separate
from production. Reference subjects BinarySearch/TriangleClassifier must produce
measured results; other A stress subjects may yield verified timeout/empty
outcomes. Unresolved errors fail the gate. Each successful preflight writes a
certificate tied to the frozen environment. B preflight uses BFS just for checking
the pipeline, independently of the later strategy selection.

A short command-path check after preflight is:

```sh
python3 "$RUNNER" run --results "$RESULTS" --experiment A --max-runs 1
python3 "$RUNNER" status --results "$RESULTS"
```

That command creates a production row. For a disposable rehearsal, use a separate
production-purpose directory, label it as validation, and never combine its rows
with the paper dataset.

## Run, inspect and resume

```sh
python3 "$RUNNER" run --results "$RESULTS" --experiment A
python3 "$RUNNER" status --results "$RESULTS"
python3 "$RUNNER" analyze --results "$RESULTS"
```

A has 2,800 runs (20 subjects × seven treatments × two budgets × ten repetitions).
Once all A outcomes are scoreable, analysis writes `selection.json`: the treatment
with the highest unweighted mean of subject means at 60 seconds. Then run B:

```sh
python3 "$RUNNER" run --results "$RESULTS" --experiment B
python3 "$RUNNER" analyze --results "$RESULTS"
```

B has 800 runs (20 subjects × four tools × ten repetitions at 60 seconds). Five
repetitions can be selected with `prepare --b-repetitions 5` before freezing.
A full matrix can take longer than one night. There is no session time limit by
default: each command continues until its phase is complete, a stop is requested,
or an operational guard stops it. An optional `--hours` limit stops starting
further rows after that duration; the current row can finish after the limit.

`status` returns measured, timeout, empty, unresolved/excluded and pending counts,
completed repetitions, the active run and stop state. `progress.log` records run
starts/completions and interventions. Poll `status` for monitoring.

```sh
python3 "$RUNNER" stop --results "$RESULTS"
python3 "$RUNNER" resume --results "$RESULTS" --experiment A
```

Stop preserves completed results, terminates the active container and retains its
incomplete attempt. Resume
retries incomplete/missing/unverifiable rows and skips verified terminal outcomes.
A lock prevents overlapping writers. Low disk space (default 5 GiB) or three
consecutive unresolved failures stop further runs. Investigate before restarting.
`--retry-excluded` is only for diagnosed transient failures, preserving attempts
and seeds; it does not retry timeout/empty outcomes to improve a score.

Changes to tools, settings, subjects or frozen scripts require a fresh environment.
Never edit `env`, `suite` or `manifest.json` inside an existing results directory.
A/B use outer watchdogs of 300/1,800 seconds including metrics; JUGE separately
allows twice the nominal generation budget for READY.

## Results and analysis

Analyze after the running command finishes. Analysis verifies raw evidence and
rebuilds `runs.csv` and `stats/` without rerunning tools. The primary tables include
confirmed tool timeouts and verified empty output as zero delivered effectiveness.
`stats/successful-only/` provides the measured-runs-only comparison. Infrastructure,
measurement, ambiguous tool errors, interrupted and corrupt/missing records remain
unresolved, never automatic zeros. Raw counts are never fabricated for zero outcomes.

`stats/outcomes.csv` reports every planned cell's measured/timeout/empty/unresolved/
pending counts and scoring denominator. `stats/availability.json` lists missing
and unresolved IDs. Partial tables are provisional. See the methodology for the
selection rule, statistical conventions and limitations.

The manifest records repository provenance, seeds, resources and outcome policy.
Each attempt retains commands, tool completion evidence, generated tests, metric
reports and logs; published run records hash that evidence. Archive the entire
results directory because immutable dependencies are shared through relative
symlinks. `local/` and `results/` are ignored by Git.

To preserve a completed or paused run, stop writers, export its image, then archive:

```sh
IMAGE=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["image"])' "$RESULTS/manifest.json")
docker image save "$IMAGE" | gzip > "$RESULTS/container-image.tar.gz"
tar -czf ast2027-results.tar.gz -C "$(dirname "$RESULTS")" "$(basename "$RESULTS")"
shasum -a 256 ast2027-results.tar.gz > ast2027-results.tar.gz.sha256
```

Publish the archive as a release/research artifact and identify the JUGE revision.
On another machine, extract it, `docker load -i container-image.tar.gz`, and run
its copied `suite/bench.py analyze --results /absolute/extracted/path`. Preserve
raw failures and an operator log with any interventions. Timed generation can
vary across machines despite fixed seeds; archived-data analysis is repeatable.

## Developer checks

```sh
python3 -m unittest discover -s experiments/ast2027/tests -v
docker run --rm --platform linux/amd64 --network none \
  -e PYTHONDONTWRITEBYTECODE=1 -v "$PWD/experiments/ast2027:/suite:ro" \
  maze-ast2027:amd64 python3 -m unittest discover -s /suite/tests -v
```

The host skips SciPy-dependent checks if it lacks SciPy. The image runs all tests.
With a prepared directory mounted as `/results:ro`, also run
`/suite/tests/check_mutation_policy.py` and `/suite/tests/check_juge_protocol.py`.
These synthetic checks verify full PIT enumeration and rejection of partial
output from a generator which fails the protocol. They are not paper observations.
