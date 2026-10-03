#!/usr/bin/env python3
"""Stage-separated, bounded parallel campaigns over immutable generated suites."""
import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import threading
import time
import uuid

from common import atomic, digest, fingerprint, identity, read, required_certificates, selection, valid_record
from bench import lock, manifest, prepare_validation, verify_environment
from progress import ProgressReporter
from host import check_capacity, container_user

GENERATION_OUTCOMES = {'generated', 'empty', 'tool_timeout', 'tool_failure'}
ZERO_OUTCOMES = GENERATION_OUTCOMES - {'generated'}


def stopped(root):
    return (root / 'STOP').exists() or (root.name == 'rehearsal-data' and (root.parent / 'STOP').exists())


def stage_path(root, row, phase):
    return root / 'stages' / phase / (row['id'] + '.json')


def verified(root, path, manifest_id=None):
    if not path.exists():
        return None
    record = read(path)
    if record['run']['id'] != path.stem or (manifest_id is not None and record['manifest_id'] != manifest_id):
        raise ValueError('Checkpoint belongs to a different case or campaign: ' + str(path))
    if path.parent.parent.name == 'stages' and record['phase'] != path.parent.name:
        raise ValueError('Checkpoint phase mismatch: ' + str(path))
    if record.get('record_sha256') != identity({k: v for k, v in record.items() if k != 'record_sha256'}):
        raise ValueError('Corrupt checkpoint: ' + str(path))
    if not record.get('evidence') or any(digest(root / p) != h for p, h in record['evidence'].items()):
        raise ValueError('Changed attempt evidence: ' + str(path))
    return record


def publish(path, record):
    record = {k: v for k, v in record.items() if k != 'record_sha256'}
    atomic(path, dict(record, record_sha256=identity(record)))


def docker_json(*args):
    value = subprocess.check_output(['docker', *args], text=True, stderr=subprocess.PIPE, timeout=30)
    import json
    return json.loads(value)


def capacity(spec):
    info = docker_json('info', '--format', '{{json .}}')
    config = spec['campaign']
    check_capacity(info, config)
    return dict(cpus=info['NCPU'], memory_bytes=info['MemTotal'], server_version=info['ServerVersion'],
                architecture=info['Architecture'], operating_system=info['OperatingSystem'])


def command(root, spec, active):
    c = spec['campaign']
    cmd = ['docker', 'run', '--platform', 'linux/amd64', '--init', *container_user(), '--name', active['container'],
           '--cpus=' + str(c['cpus']), '--memory=' + str(c['memory_gb']) + 'g',
           '--memory-swap=' + str(c['memory_gb']) + 'g', '--network=none',
           '-e', 'PYTHONDONTWRITEBYTECODE=1', '-e', 'JDK_JAVA_OPTIONS=-Xmx2500m',
           '-v', str(root) + ':/results', '-v', str(root / 'env') + ':/results/env:ro',
           '-v', str(root / 'suite') + ':/suite:ro', '-w', '/results', spec['image'],
           'python3', '/suite/worker.py', active['id'], active['attempt'], active['phase']]
    if active['phase'] != 'generation':
        cmd.append('stages/generation/' + active['id'] + '.json')
    return cmd


def finish_attempt(root, spec, row, active, reason=None):
    """Also used on restart: recover a completed worker without rerunning it."""
    work = root / active['attempt']
    inspection = docker_json('inspect', '--format', '{{json .State}}', active['container'])
    if inspection['Running']:
        raise ValueError('Worker still running: ' + active['container'] + '; wait for it to finish, then resume. It has not been stopped or restarted.')
    work.mkdir(parents=True, exist_ok=True)
    launch_log = root / 'active' / (active['id'] + '.log')
    if launch_log.exists():
        shutil.move(str(launch_log), work / 'container.log')
    atomic(work / 'container-state.json', inspection)
    result_file = work / 'result.json'
    if result_file.exists() and reason != 'interrupted':
        rec = read(result_file)
        if rec['run'] != row or rec['manifest_id'] != spec['id'] or rec['phase'] != active['phase']:
            raise ValueError('Worker returned mismatched coordinates')
        if any(digest(root / p) != h for p, h in rec['evidence'].items()):
            raise ValueError('Worker evidence changed')
    else:
        rec = dict(run=row, manifest_id=spec['id'], status='excluded', phase=active['phase'],
                   reason=reason or 'worker_failed', started_at=active['started_at'])
        # Only a container which never started is safely retryable generation.
        if inspection['StartedAt'].startswith('0001-'):
            rec['reason'] = 'container_start_failed'
        invocation = work / 'generation/invocation.json'
        if active['phase'] == 'generation' and inspection.get('OOMKilled') and invocation.exists():
            inv = read(invocation)
            if (inv.get('target') == 'nl.uu.maze.benchmarks.' + row['subject']
                    and inv.get('seed') == row['seed'] and inv.get('tool') == row['tool']):
                rec.update(status='tool_failure', reason='generation_container_oom')
    rec['attempt'] = active['attempt']
    rec['finished_at'] = time.time()
    rec['evidence'] = {str((work / p).relative_to(root)): h for p, h in fingerprint(work).items()}
    publish(stage_path(root, row, active['phase']), rec)
    subprocess.run(['docker', 'rm', active['container']], check=True, capture_output=True, timeout=30)
    (root / 'active' / (active['id'] + '.json')).unlink(missing_ok=True)
    return rec


