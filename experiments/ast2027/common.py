"""Shared serialization, matrix and integrity rules. No third-party dependencies."""
import csv
import hashlib
import json
import os
from pathlib import Path
import tempfile
import statistics

SUBJECTS = 'AckermannPeter BinarySearch BinaryTree BitwiseManipulator BracketBalancer ConnectedComponents ConvergingPaths Dijkstra ExprEvaluator FloatStatistics GraphTraversal HeapSort IntUtils MatrixAnalyzer NestedLoops QuickSort SinglyLinkedList StringPatternMatcher StringUtils TriangleClassifier'.split()
BASE = ['DFS', 'BFS', 'SGS', 'RPS', 'COS', 'FOS']
TREATMENTS = BASE + ['FOS+COS']
OPTIONS = ['--minimization=true', '--max-depth=400', '--max-replay-steps=10000', '--max-array-size=10', '--path-length-coverage=0', '--target-path-aging=0', '--constrain-fp-params-to-normal-numbers=true', '--check-division-by-zero=true']
B_TREATMENT_POLICY = dict(version=1, mode='fixed', treatment='FOS+COS')


def required_certificates(spec):
    """An explicit frozen operator waiver never becomes a preflight pass."""
    full = ('preflight.json', 'preflight-B.json', 'rehearsal.json')
    policy = spec.get('validation_policy')
    if policy is None:
        return full
    if policy.get('version') != 1 or policy.get('rehearsal') != 'required':
        raise ValueError('Unsupported frozen validation policy')
    if policy.get('full_preflights') == 'required':
        return full
    if policy.get('full_preflights') == 'operator_waiver' and isinstance(policy.get('reason'), str) and policy['reason'].strip():
        return ('rehearsal.json',)
    raise ValueError('A full-preflight waiver requires an explicit recorded reason')

MEASUREMENT_POLICY = dict(version=3, isolated_mutants=True, total_seconds=3600,
    child_budget=dict(policy='suite-v1', minimum_seconds=180, startup_seconds=30,
                      fixture_seconds_per_class=10, default_test_timeout_seconds=5),
    non_killing='evidenced JUnit timeout/interruption-only or flaky-only failures: ignored; passing siblings do not imply survival',
    incomplete='missing/null child results, process deadlines, classloading/setup errors: unresolved')


OUTCOME_POLICY = {
    'version': 1,
    'primary': 'failure-inclusive',
    'measured': 'use verified coverage and mutation fractions',
    'tool_timeout': 'zero delivered coverage/kill; confirmed generation deadline with invocation evidence',
    'empty': 'zero delivered coverage/kill; verified successful generation with no Java tests',
    'excluded': 'unresolved infrastructure, measurement, tool errors or ambiguous failures; no imputation',
    'missing': 'pending or unverifiable; no imputation',
    'secondary': 'measured successful runs only',
}


def scoreable(record):
    return record is not None and record['status'] in ('ok', 'tool_timeout', 'tool_failure', 'empty')


def scored(record):
    """Analysis convention, not fabricated raw measurements or denominators."""
    if record['status'] == 'ok':
        return record
    if not scoreable(record):
        raise ValueError('Unresolved outcome cannot be scored')
    return dict(record, coverage=0., mutation_kill=0., mutant_count=None,
                mutants_generated=None, mutants_ignored=None)


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def fingerprint(root):
    return {str(p.relative_to(root)): digest(p) for p in sorted(Path(root).rglob('*')) if p.is_file() and '__pycache__' not in p.parts}


def identity(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def atomic(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix='.' + path.name, dir=path.parent)
    try:
        with os.fdopen(fd, 'w') as f:
            json.dump(value, f, indent=2, sort_keys=True, allow_nan=False)
            f.write('\n')
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
        directory = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def read(path):
    return json.loads(Path(path).read_text())


def matrix(b_repetitions=10):
    rows = []
    for experiment, repetitions in [('A', 10), ('B', b_repetitions)]:
        for repetition in range(1, repetitions + 1):
            for subject in SUBJECTS:
                for budget in ([10, 60] if experiment == 'A' else [60]):
                    for treatment in (TREATMENTS if experiment == 'A' else ['MAZE', 'T3', 'EvoSuite', 'Kex']):
                        key = f'{experiment}-{repetition:02d}-{subject}-{budget}-{treatment.replace("+", "_")}'
                        # Paired seed schedule across treatments/tools; varies across repetitions.
                        seed = int(hashlib.sha256(f'AST2027:{subject}:{budget}:{repetition}'.encode()).hexdigest()[:8], 16)
                        rows.append(dict(id=key, experiment=experiment, repetition=repetition, subject=subject,
                                         budget=budget, treatment=treatment, tool='MAZE' if experiment == 'A' else treatment,
                                         kind=('combinator' if treatment == 'FOS+COS' else 'base') if experiment == 'A' else 'tool', seed=seed))
    return rows


def valid_record(root, run, manifest_id):
    """Return only terminal records with matching coordinates and intact evidence."""
    try:
        record = read(root / 'runs' / (run['id'] + '.json'))
        if record.get('record_sha256') != identity({k: v for k, v in record.items() if k != 'record_sha256'}):
            return None
        if record['run'] != run or record['manifest_id'] != manifest_id or record['status'] not in ('ok', 'excluded', 'tool_timeout', 'tool_failure', 'empty'):
            return None
        evidence = record['evidence']
        if not evidence or any(digest(root / p) != h for p, h in evidence.items()):
            return None
        return record
    except (OSError, ValueError, KeyError, TypeError):
        return None


def write_csv(path, rows):
    rows = list(rows)
    fields = list(dict.fromkeys(k for row in rows for k in row))
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix('.csv.tmp')
    with temp.open('w', newline='') as f:
        writer = csv.DictWriter(f, fields)
        writer.writeheader()
        writer.writerows({k: json.dumps(v, sort_keys=True) if isinstance(v, (list, dict)) else v for k, v in row.items()} for row in rows)
        f.flush()
        os.fsync(f.fileno())
    os.replace(temp, path)


def selection(root, spec):
    """Resolve the frozen B policy; retain the former rule for archived manifests."""
    if 'b_treatment_policy' in spec:
        if spec['b_treatment_policy'] != B_TREATMENT_POLICY:
            raise ValueError('Unsupported frozen B treatment policy')
        return dict(manifest_id=spec['id'], treatment='FOS+COS', kind='combinator',
                    source='fixed', rule='FOS+COS chosen a priori; independent of A outcomes')
    values = {}
    for row in spec['runs']:
        if row['experiment'] != 'A':
            continue
        record = valid_record(root, row, spec['id'])
        if not scoreable(record):
            return None
        values.setdefault((row['subject'], row['budget'], row['treatment']), []).append(scored(record)['coverage'])
    if not all(len(values.get((s, b, t), [])) == 10 for s in SUBJECTS for b in (10, 60) for t in TREATMENTS):
        return None
    scores = {t: statistics.mean(statistics.mean(values[s, 60, t]) for s in SUBJECTS) for t in TREATMENTS}
    winner = max(TREATMENTS, key=scores.get)
    return dict(manifest_id=spec['id'], treatment=winner, kind='combinator' if winner == 'FOS+COS' else 'base', scores=scores, rule=spec['selection_rule'])


def b_treatment(root, spec):
    """New B workers need no A data or selection file; reject conflicting records."""
    path = root / 'selection.json'
    if 'b_treatment_policy' in spec:
        expected = selection(root, spec)
        if path.exists() and read(path) != expected:
            raise ValueError('B treatment record conflicts with the frozen fixed policy')
        return expected['treatment']
    return read(path)['treatment']
