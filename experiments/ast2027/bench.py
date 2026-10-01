#!/usr/bin/env python3
"""AST 2027: prepare, smoke, run, status, stop/resume and analyze frozen experiments."""
import argparse
from collections import Counter
from contextlib import contextmanager
import fcntl
import os
import random
from pathlib import Path
import platform
import shutil
import signal
import subprocess
import sys
import time
import uuid

from common import OUTCOME_POLICY, SUBJECTS, atomic, digest, fingerprint, identity, matrix, read, selection, valid_record

HERE = Path(__file__).resolve().parent
JUGE = HERE.parent.parent
IMAGE = 'maze-ast2027:amd64'
PLATFORM = 'linux/amd64'


def checked(command, **kwargs):
    return subprocess.check_output(command, text=True, **kwargs).strip()


@contextmanager
def lock(root):
    with (root / '.lock').open('w') as f:
        try:
            fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise SystemExit('Another prepare/run/analyze process holds the experiment lock.')
        yield


def docker(root, image, extra=()):
    config = read(root / 'manifest.json').get('campaign', {}) if (root / 'manifest.json').exists() else {}
    cpus = config.get('cpus', 2)
    memory = str(config.get('memory_gb', 4)) + 'g'
    return ['docker', 'run', '--platform', PLATFORM, '--rm', '--init', '--cpus=' + str(cpus), '--memory=' + memory, *(['--memory-swap=' + memory] if config else []), '--network=none',
            '-e', 'PYTHONDONTWRITEBYTECODE=1', '-e', 'JDK_JAVA_OPTIONS=-Xmx2500m',
            '-v', str(root) + ':/results', '-v', str(root / 'env') + ':/results/env:ro',
            '-v', str(root / 'suite') + ':/suite:ro',
            '-w', '/results', *extra, image]


def append(root, message):
    line = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()) + ' ' + message
    with (root / 'progress.log').open('a') as f:
        f.write(line + '\n')
        f.flush()
        os.fsync(f.fileno())
    print(line, flush=True)


def manifest(root):
    spec = read(root / 'manifest.json')
    if identity({k: v for k, v in spec.items() if k != 'id'}) != spec['id']:
        raise SystemExit('Manifest changed: stop and use a new results directory.')
    return spec


def verify_environment(root, spec):
    if fingerprint(root / 'env') != spec['environment'] or fingerprint(root / 'suite') != spec['suite']:
        raise SystemExit('Frozen environment or runner changed: restore it or prepare a new directory.')


def progress(root, spec, verify=True):
    counts = {e: Counter(total=sum(r['experiment'] == e for r in spec['runs']), ok=0, tool_timeout=0, tool_failure=0, empty=0, excluded=0, pending=0) for e in ('A', 'B')}
    reasons = Counter()
    statuses = {}
    for row in spec['runs']:
        rec = valid_record(root, row, spec['id']) if verify else None
        counts[row['experiment']][rec['status'] if rec else 'pending'] += 1
        statuses[row['id']] = rec['status'] if rec else 'pending'
        if rec and rec['status'] == 'excluded':
            reasons[rec['reason']] += 1
    for experiment, count in counts.items():
        repetitions = sorted({r['repetition'] for r in spec['runs'] if r['experiment'] == experiment})
        count['complete_repetitions'] = [rep for rep in repetitions if all(statuses[r['id']] != 'pending' for r in spec['runs'] if r['experiment'] == experiment and r['repetition'] == rep)]
        count['fully_valid_repetitions'] = [rep for rep in repetitions if all(statuses[r['id']] == 'ok' for r in spec['runs'] if r['experiment'] == experiment and r['repetition'] == rep)]
    return dict(experiments={e: dict(v) for e, v in counts.items()}, exclusions=dict(reasons), stop_requested=(root / 'STOP').exists())


def remove_container(name):
    result = subprocess.run(['docker', 'rm', '-f', name], capture_output=True, text=True, timeout=20)
    if result.returncode != 0 and 'No such container' not in result.stderr:
        raise RuntimeError('Container cleanup failed; retain active.json and restore Docker before resuming: ' + result.stderr.strip())