def execute(root, spec, row, phase, stop):
    attempt = 'attempts/' + row['id'] + '/' + phase + '-' + uuid.uuid4().hex
    work = root / attempt
    # worker creates work itself; host evidence lives beside it until launch.
    work.parent.mkdir(parents=True, exist_ok=True)
    active = dict(id=row['id'], phase=phase, attempt=attempt, container='ast2027-' + uuid.uuid4().hex,
                  started_at=time.time())
    atomic(root / 'active' / (row['id'] + '.json'), active)
    launch_log = root / 'active' / (row['id'] + '.log')
    limit = 2 * row['budget'] + 90 if phase == 'generation' else (4200 if phase == 'mutation' else 600)
    reason = None
    with launch_log.open('w') as log:
        process = subprocess.Popen(command(root, spec, active), stdout=log, stderr=subprocess.STDOUT)
        began = time.monotonic()
        while process.poll() is None:
            if stop.is_set() or stopped(root):
                reason = 'interrupted'
            elif time.monotonic() - began > limit:
                reason = 'outer_watchdog_timeout'
            if reason:
                subprocess.run(['docker', 'kill', active['container']], check=True, capture_output=True, timeout=30)
                process.wait(timeout=30)
                break
            time.sleep(.25)
    return finish_attempt(root, spec, row, active, reason)


def retryable(record, phase):
    if phase == 'generation':
        return record['reason'] == 'container_start_failed'
    # Measurement retries never invoke a generator or change the saved suite.
    return record['status'] == 'excluded' and record['reason'] != 'interrupted'


def reconcile(root, spec):
    by_id = {r['id']: r for r in spec['runs']}
    for file in sorted((root / 'active').glob('*.json')):
        active = read(file)
        finish_attempt(root, spec, by_id[active['id']], active)


def run_stage(root, spec, rows, phase, stop, reporter=None):
    if reporter:
        reporter.start_stage(phase, rows)
    jobs = spec['campaign']['generation_jobs' if phase == 'generation' else 'measurement_jobs']
    pending = []
    for row in rows:
        if reporter:
            reporter.report()
        rec = verified(root, stage_path(root, row, phase), spec['id'])
        if rec is None and list((root / 'attempts' / row['id']).glob(phase + '-*')):
            raise ValueError('Attempt exists without a checkpoint; inspect before retrying: ' + row['id'])
        if rec:
            if rec['status'] in GENERATION_OUTCOMES | {'ok'}:
                continue
            attempts = len(list((root / 'attempts' / row['id']).glob(phase + '-*')))
            if rec['reason'] == 'interrupted':
                # Explicit resume permits retry of user-interrupted work.
                pass
            elif not retryable(rec, phase) or attempts >= 2:
                continue
        if phase != 'generation':
            gen = verified(root, stage_path(root, row, 'generation'), spec['id'])
            if not gen or gen['status'] != 'generated':
                continue
        pending.append(row)
    with ThreadPoolExecutor(max_workers=jobs) as pool:
        running = {}
        while pending or running:
            if reporter:
                reporter.report()
            while pending and len(running) < jobs and not stop.is_set() and not stopped(root):
                if shutil.disk_usage(root).free < 5 * 1024**3:
                    stop.set()
                    raise ValueError('Less than 5 GiB disk headroom; stopped launching workers')
                row = pending.pop(0)
                running[pool.submit(execute, root, spec, row, phase, stop)] = row
            if not running:
                break
            done, _ = wait(running, timeout=1, return_when=FIRST_COMPLETED)
            for future in done:
                row = running.pop(future)
                try:
                    rec = future.result()
                except BaseException:
                    stop.set()
                    raise
                print(phase, row['id'], rec['status'], rec.get('reason'), flush=True)
                if rec['status'] == 'excluded' and retryable(rec, phase):
                    attempts = len(list((root / 'attempts' / row['id']).glob(phase + '-*')))
                    if attempts < 2:
                        pending.append(row)
    return not stop.is_set() and not stopped(root)


