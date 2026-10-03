# AST2027 methodology and audit

The campaign pins the supplied MAZE archive, including its version and hash.
The exploration-reserve fix enforces phase deadlines in Z3 and retains the
final 30% of the symbolic budget for unfinished-path generation. Bounded
candidate replay remains enabled. These limits are engine behavior shared by all MAZE treatments.
They do not guarantee termination of arbitrary subject/library execution.

## Fixed experimental choices

- Twenty synthetic subjects are snapshotted under `subjects/`; their provenance
  is recorded there. No subject is removed for being difficult. A uses DFS, BFS,
  SGS, RPS, COS, FOS and FOS+COS at 10/60 seconds, ten repetitions. B compares the
  fixed MAZE FOS+COS treatment with T3, EvoSuite and Kex at 60 seconds, ten repetitions.
- MAZE runs symbolically with minimization, depth 400, replay bound 10,000,
  array bound 10, path-length coverage 0, target aging 0, normal floating-point
  constraints and division-by-zero checking. FOS+COS starts with FOS and uses
  MAZE's existing time slices. Settings are explicit in `common.py`.
- Seeds derive from subject/budget/repetition and are paired across treatments
  and tools. Campaign run order is shuffled once with a recorded seed and frozen in the manifest. Host load,
  emulation and thermal drift can affect time-limited search. Record interruptions
  and relevant host changes. Seeds do not guarantee identical generated suites.
- T3 is built from unmodified upstream source. Its existing T3Random API receives
  the scheduled seed, but Worklist's separate random generator remains unseeded.
  T3 repetitions therefore include uncontrolled Worklist randomness; the recorded
  seed is insufficient to replay all random choices, even on the same machine.
- All tools use Linux AMD64 because Kex's native solver requires it; this is
  emulated on ARM hosts. Per-row CPU/memory limits and stage concurrency are frozen at preparation; defaults
  are two CPUs and 4 GiB. MAZE's heap is 2500 MiB and JUGE's is 1500 MiB. Other tool/executor heap settings are in their wrappers.
  Equal container limits do not imply equal per-process heaps.
- MAZE uses Java 21; subjects and legacy measurement tools use Java 8. Preparation
  records their versions and hashes. The actual image must be archived for exact
  reuse: apt-installed packages are not fully version-locked for future rebuilds.
- Tool versions, source patches, seed mapping and phase budgets are documented in
  `tools/seeded/README.md` and frozen wrappers. In particular, T3's upstream JUnit
  execution can return without a verdict after its ten-second wait: retained as
  an explicit limitation, not silently corrected in this study. T3 methods can
  aggregate many traces; method counts are not comparable independent-test counts.

## Measurements and outcome policy

JUGE measures JaCoCo branch outcomes (`conditionsCovered/conditionsTotal`). Use
raw integer counts rather than rounded percentage strings. A skips mutation;
its mutation placeholders are not measurements. B uses PIT 1.1.11 default mutators
with full enumeration, disabling historical half/third sampling on large subjects.
The effective mutant denominator excludes ignored mutants. Campaigns use a fresh
Java 8 JVM per mutant. The common child allowance is
`min(3600s, max(180s, 30s + 10s * test-class count + sum(test-method timeouts)))`;
Methods without an explicit timeout use JUGE's existing five seconds, and explicit
timeouts remain unchanged. Startup and class-fixture allowances cover JVM setup
and generated replay/fixture waits. Each child's `budget.json` records the counts
and allowance. The entire mutation stage retains its 3600-second cap; deadlines
remain unresolved. This replaces the fixed 180-second child cap, which could
expire during ordinary sequential timeouts in large suites. It applies equally
to all tools. JUnit timeout-only/flaky-only failures are ignored consistently even
when other tests pass. A missing child result or classloading/setup error makes
the measurement incomplete; it is never an invented kill. Mutated bytecode
precedes other subject copies on the mutation classpath. Retain generated,
ignored and effective counts; report denominator differences across runs/tools.

JUnit 4.12 timeouts and evidenced generated-test `InterruptedException` failures
are retained as non-killing evidence, rather than misclassified as kills or
operator stops. Without another killing failure the mutant is ignored. This
correction can change ignored denominators; report the harness revision. Timed-out
threads can remain active within a mutant child; exiting or terminating that JVM
prevents leakage into later mutants. T3's engine and ten-second wait remain unchanged.

