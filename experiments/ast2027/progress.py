"""Read small checkpoints for deterministic, informational progress reports."""
from collections import Counter
from datetime import datetime, timezone
import json
import shutil
import time

from common import read

ZERO_OUTCOMES = {'empty', 'tool_timeout', 'tool_failure'}
RESOLVED = ZERO_OUTCOMES | {'generated', 'ok', 'not_required'}


def snapshot(root, rows):
    ids = {r['id'] for r in rows}
    records = {}
    for phase in ('generation', 'coverage', 'mutation'):
        records[phase] = {p.stem: read(p) for p in (root / 'stages' / phase).glob('*.json') if p.stem in ids}
    groups = {}
    for experiment in sorted({r['experiment'] for r in rows}):
        subjects = [r for r in rows if r['experiment'] == experiment]
        for phase in ('generation', 'coverage', 'mutation'):
            if phase == 'mutation' and experiment == 'A':
                continue
            counts = Counter()
            for row in subjects:
                rec = records[phase].get(row['id'])
                generation = records['generation'].get(row['id'], {})
                if rec:
                    outcome = rec['status']
                elif phase != 'generation' and generation.get('status') in ZERO_OUTCOMES:
                    outcome = 'not_required'
                elif phase != 'generation' and generation.get('status') == 'excluded':
                    outcome = 'blocked_by_generation'
                else:
                    outcome = 'pending'
                counts[outcome] += 1
            groups[experiment + ' ' + phase] = dict(total=len(subjects),
                resolved=sum(counts[s] for s in RESOLVED), outcomes=dict(sorted(counts.items())))
    active = []
    for path in sorted((root / 'active').glob('*.json')):
        try:
            rec = read(path)
        except FileNotFoundError:
            # A worker may finish between directory listing and reading its entry.
            continue
        if rec['id'] in ids:
            active.append(rec)
    reasons = Counter(r.get('reason') or 'unspecified' for phase in records.values()
                      for r in phase.values() if r['status'] == 'excluded')
    completions = [r['finished_at'] for phase in records.values() for r in phase.values() if 'finished_at' in r]
    return dict(phases=groups, active=active, unresolved_reasons=dict(sorted(reasons.items())),
                last_completion_at=max(completions, default=None),
                stop_requested=(root / 'STOP').exists() or (root.name == 'rehearsal-data' and (root.parent / 'STOP').exists()),
                free_disk_gib=round(shutil.disk_usage(root).free / 1024**3, 1))


def duration(seconds):
    seconds = max(0, int(seconds))
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f'{hours:02d}:{minutes:02d}:{seconds:02d}'


class ProgressReporter:
    """Called by the coordinator; never starts, stops, or changes worker jobs."""
    def __init__(self, root, spec, command, interval=900):
        if interval <= 0:
            raise ValueError('Progress interval must be positive')
        self.root = root
        self.rows = [] if command == 'rehearse' else spec['runs']
        self.command = command
        self.interval = interval
        self.log = root / 'progress-reports.jsonl'
        self.began = time.monotonic()
        self.next_report = self.began
        self.phase = 'setup'
        self.stop = None

    def __enter__(self):
        self.report('started', force=True)
        return self

    def __exit__(self, exc_type, exc, traceback):
        stopped = (self.stop is not None and self.stop.is_set()) or (self.root / 'STOP').exists()
        if self.root.name == 'rehearsal-data':
            stopped = stopped or (self.root.parent / 'STOP').exists()
        event = 'failed' if exc_type else ('stopped' if stopped else 'finished')
        self.report(event, force=True, error=str(exc) if exc else None)
        return False

    def start_stage(self, phase, rows):
        self.phase = '+'.join(sorted({r['experiment'] for r in rows})) + ' ' + phase
        self.report('phase_started', force=True)

    def report(self, event='progress', force=False, error=None):
        now = time.monotonic()
        if not force and now < self.next_report:
            return
        self.next_report = now + self.interval
        wall = time.time()
        record = dict(timestamp=datetime.fromtimestamp(wall, timezone.utc).isoformat(),
                      command=self.command, event=event, phase=self.phase,
                      elapsed_seconds=round(now - self.began, 1))
        if error:
            record['error'] = error
        try:
            record.update(snapshot(self.root, self.rows))
        except (OSError, ValueError, KeyError, TypeError) as failure:
            # Reporting must not terminate generation or hide its original error.
            record['report_error'] = str(failure)
        lines = [f"[{record['timestamp']}] {self.command}: {event}; phase={self.phase}; session elapsed={duration(now - self.began)}"]
        for name, group in record.get('phases', {}).items():
            counts = ', '.join(f'{k}={v}' for k, v in group['outcomes'].items())
            lines.append(f"  {name}: {group['resolved']}/{group['total']} resolved ({counts})")
        for active in record.get('active', []):
            lines.append(f"  active: {active['id']} {active['phase']}; elapsed={duration(wall - active['started_at'])}")
        if 'free_disk_gib' in record:
            lines.append(f"  disk free={record['free_disk_gib']} GiB; stop requested={record['stop_requested']}")
        for key in ('unresolved_reasons', 'error', 'report_error'):
            if record.get(key):
                lines.append(f'  {key}: {record[key]}')
        try:
            with self.log.open('a') as stream:
                stream.write(json.dumps(record, sort_keys=True) + '\n')
        except OSError as failure:
            lines.append(f'  report log unavailable: {failure}')
        try:
            print('\n'.join(lines), flush=True)
        except (OSError, ValueError):
            # A reporting write failure must not mask the experiment's outcome.
            pass