def assemble(root, spec, rows, reporter=None):
    complete = True
    for row in rows:
        if reporter:
            reporter.report()
        gen = verified(root, stage_path(root, row, 'generation'), spec['id'])
        if not gen:
            complete = False
            continue
        phases = [gen]
        if gen['status'] == 'generated':
            cov = verified(root, stage_path(root, row, 'coverage'), spec['id'])
            mut = verified(root, stage_path(root, row, 'mutation'), spec['id']) if row['experiment'] == 'B' else None
            phases += [v for v in (cov, mut) if v]
            if cov is None or cov['status'] != 'ok' or (row['experiment'] == 'B' and (mut is None or mut['status'] != 'ok')):
                complete = False
                rec = dict(gen, status='excluded', reason='measurement_incomplete')
                if cov and cov['status'] == 'ok':
                    rec.update({k: cov[k] for k in ('coverage', 'branch_total', 'branch_covered')})
            else:
                rec = dict(gen, status='ok', reason=None)
                rec.update({k: cov[k] for k in ('coverage', 'branch_total', 'branch_covered')})
                if mut:
                    rec.update({k: mut[k] for k in ('mutation_kill', 'mutant_count', 'mutants_killed', 'mutants_generated', 'mutants_ignored')})
        else:
            rec = dict(gen)
            complete &= gen['status'] in ZERO_OUTCOMES
        rec['phase'] = 'consolidated'
        rec.pop('wall_seconds', None)
        rec['stage_wall_seconds'] = {p['phase']: p.get('wall_seconds') for p in phases}
        rec['finished_at'] = max(p.get('finished_at', 0) for p in phases)
        rec['evidence'] = {p: h for phase in phases for p, h in phase['evidence'].items()}
        rec['stage_records'] = {p['phase']: str(stage_path(root, row, p['phase']).relative_to(root)) for p in phases}
        for p in rec['stage_records'].values():
            rec['evidence'][p] = digest(root / p)
        publish(root / 'runs' / (row['id'] + '.json'), rec)
    return complete


def status(root, spec):
    result = {}
    for phase in ('generation', 'coverage', 'mutation'):
        result[phase] = dict(Counter(read(p)['status'] for p in (root / 'stages' / phase).glob('*.json')))
    result['active'] = [read(p) for p in (root / 'active').glob('*.json')]
    result['stop_requested'] = stopped(root)
    if (root / 'rehearsal-data/manifest.json').exists() and not (root / 'rehearsal.json').exists():
        result['rehearsal'] = status(root / 'rehearsal-data', spec)
    return result


