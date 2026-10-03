# AST 2027 experiments

The campaign generates and archives tests first, measures the saved suites in
separate phases, and exports statistical analysis only when requested. Each
planned case gets one generation attempt. Confirmed generator failures and
verified empty output contribute zero delivered effectiveness; measurement and
infrastructure errors are kept distinct.

Use Docker and Python 3.9+ on Linux/macOS, or inside WSL2 on Windows. Store the
checkout and results in the WSL Linux filesystem, not `/mnt/c`. All containers
use Linux AMD64; a Ryzen desktop executes this architecture without ARM emulation.
Read [methodology](docs/methodology.md) before interpreting results.

On WSL/Linux, containers use the invoking user's UID/GID so evidence stays readable.
From Windows PowerShell, enter your usual WSL user terminal:

```powershell
wsl.exe -d Ubuntu
```

Use a Python 3.9+ interpreter for all host commands. If Ubuntu's system Python is
older, use a separate installation or virtual environment instead of replacing
the system interpreter. Check Docker availability inside that same WSL terminal.
Run the read-only prerequisite check before provisioning/preparation:

```sh
python3 experiments/ast2027/host.py --directory "$PWD/results/ast2027" \
  --generation-jobs 1 --measurement-jobs 1 --cpus 2 --memory-gb 4
```

Preparation checks these prerequisites automatically and saves `host-machine.json`
with Python, hardware, actual Docker capacity/context, filesystem, competing
processes and, on WSL, Windows/WSL and power settings. The manifest hashes this
record. Review unavailable fields and record interventions in `operator-log.md`.
The running Docker engine's capacity governs the resource check. Host installation
and power/VM configuration changes remain explicit operator actions.

## Prepare

Preparation downloads the published Linux AMD64 MAZE 1.2.3 distribution and
verifies its pinned checksum. To test a different engine build, supply
`--maze-package /absolute/path/to/maze-linux-amd64.tar.gz`; the local archive is
copied and hashed into the frozen environment.

From this JUGE checkout:

```sh
python3 tools/seeded/provision.py --output "$PWD/local/ast2027/tools"
python3 experiments/ast2027/bench.py prepare --campaign \
  --results "$PWD/results/ast2027" --purpose production \
  --tools "$PWD/local/ast2027/tools/tools.json" \
  --generation-jobs 1 --measurement-jobs 1 --cpus 2 --memory-gb 4
```

Set the job counts and per-container CPU/memory limits before preparation. The
runner requires enough Docker VM capacity for the larger job count, plus at
least 1 GiB memory headroom. CPU quotas are not dedicated physical cores; pilot
under the intended load before increasing concurrency. Kex uses several JVMs
and native solver memory, so heap limits alone do not establish adequate RAM.
Swap is disabled for campaign containers. Record the desktop CPU, RAM, OS,
Docker/WSL configuration and power settings with the published artifact.

Preparation snapshots subjects, compiler/tool binaries, adapters and runner,
records hashes and the image identity, retains a unique local image tag, and
freezes a randomized run order. Keep that image tag until the campaign is archived.
Adapters must come from the same revision. Existing output directories are not
overwritten. Changing resources, tools or policies requires fresh preparation.

## Validate, then run

Always use the copied scripts:

```sh
RESULTS="$PWD/results/ast2027"
python3 "$RESULTS/suite/bench.py" smoke --results "$RESULTS" --experiment A
python3 "$RESULTS/suite/bench.py" smoke --results "$RESULTS" --experiment B
python3 "$RESULTS/suite/campaign.py" rehearse --results "$RESULTS"
python3 "$RESULTS/suite/campaign.py" run --results "$RESULTS"
```

Preflight covers every MAZE strategy and subject, all tools on reference subjects,
and B stress subjects including BitwiseManipulator, StringPatternMatcher,
FloatStatistics, StringUtils and BinaryTree. The separate rehearsal exercises
HeapSort/DFS, all four tools on BinarySearch, and T3 StringPatternMatcher using
the frozen concurrency. No preflight or rehearsal observations enter production.
Reference cases must yield measured results; confirmed tool failures on stress
cases are acceptable, but unresolved measurement/infrastructure errors are not.

Mutation children use a suite-size allowance with a 180-second minimum, bounded
by the unchanged 3600-second total measurement cap. The formula and timeout
interpretation are in [methodology](docs/methodology.md); per-child `budget.json`
preserves the calculation. Generated engines and test timeouts are unchanged.

`run` performs A generation, B generation, A coverage, B coverage, then B mutation.
B's MAZE treatment is always FOS+COS, frozen at preparation and independent of
A results. `selection.json` records that fixed choice.
Generation and measurement never overlap within a campaign. A has 2,800 cases;
B has 800 by default. There is no overall session time limit and no statistics
export during the campaign.

For explicit control over the stage boundary:

```sh
python3 "$RESULTS/suite/campaign.py" generate --results "$RESULTS" --experiment A
python3 "$RESULTS/suite/campaign.py" generate --results "$RESULTS" --experiment B
python3 "$RESULTS/suite/campaign.py" measure --results "$RESULTS" --experiment A
python3 "$RESULTS/suite/campaign.py" measure --results "$RESULTS" --experiment B
```