Primary analysis includes measured outcomes and gives zero delivered coverage/kill
to confirmed generator process failures, generation timeouts and verified
successful empty outputs. This is
an analysis convention about usable output, not a claim that partial output had
no coverage. No synthetic mutant or branch counts are assigned to these outcomes.
Timeout classification requires a JUGE/adapter deadline and matching evidence
that the tool actually started; a startup/protocol error alone is insufficient.
MAZE evidence must match the target, seed, mode and packaged JAR hash. External
receipts match tool version, target, seed and budget. Empty output requires normal
completion and configuration/seed checks first.

Infrastructure failures, metric failures, tool errors of unresolved cause,
and missing/corrupt records are not zeroed. They block complete analysis
until diagnosed. Interrupted attempts remain retryable, not observations.
Successful-only statistics are explicitly secondary. Both views retain sample
sizes; `outcomes.csv` shows denominators and failure categories for every cell.
Do not retry legitimate timeouts or empty outcomes seeking a better result.

B always uses MAZE FOS+COS, chosen a priori and frozen in `b_treatment_policy`.
A results do not choose or change B's treatment. A and B generation can both
finish before any measurement. `selection.json` records the fixed configuration;
it is not an empirical winner selection. Archived manifests without this policy
retain their former A-dependent rule and must not be mixed with this campaign.
Higher measurement concurrency can still affect timeouts and ignored denominators;
freeze and validate it even when generation has finished.

## Statistical conventions

Fractions are in [0,1]; spread .10 means ten percentage points. SD uses n−1,
undefined at n=1. Quartiles use linear interpolation. Tied means count all winners;
rank ties use midranks. Every table includes sample/subject counts.

Mann–Whitney U is two-sided, asymptotic with tie/continuity correction. A12=U/(n1*n2)
is oriented best vs runner-up, or composition vs component. These comparisons are
exploratory: p-values are unadjusted, best/runner-up are selected on the same data,
and the test does not use the paired seed schedule.

Friedman uses complete subject blocks of treatment means; Nemenyi uses alpha .05,
studentized-range infinite-df / sqrt(2). Publish the omnibus with post-hoc results.
Partial cells/blocks are reported with their actual n; final claims require a
complete or explicitly accounted-for dataset. B overall means weight available
subjects equally, and best counts require all four tools represented.

Subject characteristics use JaCoCo on frozen bytecode, including private methods
and constructors of the CUT, excluding nested classes. Physical LOC includes
blank/comment lines. `feature-tags.json` is hand-assigned descriptive metadata.

## Recording changes and interventions

Keep preflight, diagnostic and rehearsal runs separate from the paper dataset.
Run fresh preflights for each frozen environment.

Record each change or intervention with its date, reason, affected settings,
validation and disposition of prior attempts in the results' `operator-log.md`.
Report these details alongside completion counts. Never alter frozen raw evidence.


## Stage and retry policy

Generation, coverage and mutation have independent checkpoints. No statistical
analysis runs during generation. Coverage measurement of A must precede B's
MAZE generation because it determines the selected strategy. Saved suites are
measured in fresh working copies; metric failures never trigger regeneration.

The generation deadline follows JUGE's documented twice-budget allowance for
pre/post-processing, while each generator still receives its nominal internal
budget. See [JUGE, sections 3.2 and 4.3](https://arxiv.org/pdf/2106.07520).
The protocol, JaCoCo/PIT metrics and composite-score calculation remain in place.
Partial output from failed generation is archived but is not substituted into
primary results. This is a delivered-output policy, not a claim about its latent
coverage. No generator source is patched to improve completion rates.

A proven container-start failure can be retried once automatically. An ambiguous
missing receipt cannot. Measurements may be retried once using the identical
suite; the first complete verified measurement is retained. All attempts survive.
Explicit user interruption is recorded separately and may be resumed. Unresolved
cases block a completed campaign rather than being relabelled as tool failures.

Concurrent containers still share caches, memory bandwidth and thermal limits.
The frozen resource check prevents obvious oversubscription; the target-machine
rehearsal must establish acceptable contention. Keep the host idle during timed
generation and report the hardware and concurrency. Measurement also needs
adequate resources because it executes tests under deadlines. Offline statistics
have no influence on previously generated suites.