def prepare(args, root):
    if args.campaign and not args.maze_package:
        raise SystemExit('Campaign preparation requires --maze-package with the tested engine archive.')
    if args.campaign and min(args.generation_jobs, args.measurement_jobs, args.cpus, args.memory_gb) < 1:
        raise SystemExit('Resource limits and job counts must be positive.')
    if (root / 'manifest.json').exists() or (root / 'env').exists():
        raise SystemExit('Prepare requires a fresh directory. Existing data are never overwritten.')
    juge = JUGE
    # Fail before builds if the required controls were not applied to this fork.
    for path, needle in [('benchmarktool/src/main/java/sbst/benchmark/TestSuite.java', 'sbst.benchmark.skipMutation'),
                         ('benchmarktool/src/main/java/sbst/benchmark/pitest/PITWrapper.java', 'sbst.benchmark.allMutants')]:
        if needle not in (juge / path).read_text():
            raise SystemExit('Missing required JUGE control: ' + needle)
    build_image = 'maze-ast2027-campaign-build:amd64' if args.campaign else IMAGE
    subprocess.run(['docker', 'build', '--platform', PLATFORM, '-t', build_image, '-f', str(HERE / 'Dockerfile'), str(JUGE)], check=True)
    image = checked(['docker', 'image', 'inspect', '--format', '{{.Id}}', build_image])
    # Containerd can drop an untagged image index after its last container exits.
    # Keep a unique local reference so another preparation cannot orphan it.
    image_tag = 'maze-ast2027-frozen:' + uuid.uuid4().hex
    subprocess.run(['docker', 'image', 'tag', image, image_tag], check=True)
    shutil.copytree(HERE, root / 'suite', ignore=shutil.ignore_patterns('__pycache__'))
    command = ['docker', 'run', '--platform', PLATFORM, '--rm', '--init', '--cpus=2', '--memory=4g',
               '-v', str(juge) + ':/juge', '-v', str(root) + ':/results',
               '-v', 'maze-ast2027-maven:/root/.m2', image, 'sh', '/results/suite/prepare.sh']
    if args.maze_package:
        package = Path(args.maze_package).resolve()
        shutil.copy2(package, root / 'maze-package.tar.gz')
        atomic(root / 'maze-package.json', dict(sha256=digest(package), source=str(package)))
    with (root / 'prepare.log').open('w') as log:
        subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, check=True)
    source_subjects = sorted(p.stem for p in (root / 'env/subjects/src').glob('*.java'))
    if source_subjects != sorted(SUBJECTS):
        raise SystemExit('The source CUT set differs from the frozen 20 subjects.')
    repositories = {}
    for name, directory in [('juge', juge)]:
        repositories[name] = {'commit': checked(['git', 'rev-parse', 'HEAD'], cwd=directory),
                              'status': checked(['git', 'status', '--short'], cwd=directory)}
        # Save relevant source differences as provenance, never environment files.
        diff = checked(['git', 'diff', 'HEAD', '--', 'src', 'benchmarktool', 'maze_runtool'], cwd=directory)
        (root / (name + '-source.patch')).write_text(diff + '\n')
    external = {}
    if args.tools:
        definitions = read(Path(args.tools))
        for name, definition in definitions.items():
            if name not in ('T3', 'EvoSuite', 'Kex') or not all(definition.get(k) for k in ('directory', 'version', 'seed_env', 'configuration')):
                raise SystemExit('tools.json requires named tools with directory, version, seed_env, configuration.')
            folder = Path(definition['directory']).resolve()
            if not os.access(folder / 'runtool', os.X_OK):
                raise SystemExit('Tool has no executable runtool: ' + name)
            if args.campaign:
                for adapter in ('runtool', 'generation.py'):
                    source = JUGE / 'tools/seeded' / (name.lower() + '/runtool' if adapter == 'runtool' else adapter)
                    if not (folder / adapter).exists() or (folder / adapter).read_bytes() != source.read_bytes():
                        raise SystemExit('Reprovision adapters from this revision: ' + name + '/' + adapter)
            shutil.copytree(folder, root / 'env/tools' / name)
            external[name] = {k: v for k, v in definition.items() if k != 'directory'}
    atomic(root / 'env/tools.json', external)
    spec = dict(schema=2, outcome_policy=OUTCOME_POLICY, image=image, image_tag=image_tag, execution_platform=PLATFORM, created_at=time.time(), host={'name': platform.node(), 'architecture': platform.machine(), 'platform': platform.platform()},
                repositories=repositories, environment=fingerprint(root / 'env'), suite=fingerprint(root / 'suite'),
                b_repetitions=args.b_repetitions, purpose=args.purpose, runs=matrix(args.b_repetitions),
                resources=dict(cpus=2, container_memory='4g', maze_jvm_heap='2500m', juge_jvm_heap='1500m', a_watchdog_seconds=300, b_watchdog_seconds=1800),
                selection_rule='maximum unweighted mean of per-subject mean branch coverage at 60s; failure-inclusive outcomes; all 20 subjects and 10 repetitions required; ties use DFS,BFS,SGS,RPS,COS,FOS,FOS+COS order',
                statistics_policy='alpha=.05; MWU two-sided asymptotic tie-corrected with continuity correction; quartiles linear; sample SD; Friedman on complete subject blocks of treatment means; Nemenyi studentized-range infinite df / sqrt(2); ties average ranks and all co-winners counted')
    if args.campaign:
        spec['campaign'] = dict(generation_jobs=args.generation_jobs, measurement_jobs=args.measurement_jobs,
                                cpus=args.cpus, memory_gb=args.memory_gb, order_seed=2027,
                                generation_retry='only proven container startup failure; at most one retry',
                                measurement_retry='at most one retry of the same saved suite',
                                partial_output='retained; failed generation scores zero',
                                mutation='isolated JVM; 180s per child, 3600s total; timeout-only mutants ignored')
        spec['outcome_policy'] = dict(OUTCOME_POLICY, version=2, tool_failure='confirmed generator failure: zero delivered effectiveness')
        spec['resources'].update(cpus=args.cpus, container_memory=str(args.memory_gb)+'g', b_watchdog_seconds=4200)
        random.Random(2027).shuffle(spec['runs'])
    spec['id'] = identity(spec)
    atomic(root / 'manifest.json', spec)
    append(root, f'prepared {len(spec["runs"])} rows; image={image}; missing B tools={sorted(set(["T3", "EvoSuite", "Kex"]) - external.keys())}')


