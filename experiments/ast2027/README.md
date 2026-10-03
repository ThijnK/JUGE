# AST2027 benchmark

The campaign preserves generated suites, measures those saved suites in separate
stages, and analyzes results on request. Generation and measurement never overlap.
See [methodology](docs/methodology.md) for settings and outcome interpretation.

- A: 20 subjects, seven MAZE treatments, 10/60-second budgets, ten repetitions
  (2,800 cases).
- B: MAZE FOS+COS, T3, EvoSuite and Kex, 60 seconds, ten repetitions (800 cases).
  FOS+COS is fixed before execution; B does not depend on A results.
- Seeds are paired by subject/budget/repetition; randomized run order is frozen.
  Wall-clock budgets and uncontrolled tool randomness prevent exact reproducibility.
- Engines: MAZE 1.2.3 Linux AMD64, EvoSuite 1.2.0, Kex 0.0.11 and pinned upstream T3.
  T3 Worklist randomness remains unseeded; its generated ten-second waits remain.

## Prepare

Use Docker Linux AMD64 containers and Python 3.9+. On Windows, use WSL2 and keep
checkouts, tools and results in the Linux filesystem, not `/mnt/c`.

```sh
python3 tools/seeded/provision.py --output "$PWD/local/ast2027/tools"
python3 experiments/ast2027/bench.py prepare --campaign \
  --results "$PWD/results/ast2027" --purpose production \
  --tools "$PWD/local/ast2027/tools/tools.json" \
  --generation-jobs 1 --measurement-jobs 1 --cpus 2 --memory-gb 4
```

Preparation checks host capacity, records the machine, verifies the pinned MAZE
package checksum, and snapshots tools, subjects, adapters, scripts and image
identity. Use an unused results directory. Resources and job counts are frozen;
changes require fresh preparation. Swap is disabled. Leave Docker at least 1 GiB
memory headroom and practical headroom for the host. CPU quotas share cores and
caches; more concurrent measurements can change timeout outcomes.

## Run

Always use the copied scripts. Run each command after the previous one finishes:

```sh
RESULTS="$PWD/results/ast2027"
python3 "$RESULTS/suite/campaign.py" generate --results "$RESULTS" --experiment A
python3 "$RESULTS/suite/campaign.py" generate --results "$RESULTS" --experiment B
python3 "$RESULTS/suite/campaign.py" measure --results "$RESULTS" --experiment A
python3 "$RESULTS/suite/campaign.py" measure --results "$RESULTS" --experiment B
python3 "$RESULTS/suite/bench.py" analyze --results "$RESULTS"
```

`generate` only generates tests. `measure` reads saved suites: A coverage; B
coverage then mutation. `analyze` verifies evidence and exports `runs.csv`,
`selection.json` (the fixed B treatment) and `stats/`. Branch coverage and mutation
effectiveness are separate; the composite JUGE score is not used.

For the whole execution pipeline, use `campaign.py run --results "$RESULTS"`.
There is no overall time limit. Reports appear every 15 minutes and at stage
boundaries, in the terminal and `progress-reports.jsonl`; change the interval with
`--progress-interval SECONDS`. Keep the terminal open, the machine awake and Docker
running. No agent or monitoring service is needed. Run one coordinator at a time.

Optional sanity checks exercise strategies/subjects/tools and the configured
concurrency. They are not prerequisites for execution. Their observations stay
in separate validation directories and are excluded from production analysis:

```sh
python3 "$RESULTS/suite/bench.py" smoke --results "$RESULTS" --experiment A
python3 "$RESULTS/suite/bench.py" smoke --results "$RESULTS" --experiment B
python3 "$RESULTS/suite/campaign.py" rehearse --results "$RESULTS"
```

## Status and recovery

```sh
python3 "$RESULTS/suite/campaign.py" status --results "$RESULTS"
python3 "$RESULTS/suite/campaign.py" stop --results "$RESULTS"
python3 "$RESULTS/suite/campaign.py" resume --results "$RESULTS"
```

`resume` continues the whole pipeline. To retain separate stages, interrupt with
Ctrl+C and rerun that same `generate` or `measure` command. After `stop`, explicitly
remove its `STOP` file before continuing a single stage. Completed work is reused;
interrupted attempts remain saved. Never delete evidence to force regeneration.
If the coordinator disappears while containers survive, let them finish before
continuing to collect their results.

Confirmed generator failures/timeouts and verified empty output score zero
primary delivered effectiveness, without fabricated raw counts. Infrastructure,
measurement and ambiguous failures remain unresolved. Generation retries once
only after a proven never-started container; measurement retries once against the
identical saved suite. Keep the first complete verified measurement.

Mutation uses a fresh Java 8 JVM per mutant and a suite-size child allowance with
a 180-second minimum and 3,600-second total cap. `budget.json` records the allowance;
`TIMEOUT.txt` and `MUTATION_ERROR.txt` identify unresolved failures. Inspect
`stages/`, `attempts/`, `runs/`, `logs/` and progress reports when troubleshooting.

## Archive

After all writers stop, save the actual frozen image and archive the complete
results directory (dependencies use relative symlinks). Use unique filenames:

```sh
(
  set -euo pipefail
  IMAGE=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["image_tag"])' "$RESULTS/manifest.json")
  IMAGE_TMP=$(mktemp "$RESULTS/container-image-XXXXXXXX.tar.gz.partial")
  docker image save "$IMAGE" | gzip > "$IMAGE_TMP"
  gzip -t "$IMAGE_TMP"
  mv "$IMAGE_TMP" "${IMAGE_TMP%.partial}"
  ARCHIVE_DIR=$(mktemp -d "$(dirname "$RESULTS")/ast2027-archive-XXXXXXXX")
  tar -czf "$ARCHIVE_DIR/ast2027-results.tar.gz" -C "$(dirname "$RESULTS")" "$(basename "$RESULTS")"
  tar -tzf "$ARCHIVE_DIR/ast2027-results.tar.gz" > /dev/null
  (cd "$ARCHIVE_DIR" && sha256sum ast2027-results.tar.gz > ast2027-results.tar.gz.sha256)
  printf 'Verified archive: %s\n' "$ARCHIVE_DIR/ast2027-results.tar.gz"
)
```

Back up and verify the archive before deleting working data. Rebuilding the image
later may change installed dependencies. Include revisions, package hashes,
hardware, resource limits and operator notes with published results.
