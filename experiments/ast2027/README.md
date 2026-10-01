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

## Prepare

Choose a tested Linux AMD64 MAZE distribution containing the exploration-reserve
fix (1.2.3 or its development snapshot). A local archive is copied and hashed;
no unpublished GitHub release is assumed. Build it with MAZE's documented
`distribution/build.sh` workflow if a published archive is unavailable.

From this JUGE checkout:

```sh
python3 tools/seeded/provision.py --output "$PWD/local/ast2027/tools"
python3 experiments/ast2027/bench.py prepare --campaign \
  --results "$PWD/results/ast2027" --purpose production \
  --maze-package /absolute/path/to/maze-linux-amd64.tar.gz \
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

`run` performs A generation, A coverage, B generation, B coverage, then B mutation.
It selects the MAZE configuration after A coverage, using the frozen selection
rule; this dependency prevents generating B's MAZE tests before A is measured.
Generation and measurement never overlap within a campaign. A has 2,800 cases;
B has 800 by default. There is no overall session time limit and no statistics
export during the campaign.

For explicit control over the stage boundary:

```sh
python3 "$RESULTS/suite/campaign.py" generate --results "$RESULTS" --experiment A
python3 "$RESULTS/suite/campaign.py" measure --results "$RESULTS" --experiment A
python3 "$RESULTS/suite/campaign.py" generate --results "$RESULTS" --experiment B
python3 "$RESULTS/suite/campaign.py" measure --results "$RESULTS" --experiment B
```

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
available cgroup memory/CPU counters. No monitoring agent is required to execute
the queue; launch it in a persistent terminal/session if closing its parent shell.

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

Stop writers, save the image, then archive the directory:

```sh
IMAGE=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["image_tag"])' "$RESULTS/manifest.json")
docker image save "$IMAGE" | gzip > "$RESULTS/container-image.tar.gz"
tar -czf ast2027-results.tar.gz -C "$(dirname "$RESULTS")" "$(basename "$RESULTS")"
shasum -a 256 ast2027-results.tar.gz > ast2027-results.tar.gz.sha256
```

Publish the archive and identify both source revisions and the engine archive hash.
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
