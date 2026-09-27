# AST2027 methodology and audit

MAZE 1.2.2 enforces the remaining search budget in Z3 and retains
completed tests on solver deadline expiration. Version 1.2.1 added bounded
candidate replay. These limits are engine behavior shared by all MAZE treatments.
They do not guarantee termination of arbitrary subject/library execution.

## Fixed experimental choices

- Twenty synthetic subjects are snapshotted under `subjects/`; their provenance
  is recorded there. No subject is removed for being difficult. A uses DFS, BFS,
  SGS, RPS, COS, FOS and FOS+COS at 10/60 seconds, ten repetitions. B compares the
  selected MAZE treatment with T3, EvoSuite and Kex at 60 seconds, ten repetitions.
- MAZE runs symbolically with minimization, depth 400, replay bound 10,000,
  array bound 10, path-length coverage 0, target aging 0, normal floating-point
  constraints and division-by-zero checking. FOS+COS starts with FOS and uses
  MAZE's existing time slices. Settings are explicit in `common.py`.
- Seeds derive from subject/budget/repetition and are paired across treatments
  and tools. Run order is fixed, repetition-major, not randomized. Host load,
  emulation and thermal drift can affect time-limited search. Record interruptions
  and relevant host changes. Seeds do not guarantee identical generated suites.
- All tools use Linux AMD64 because Kex's native solver requires it; this is
  emulated on ARM hosts. Each row gets two CPUs and 4 GiB; MAZE's heap is 2500 MiB
  and JUGE's is 1500 MiB. Other tool/executor heap settings are in their wrappers.
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
The effective mutant denominator excludes ignored mutants. Retain generated,
ignored and effective counts; report denominator differences across runs/tools.

Primary analysis includes measured outcomes and gives zero delivered coverage/kill
to confirmed generation timeouts and verified successful empty outputs. This is
an analysis convention about usable output, not a claim that partial output had
no coverage. No synthetic mutant or branch counts are assigned to these outcomes.
Timeout classification requires a JUGE/adapter deadline and matching evidence
that the tool actually started; a startup/protocol error alone is insufficient.
MAZE evidence must match the target, seed, mode and packaged JAR hash. External
receipts match tool version, target, seed and budget. Empty output requires normal
completion and configuration/seed checks first.

Infrastructure failures, metric failures, other tool errors of unresolved cause,
and missing/corrupt records are not zeroed. They block complete analysis/selection
until diagnosed. Interrupted attempts remain retryable, not observations.
Successful-only statistics are explicitly secondary. Both views retain sample
sizes; `outcomes.csv` shows denominators and failure categories for every cell.
Do not retry legitimate timeouts or empty outcomes seeking a better result.

A-to-B selection requires all 2,800 A outcomes scoreable under the primary policy;
maximize the unweighted mean of 20 subject means at 60 seconds. Ties follow the
listed strategy order. B reuses the same subjects: this evaluates a configuration
selected on the corpus, not held-out generalization.

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
