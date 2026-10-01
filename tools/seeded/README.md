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
  `a12cf1a3b1b7149566cf6dbb80e43eabdbb70041`, archive SHA-256 checked. Built for
  Java 8 from unmodified upstream source. `SeededT3.java` calls Gen2 directly,
  avoiding the upstream SBST entry point's unconditional failure exit, and seeds
  T3Random through its existing API. Worklist retains its separate unseeded RNG:
  the recorded seed does not control all T3 randomness, so repeated invocations
  with the same seed may differ. Gen2 receives budget minus two seconds (minimum one),
  with the wrapper deadline at twice the nominal budget. Settings include coverage guidance,
  regression oracles and private/default members; all are visible in the wrapper.
  Traces are retained for replay. Upstream generated JUnit can silently return
  after a ten-second execution wait; this limitation affects interpretation.

These adapters report READY only after normal seeded generation, including valid
empty output. `invocation.json` records tool/version/target/seed/budget after the
process starts; `timeout.json` records an adapter deadline. `termination.json` records the process exit and elapsed wall time, including failed attempts. Neither claims a
successful generated suite. JUGE/experiment code decides how outcomes are scored.

Provisioning builds the small Java 8/21/Python image in
`experiments/ast2027/Dockerfile`. Downloads and build outputs stay outside tracked
source directories.

Adapter process checks: `python3 -m unittest discover -s tools/seeded/tests -v`.

Kex internal per-trace error messages are retained as diagnostics, not interpreted
as a fatal generator exit. A nonzero native process exit still fails generation.
No Kex, EvoSuite or T3 engine source is modified by these adapters.