def execute(root, spec, row, timeout, control_root=None):
    control_root = control_root or root
    attempt = 'artifacts/' + row['id'] + '/' + uuid.uuid4().hex
    directory = root / attempt
    directory.parent.mkdir(parents=True, exist_ok=True)
    name = 'ast2027-' + uuid.uuid4().hex[:16]
    active = dict(id=row['id'], container=name, attempt=attempt, started_at=time.time())
    atomic(root / 'active.json', active)
    stop_requested = False

    def stop(signum, frame):
        nonlocal stop_requested
        stop_requested = True

    old = {s: signal.signal(s, stop) for s in (signal.SIGINT, signal.SIGTERM)}
    command = docker(root, spec['image'], ['--name', name]) + ['python3', '/suite/worker.py', row['id'], attempt]
    start = time.monotonic()
    code, reason = None, None
    cleanup_ok = False
    try:
        with (root / 'worker.log').open('a') as log:
            process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT)
            while process.poll() is None:
                if stop_requested or (root / 'STOP').exists() or (control_root / 'STOP').exists():
                    reason = 'interrupted'
                    break
                if time.monotonic() - start >= timeout:
                    reason = 'outer_watchdog_timeout'
                    break
                time.sleep(1)
            if reason:
                remove_container(name)
                try:
                    process.wait(timeout=20)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
            code = process.returncode
        # Handles CLI/daemon disconnects too: never leave an untracked worker alive.
        remove_container(name)
        cleanup_ok = True
        if reason == 'interrupted':
            atomic(root / 'incomplete' / (row['id'] + '.json'), dict(**active, reason=reason))
            return None
        if reason or code != 0 or not (directory / 'result.json').exists():
            directory.mkdir(parents=True, exist_ok=True)
            atomic(directory / 'failure.json', dict(reason=reason or 'worker_failed', exit=code))
            rec = dict(run=row, manifest_id=spec['id'], status='excluded', reason=reason or 'worker_failed',
                       host=spec['host'], versions=read(root / 'env/versions.json'), started_at=active['started_at'],
                       wall_seconds=time.monotonic() - start,
                       evidence={str((directory / k).relative_to(root)): v for k, v in fingerprint(directory).items()})
        else:
            rec = read(directory / 'result.json')
        rec['host'] = {'name': platform.node(), 'architecture': platform.machine(), 'platform': platform.platform()}
        rec['record_sha256'] = identity(rec)
        atomic(root / 'runs' / (row['id'] + '.json'), rec)
        if not valid_record(root, row, spec['id']):
            raise SystemExit('New run failed integrity validation: ' + row['id'])
        return rec
    finally:
        for s, handler in old.items():
            signal.signal(s, handler)
        if cleanup_ok:
            (root / 'active.json').unlink(missing_ok=True)