Each command exits after its requested stage. Generation uses `generation_jobs`;
coverage and mutation use `measurement_jobs`, both frozen before validation.
Measurement only reads saved suites and does not invoke generators. Analysis is
a separate aggregate command. Keep other work idle during generation; measurement
concurrency also needs validation because resource contention can change timeouts.

## Run unattended with periodic reports

The campaign is a normal Python program. It requires no agent or scheduled chat
monitor. After preparation, preflight and rehearsal, run it in the foreground:

```sh
python3 "$RESULTS/suite/campaign.py" run --results "$RESULTS" --progress-interval 900
```

The default interval is 900 seconds (15 minutes). Reports also appear at startup,
phase changes, and command completion, interruption or failure. They show resolved
and planned counts for each experiment and phase, outcome counts, active case IDs
and elapsed times, unresolved reasons, and free disk space. Confirmed generation
failures/empty output need no measurement and are reported as `not_required` in
measurement phases; unresolved failures stay separate from resolved results.

Reports go to the terminal and append to `progress-reports.jsonl` in the results
directory. They read small checkpoints without hashing test artifacts or invoking
Docker statistics. The coordinator checks the timer while scheduling/waiting for
workers and between verification records; reports can be delayed by a blocking
operation. Reporting does not alter retry policies or launch jobs. Status is an
informational snapshot, not evidence verification or a guarantee of worker health.
These are terminal/file reports, not chat messages or desktop notifications.

To continue after disconnecting the shell, start the validated campaign with:

```sh
nohup python3 "$RESULTS/suite/campaign.py" run --results "$RESULTS" \
  --progress-interval 900 >> "$RESULTS/campaign-console.log" 2>&1 < /dev/null &
tail -f "$RESULTS/campaign-console.log"
```

Exit `tail` with Ctrl+C; that leaves the background runner active. Use the `stop`
command below to stop the campaign. For a stopped campaign, use `resume` in the
same launch command. Keep the computer awake and Docker/WSL running. Statistical
analysis remains a separate, explicitly requested step.

## Status, stopping and recovery

```sh
python3 "$RESULTS/suite/campaign.py" status --results "$RESULTS"
python3 "$RESULTS/suite/campaign.py" stop --results "$RESULTS"
python3 "$RESULTS/suite/campaign.py" resume --results "$RESULTS"
```

Status reads small checkpoints without hashing all raw evidence during timed
experiments. Full verification happens before reuse and analysis. Stop terminates
active containers, preserving completed stages and interrupted attempts. Explicit
resume may rerun user-interrupted work, but skips successful generation and all
terminal tool failures. If the coordinator disappears, surviving containers are
not blindly restarted: let them finish, then resume to collect their results.
Untracked/missing evidence blocks execution rather than silently regenerating.

Automatic generation retry is limited to one proven container-start failure.
Tool crashes, confirmed deadlines and OOMs after confirmed tool invocation are
terminal outcomes, not reasons to seek another generated suite. Measurement may
retry once against the identical saved suite. Every attempt retains its evidence;
remaining errors require diagnosis and are never silently scored zero. The runner
captures Docker exit/OOM state before removing containers, and workers save
available cgroup v1/v2 OOM, memory-peak and CPU counters. No monitoring agent is required to execute
the queue; launch it in a persistent terminal/session if closing its parent shell.

Mutation setup failures are recorded in `MUTATION_ERROR.txt`; actual deadlines
in `TIMEOUT.txt`, with the affected mutant and cause. Both remain unresolved.
See the methodology for timeout/interruption and ignored-mutant interpretation.

## Analyze and archive

After the campaign finishes, explicitly run:

```sh
python3 "$RESULTS/suite/bench.py" analyze --results "$RESULTS"
```

This verifies evidence and creates `runs.csv`, `selection.json` and `stats/`.
Primary effectiveness includes confirmed generator failures/timeouts and empty
outputs as zero, without fabricating raw coverage/mutation counts. Successful-only
results are secondary. Coverage and mutation are separately preserved when only
one measurement succeeds. JUGE's composite score is not used by this analysis.

`stages/` contains the selected stage checkpoints; `attempts/` preserves every
attempt and output. `runs/` consolidates one row per planned case with stage
provenance. Original generation artifacts are never used as writable measurement
workspaces. Archive the complete directory because dependencies are shared through
relative symlinks. `local/` and `results/` are ignored by Git.

Stop writers, save the image, then archive the directory. In Bash, use unique
names and fail on export/compression errors:

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
  (cd "$ARCHIVE_DIR" && shasum -a 256 ast2027-results.tar.gz > ast2027-results.tar.gz.sha256)
  printf 'Verified archive: %s\n' "$ARCHIVE_DIR/ast2027-results.tar.gz"
)
```

Back up the verified archive before deleting any working data. Publish the archive
and identify both source revisions and the engine archive hash.
To reanalyze elsewhere, extract it, load the saved Docker image and use its copied
`bench.py analyze`. Seeds cannot make wall-clock-limited generation identical
across hardware. Historical sequential campaigns retain their own frozen scripts;
the parallel runner refuses to migrate their manifests.

## Developer checks

```sh
python3 -m unittest discover -s tools/seeded/tests -v
python3 -m unittest discover -s experiments/ast2027/tests -v
```

Run the experiment tests inside the benchmark image too, so SciPy-dependent
analysis checks run. Run JUGE's Maven tests under Java 8, including the isolated
mutation regressions. Real preflight/rehearsal remains necessary on the target
machine before collecting paper observations.