def configure_b(root, spec):
    chosen = selection(root, spec)
    if not chosen:
        raise ValueError('B requires complete verified A measurements for this archived policy')
    if 'b_treatment_policy' in spec and (root / 'selection.json').exists() and read(root / 'selection.json') != chosen:
        raise ValueError('B treatment record conflicts with the frozen fixed policy')
    atomic(root / 'selection.json', chosen)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('command', choices=['run', 'resume', 'generate', 'measure', 'rehearse', 'status', 'stop'])
    p.add_argument('--results', required=True, type=Path)
    p.add_argument('--experiment', choices=['A', 'B'], default='A')
    p.add_argument('--progress-interval', type=int, default=900, metavar='SECONDS',
                   help='Periodic terminal and JSONL progress reports (default: 900 seconds)')
    args = p.parse_args()
    if args.progress_interval <= 0:
        p.error('--progress-interval must be positive')
    root = args.results.resolve()
    spec = manifest(root)
    if args.command in ('run', 'resume', 'generate', 'measure') and spec.get('purpose') != 'production':
        raise SystemExit('Production commands require a production-purpose manifest.')
    if not spec.get('campaign'):
        raise SystemExit('Prepare a fresh directory with --campaign; legacy results are not migrated.')
    if args.command == 'stop':
        (root / 'STOP').touch()
        return
    if args.command == 'status':
        import json
        print(json.dumps(status(root, spec), indent=2))
        return
    with lock(root), ProgressReporter(root, spec, args.command, args.progress_interval) as reporter:
        verify_environment(root, spec)
        for name in (() if args.command == 'rehearse' else required_certificates(spec)):
            cert = read(root / name)
            if cert['environment_id'] != identity(spec['environment']) or cert.get('manifest_id') != spec['id']:
                raise ValueError('Preflight does not match environment')
            directory = {'preflight.json': 'preflight-data', 'preflight-B.json': 'preflight-B-data',
                         'rehearsal.json': 'rehearsal-data'}[name]
            by_id = {r['id']: r for r in spec['runs']}
            for run_id in cert.get('run_ids', cert.get('runs', [])):
                if not valid_record(root / directory, by_id[run_id], spec['id']):
                    raise ValueError('Preflight evidence changed: ' + run_id)
        host = capacity(spec)
        if not (root / 'host-resources.json').exists():
            atomic(root / 'host-resources.json', host)
        elif read(root / 'host-resources.json') != host:
            raise ValueError('Docker resources/runtime changed; use a fresh campaign or restore the frozen host configuration.')
        if args.command in ('resume', 'rehearse'):
            (root / 'STOP').unlink(missing_ok=True)
        stop = threading.Event()
        reporter.stop = stop
        def halt(signum, frame):
            stop.set()
        for sig in (signal.SIGINT, signal.SIGTERM):
            signal.signal(sig, halt)
        if args.command == 'rehearse':
            parent = root
            root = parent / 'rehearsal-data'
            prepare_validation(parent, root, spec)
            (root / 'STOP').unlink(missing_ok=True)
            atomic(root / 'selection.json', selection(root, spec) if 'b_treatment_policy' in spec
                   else dict(manifest_id=spec['id'], treatment='BFS', purpose='rehearsal'))
            reconcile(root, spec)
            rows = [r for r in spec['runs'] if r['repetition'] == 1 and (
                (r['experiment'] == 'A' and r['subject'] == 'HeapSort' and r['treatment'] == 'DFS' and r['budget'] == 10)
                or (r['experiment'] == 'B' and (r['subject'] == 'BinarySearch'
                    or (r['tool'] == 'T3' and r['subject'] == 'StringPatternMatcher'))))]
            reporter.root, reporter.rows = root, rows
            for phase in ('generation', 'coverage', 'mutation'):
                eligible = [r for r in rows if phase != 'mutation' or r['experiment'] == 'B']
                if not run_stage(root, spec, eligible, phase, stop, reporter):
                    return
            if not assemble(root, spec, rows, reporter):
                raise ValueError('Rehearsal has unresolved results')
            for row in rows:
                rec = verified(root, root / 'runs' / (row['id'] + '.json'))
                if row['subject'] == 'BinarySearch' and rec['status'] != 'ok':
                    raise ValueError('Reference subject must produce measured results: ' + row['id'])
            atomic(parent / 'rehearsal.json', dict(manifest_id=spec['id'], environment_id=identity(spec['environment']),
                                                 runs=[r['id'] for r in rows], finished_at=time.time()))
            print('Concurrency rehearsal complete; observations are separate from production.')
            return
        reconcile(root, spec)
        experiments = ('A', 'B') if args.command in ('run', 'resume') else (args.experiment,)
        generation_first = args.command in ('run', 'resume') and 'b_treatment_policy' in spec
        if generation_first:
            for experiment in experiments:
                if experiment == 'B':
                    configure_b(root, spec)
                rows = [r for r in spec['runs'] if r['experiment'] == experiment]
                if not run_stage(root, spec, rows, 'generation', stop, reporter):
                    return
        for experiment in experiments:
            rows = [r for r in spec['runs'] if r['experiment'] == experiment]
            if experiment == 'B':
                configure_b(root, spec)
            if args.command != 'measure' and not generation_first:
                if not run_stage(root, spec, rows, 'generation', stop, reporter):
                    return
            if args.command != 'generate':
                if not run_stage(root, spec, rows, 'coverage', stop, reporter):
                    return
                if experiment == 'B' and not run_stage(root, spec, rows, 'mutation', stop, reporter):
                    return
                if not assemble(root, spec, rows, reporter):
                    raise ValueError('Unresolved cases remain; inspect stages. Tool failures are scored, infrastructure/measurement failures are not.')
        if args.command in ('run', 'resume'):
            atomic(root / 'campaign-complete.json', dict(manifest_id=spec['id'], finished_at=time.time()))
            print('Campaign complete. Run bench.py analyze separately to export statistics.')


if __name__ == '__main__':
    main()
