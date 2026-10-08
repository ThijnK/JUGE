# Provisioned seeded tool adapters

`python3 tools/seeded/provision.py --output /absolute/fresh/directory` produces
self-contained tool directories and a `tools.json` inventory for single-target
JUGE invocations, as used by the experiment runner. Kex explicitly rejects batches
with multiple targets; use one isolated invocation per class.
Legacy `tools/<tool>/runtool` deployments remain available for historical workflows.
The new adapters share `generation.py` for invocation evidence, deadlines and
process-group cleanup, and read a required unsigned 32-bit `JUGE_TOOL_SEED`.
Use the generated tool directories with JUGE; source templates alone lack binaries.

- **EvoSuite 1.2.0:** official release JARs, SHA-256 checked; DynaMOSA, `-seed`,
  Java 8. Half the budget is search; the other half is divided across setup,
  assertions and checks. Minimization/inlining are disabled. The complete command
  is retained in `tool-command.json`. Adapter deadline: twice the nominal budget, matching JUGE’s global allowance.
- **Kex 0.0.11:** official distribution, SHA-256 checked; concolic, one executor
  and worker, scheduled easy-random seed and SMT seed masked to 31 bits. Native
  solvers require Linux AMD64. Internal timeLimit is the requested budget;
  adapter deadline is twice the nominal budget, alongside JUGE’s READY deadline.
  Exact overrides are retained in `temp/kex.ini` and `kex-command.json`.
- **T3:** [author source](https://git.science.uu.nl/prase101/t3), pinned revision
  `a12cf1a3b1b7149566cf6dbb80e43eabdbb70041`, archive SHA-256 checked.
  The adapter follows the author's JUGE runtool (`cbae18cd`): upstream
  `G2_forSBST generate`, random worklist, evo refinement, five refinements,
  coverage guidance on, static information off, and the full nominal budget.
  Upstream supplies the budget + ten-second watchdog and the remaining settings.
  Four integration differences are retained:
  1. Unmodified source is built for Java 8, because the author's Java 11 JAR
     cannot load in JUGE's Java 8 measurement JVM; generated tests import T3.
  2. A minimal wrapper seeds the existing `T3Random` API before calling upstream.
     `WorklistRandom` uses the separate `new Random()` inherited from `Worklist`,
     which remains unseeded. The recorded seed does not control all randomness.
  3. Traces use a per-run directory rather than `/home/t3/traces/`.
  4. Upstream exits -1 (255 on Linux) on completion and watchdog expiry. That exit
     alone is not a failure when saved tests exist. `t3-outcome.json` records
     completion, upstream watchdog, adapter timeout or failure and saved sources.
     A crash without output is a failure; exceeding twice the nominal budget
     remains a tool timeout. Fatal main-thread exceptions are not accepted.
  Traces are retained for replay. Upstream generated JUnit can silently return
  after a ten-second wait; this limitation remains unchanged.

These adapters report READY after accepted seeded generation, including valid
empty output. T3 also accepts saved suites from its upstream watchdog exit. `invocation.json` records tool/version/target/seed/budget after the
process starts; `timeout.json` records an adapter deadline. `termination.json` records the process exit and elapsed wall time, including failed attempts. Neither claims a
successful generated suite. JUGE/experiment code decides how outcomes are scored.

Provisioning builds the small Java 8/21/Python image in
`experiments/ast2027/Dockerfile`. Downloads and build outputs stay outside tracked
source directories.

Provisioning checks host Python/Docker/storage prerequisites before building and
records `host-machine.json`. T3 builds use the invoking Linux UID/GID and a local
Maven cache, without leaving root-owned tool files. Use the same Python 3.9+
interpreter for provisioning and campaign commands. Host installation and power
or VM configuration changes remain explicit operator actions.

Adapter process checks: `python3 -m unittest discover -s tools/seeded/tests -v`.

Kex internal per-trace error messages are retained as diagnostics, not interpreted
as a fatal generator exit. A nonzero native process exit still fails generation.
No Kex, EvoSuite or T3 engine source is modified by these adapters.