def run(args, root, spec):
    control_root = root
    verify_environment(root, spec)
    if args.command == 'run' and spec['purpose'] != 'production':
        raise SystemExit('Use smoke for a smoke manifest; prepare a separate production directory.')
    preflight_file = 'preflight.json' if args.experiment == 'A' else 'preflight-B.json'
    if args.command == 'run' and not (root / preflight_file).exists():
        raise SystemExit('Run smoke on this frozen environment first.')
    if args.command == 'run' and read(root / preflight_file)['environment_id'] != identity(spec['environment']):
        raise SystemExit('Preflight does not match frozen environment.')
    rows = [r for r in spec['runs'] if r['experiment'] == args.experiment]
    if args.command == 'smoke':
        # Preflight records never enter the production matrix or change its order.
        parent = root
        root = parent / ('preflight-data' if args.experiment == 'A' else 'preflight-B-data')
        root.mkdir(exist_ok=True)
        for folder in ('env', 'suite'):
            if not (root / folder).exists():
                shutil.copytree(parent / folder, root / folder)
        if not (root / 'manifest.json').exists():
            atomic(root / 'manifest.json', spec)
        verify_environment(root, spec)
        # An explicit smoke command resumes a stopped preflight.
        (control_root / 'STOP').unlink(missing_ok=True)
        (root / 'STOP').unlink(missing_ok=True)
        # Cover all treatments and verify varied random seeds.
        if args.experiment == 'A':
            rows = [r for r in rows if r['budget'] == 10 and (
                (r['subject'] == 'BinarySearch' and r['repetition'] in (1, 2)) or
                (r['treatment'] == 'BFS' and r['repetition'] == 1))]
            rows += [r for r in spec['runs'] if r['experiment'] == 'B' and r['tool'] == 'MAZE' and r['subject'] == 'BinarySearch' and r['repetition'] == 1]
        else:
            rows = [r for r in rows if r['subject'] in (('BinarySearch', 'TriangleClassifier', 'BitwiseManipulator', 'StringPatternMatcher', 'FloatStatistics', 'StringUtils', 'BinaryTree') if spec.get('campaign') else ('BinarySearch', 'TriangleClassifier')) and r['repetition'] in (1, 2)]
        atomic(root / 'selection.json', dict(manifest_id=spec['id'], treatment='BFS', purpose='PIT preflight only'))
    if args.experiment == 'B':
        chosen = read(root / 'selection.json') if (root / 'selection.json').exists() else {}
        if chosen.get('manifest_id') != spec['id']:
            raise SystemExit('Analyze complete A first to write a valid selection.json.')
        if args.command == 'run' and chosen != selection(root, spec):
            raise SystemExit('A evidence or selection changed: analyze verified complete A before B.')
        missing = set(['T3', 'EvoSuite', 'Kex']) - read(root / 'env/tools.json').keys()
        if missing:
            raise SystemExit('Experiment B blocked: missing pinned, seeded adapters for ' + ', '.join(sorted(missing)))
    if (root / 'active.json').exists():
        active = read(root / 'active.json')
        remove_container(active['container'])
        atomic(root / 'incomplete' / (active['id'] + '.json'), dict(**active, reason='unclean_previous_exit'))
        (root / 'active.json').unlink()
    stop_at = time.monotonic() + args.hours * 3600 if args.hours is not None else float('inf')
    completed = failures = 0
    for row in rows:
        if (root / 'STOP').exists() or (control_root / 'STOP').exists() or time.monotonic() >= stop_at or completed >= args.max_runs:
            break
        existing = valid_record(root, row, spec['id'])
        if existing and not (args.retry_excluded and existing['status'] == 'excluded'):
            continue
        if shutil.disk_usage(root).free < args.min_free_gb * 1024**3:
            append(root, 'STOP low disk space')
            break
        append(root, 'start ' + row['id'])
        rec = execute(root, spec, row, 300 if row['experiment'] == 'A' else (4200 if spec.get('campaign') else 1800), control_root)
        if rec is None:
            append(root, 'interrupted ' + row['id'] + '; retry on resume')
            break
        completed += 1
        failures = failures + 1 if rec['status'] == 'excluded' else 0
        append(root, row['id'] + ' ' + rec['status'] + ' ' + str(rec.get('reason')))
        # Counts remain inexpensive between runs; status/analyze perform the full integrity scan.
        for e in ('A', 'B'):
            total = sum(r['experiment'] == e for r in spec['runs'])
            terminal = sum((root / 'runs' / (r['id'] + '.json')).exists() for r in spec['runs'] if r['experiment'] == e)
            append(root, f'{e}: terminal_files={terminal}/{total} remaining={total-terminal} (status verifies evidence)')
        if failures >= 3:
            append(root, 'STOP three consecutive unresolved failures; inspect before resuming')
            return 3
    if args.command == 'smoke':
        records = [valid_record(root, r, spec['id']) for r in rows]
        if not all(rec and (rec['status'] == 'ok' or ((row['experiment'] == 'A' or spec.get('campaign'))
                and row['subject'] not in ('BinarySearch', 'TriangleClassifier')
                and rec['status'] in ('tool_timeout', 'tool_failure', 'empty'))) for row, rec in zip(rows, records)):
            return 3
        # Seed receipts and generated suites demonstrate plumbing; equal coverage is permitted.
        atomic(parent / preflight_file, dict(environment_id=identity(spec['environment']), run_ids=[r['id'] for r in rows],
                                            seeds=[r['seed'] for r in rows], manifest_id=spec['id'], passed_at=time.time()))
        append(root, f'preflight passed: {len(rows)} real runs for experiment {args.experiment}')
    atomic(root / 'progress.json', progress(root, spec))
    return 0


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('command', choices=['prepare', 'smoke', 'run', 'status', 'stop', 'resume', 'analyze'])
    p.add_argument('--results', required=True, type=Path)
    p.add_argument('--tools', help='JSON of pinned external JUGE adapter directories; see runbook')
    p.add_argument('--b-repetitions', type=int, choices=[5, 10], default=10)
    p.add_argument('--purpose', choices=['smoke', 'production'], default='production')
    p.add_argument('--experiment', choices=['A', 'B'], default='A')
    p.add_argument('--hours', type=float, help='Optional session limit in hours; no time limit by default')
    p.add_argument('--max-runs', type=int, default=100000)
    p.add_argument('--min-free-gb', type=float, default=5)
    p.add_argument('--retry-excluded', action='store_true')
    p.add_argument('--campaign', action='store_true', help='Freeze a stage-separated parallel campaign')
    p.add_argument('--maze-package', type=Path, help='Local Linux AMD64 MAZE distribution; copied and hashed')
    p.add_argument('--generation-jobs', type=int, default=1)
    p.add_argument('--measurement-jobs', type=int, default=1)
    p.add_argument('--cpus', type=int, default=2)
    p.add_argument('--memory-gb', type=int, default=4)
    args = p.parse_args()
    root = args.results.resolve()
    root.mkdir(parents=True, exist_ok=True)
    if args.command == 'stop':
        (root / 'STOP').touch()
        print('Stop requested; current run will be abandoned and retried on resume.')
        return 0
    if args.command == 'status':
        spec = manifest(root)
        summary = progress(root, spec)
        summary['active'] = read(root / 'active.json') if (root / 'active.json').exists() else None
        import json
        print(json.dumps(summary, indent=2))
        return 0
    with lock(root):
        if args.command == 'prepare':
            prepare(args, root)
            return 0
        spec = manifest(root)
        if spec.get('campaign') and args.command in ('run', 'resume'):
            raise SystemExit('Use the frozen campaign.py run/resume for this manifest.')
        if args.command == 'resume':
            (root / 'STOP').unlink(missing_ok=True)
            args.command = 'run'
        if args.command == 'analyze':
            verify_environment(root, spec)
            subprocess.run(docker(root, spec['image']) + ['python3', '/suite/analyze.py'], check=True)
            return 0
        return run(args, root, spec)


if __name__ == '__main__':
    sys.exit(main())
