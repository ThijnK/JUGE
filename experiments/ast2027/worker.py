"""Execute exactly one manifest row inside an isolated, disposable container."""
import csv
import importlib.util
import os
import re
from pathlib import Path
import shutil
import subprocess
import sys
import time
import uuid

from common import OPTIONS, atomic, b_treatment, digest, fingerprint, read


def instantiate(template, destination):
    """Share frozen dependencies; keep only writable run outputs per attempt."""
    destination.mkdir()
    for source in template.iterdir():
        if source.is_dir():
            # Tool templates contain immutable lib/classes directories only.
            (destination / source.name).symlink_to(os.path.relpath(source, destination), target_is_directory=True)
        else:
            shutil.copy2(source, destination / source.name)


class ToolTimeout(ValueError):
    pass


class EmptyOutput(ValueError):
    pass


def mutation_properties(spec, metrics):
    policy = spec.get('measurement_policy', {})
    props = dict(isolateMutants='true', mutationTimeoutMs=str(policy.get('total_seconds', 3600) * 1000),
                 mutationEvidence=str(metrics / 'mutation-isolation'))
    if policy.get('version', 2) < 3:
        return dict(props, mutantProcessTimeoutMs='180000')
    child = policy['child_budget']
    if child['policy'] != 'suite-v1' or child['default_test_timeout_seconds'] != 5:
        raise ValueError('Unsupported frozen mutation budget policy')
    return dict(props, mutantProcessTimeoutPolicy=child['policy'],
                mutantProcessTimeoutMinMs=str(child['minimum_seconds'] * 1000),
                mutantStartupAllowanceMs=str(child['startup_seconds'] * 1000),
                mutantClassAllowanceMs=str(child['fixture_seconds_per_class'] * 1000))


def resource_counters(root=Path('/sys/fs/cgroup')):
    """Read available cgroup v1/v2 evidence before Docker removes the container."""
    paths = {'memory-events.txt': 'memory.events', 'memory.peak': 'memory.peak', 'cpu.stat': 'cpu.stat'}
    if not (root / 'memory.events').exists():
        paths = {'memory-oom-control.txt': 'memory/memory.oom_control',
                 'memory.peak': 'memory/memory.max_usage_in_bytes',
                 'memory.failcnt': 'memory/memory.failcnt',
                 'cpu.stat': 'cpu/cpu.stat', 'cpuacct.usage': 'cpuacct/cpuacct.usage'}
    return {name: (root / path).read_text() for name, path in paths.items() if (root / path).exists()}


def confirmed_timeout(generation, row, definition, jar_sha):
    """Return a deadline reason only with matching evidence that the tool ran."""
    target = 'nl.uu.maze.benchmarks.' + row['subject']
    try:
        if row['tool'] == 'MAZE':
            statuses = list(generation.glob('temp/maze-run-*/tests/*-run-status.json'))
            if len(statuses) != 1:
                return False
            receipt = read(statuses[0])
            return (receipt['outcome'] in ('running', 'completed')
                    and receipt['target'] == target and receipt['seed'] == row['seed']
                    and receipt['mode'] == 'symbolic'
                    and receipt['search']['maze']['sha256'] == jar_sha)
        expected = dict(tool=row['tool'], version=definition['version'], seed=row['seed'],
                        target=target, budget=row['budget'])
        return read(generation / 'invocation.json') == expected
    except (OSError, ValueError, KeyError, TypeError):
        return False


def run_one(root, row, attempt, phase="all", generation_record=None):
    envroot = root / 'env'
    work = root / attempt
    work.mkdir(parents=True, exist_ok=False)
    spec = read(root / 'manifest.json')
    result = dict(run=row, manifest_id=spec['id'], status='excluded', reason=None,
                  host=spec['host'], versions=read(envroot / 'versions.json'), started_at=time.time())
    target = 'nl.uu.maze.benchmarks.' + row['subject']
    treatment = row['treatment']
    if row['experiment'] == 'B' and row['tool'] == 'MAZE':
        treatment = b_treatment(root, spec)
    result['maze_treatment'] = treatment if row['tool'] == 'MAZE' else None
    result['treatment_kind'] = 'combinator' if treatment == 'FOS+COS' else ('base' if row['tool'] == 'MAZE' else 'tool')
    tool = 'maze-ast2027' if row['tool'] == 'MAZE' else row['tool'].lower()
    runenv = dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
    config = work / 'benchmarks.list'
    classes = envroot / 'subjects/classes'
    config.write_text('{ SUBJECT={ src="%s"; bin="%s"; classpath=("%s"); classes=(%s); }; }\n' % (envroot / 'subjects/src', classes, classes, target))
    generation = work / 'generation'
    metrics = work / 'metrics'
    definition = None
    template = envroot / 'tool'
    if row['tool'] != 'MAZE':
        definition = read(envroot / 'tools.json')[row['tool']]
        template = envroot / 'tools' / row['tool']
        runenv[definition['seed_env']] = str(row['seed'])
        result['external_tool'] = definition
    if generation_record is None:
        instantiate(template, generation)
    else:
        generation = root / generation_record['generation_directory']
    instantiate(template, metrics)
    batch_id = str(uuid.uuid4())
    if row['tool'] == 'MAZE':
        experiment = dict(name='ast2027', mode='symbolic', arguments=['--strategy=' + treatment.replace('+', ','), '--seed=' + str(row['seed']), *OPTIONS])
        atomic(work / 'experiment.json', experiment)
        runenv.update(MAZE_HOME=str(envroot / 'maze'), MAZE_EXPERIMENT=str(work / 'experiment.json'), JUGE_MAZE_BATCH_ID=batch_id)
        if generation_record is None:
            (generation / 'maze-batch-id.txt').write_text(batch_id)
    libs = envroot / 'lib'
    props = {'config': config, 'java': '/opt/java8/bin/java', 'javac': '/opt/java8/bin/javac',
             'junit': libs / 'junit-4.12.jar', 'junit.dependency': libs / 'hamcrest-core-1.3.jar',
             'jacoco': libs / 'jacocoagent.jar',
             'pitest': str(libs / 'pitest-1.1.11.jar') + ':' + str(libs / 'pitest-command-line-1.1.11.jar'),
             'skipMutation': str(row['experiment'] == 'A' or phase == 'coverage').lower(), 'allMutants': 'true'}
    if spec.get('campaign'):
        props.update(mutation_properties(spec, metrics))
    command = ['/opt/java8/bin/java', '-Xmx1500m', '-ea'] + ['-Dsbst.benchmark.' + k + '=' + str(v) for k, v in props.items()] + ['-jar', str(libs / 'runner.jar')]
    commands = []

    def invoke(directory, arguments):
        cmd = command + [tool, 'SUBJECT', str(directory), str(row['repetition']), str(row['budget'])] + arguments
        commands.append(cmd)
        atomic(work / 'commands.json', commands)
        with (directory / 'process.log').open('w') as log:
            return subprocess.run(cmd, cwd=directory, env=runenv, stdout=log, stderr=subprocess.STDOUT).returncode

    def logs(directory):
        return '\n'.join(p.read_text(errors='replace') for p in directory.glob('*.txt')) + (directory / 'process.log').read_text(errors='replace')

    def finish():
        result['finished_at'] = time.time()
        result['wall_seconds'] = result['finished_at'] - result['started_at']
        result['phase'] = phase
        counters = resource_counters()
        if 'memory-events.txt' in counters:
            result['memory_events'] = counters['memory-events.txt']
        if 'memory-oom-control.txt' in counters:
            result['memory_oom_control'] = counters['memory-oom-control.txt']
        for name, value in counters.items():
            (work / name).write_text(value)
        result['evidence'] = {str((work / name).relative_to(root)): sha for name, sha in fingerprint(work).items()}
        atomic(work / 'result.json', result)
        return result

    try:
        if generation_record is None:
            code = invoke(generation, ['--only-generate-tests'])
            result['generation_exit'] = code
            (generation / 'maze-process-exit.txt').write_text(str(code))
            text = logs(generation)
            ready_timeout = 'A timeout occurred waiting for signal READY' in text
            adapter_timeout = False
            if row['tool'] != 'MAZE' and (generation / 'timeout.json').exists():
                expected = dict(tool=row['tool'], version=definition['version'], seed=row['seed'],
                                target=target, budget=row['budget'], reason='adapter_generation_timeout')
                adapter_timeout = read(generation / 'timeout.json') == expected
            if ready_timeout or adapter_timeout:
                reason = 'juge_generation_timeout' if ready_timeout else 'adapter_generation_timeout'
                if confirmed_timeout(generation, row, definition, digest(envroot / 'maze/maze.jar')):
                    raise ToolTimeout(reason)
                raise ValueError(reason + '_without_invocation_evidence')
            if row['tool'] == 'T3' and (generation / 't3-outcome.json').exists():
                receipt = read(generation / 't3-outcome.json')
                if (receipt.get('outcome') == 'upstream_watchdog' and not receipt.get('generated_tests')
                        and confirmed_timeout(generation, row, definition, '')):
                    raise ToolTimeout('t3_upstream_watchdog_without_saved_tests')
            if row['tool'] == 'MAZE':
                maze_logs = '\n'.join(p.read_text(errors='replace') for p in generation.glob('temp/maze-run-*/maze.log'))
                if 'OutOfMemoryError' in maze_logs:
                    if spec.get('campaign') and confirmed_timeout(generation, row, definition, digest(envroot / 'maze/maze.jar')):
                        result['status'] = 'tool_failure'
                    raise ValueError('maze_out_of_memory')
            if code:
                if spec.get('campaign') and row['tool'] == 'MAZE':
                    statuses = list(generation.glob('temp/maze-run-*/tests/*-run-status.json'))
                    if len(statuses) == 1:
                        receipt = read(statuses[0])
                        if (receipt.get('outcome') == 'failed' and receipt.get('target') == target
                                and receipt.get('seed') == row['seed']
                                and receipt.get('search', {}).get('maze', {}).get('sha256') == digest(envroot / 'maze/maze.jar')):
                            result['status'] = 'tool_failure'
                if spec.get('campaign') and row['tool'] != 'MAZE':
                    failure = generation / 'tool-failure.json'
                    if failure.exists() and confirmed_timeout(generation, row, definition, ''):
                        expected = dict(tool=row['tool'], version=definition['version'], seed=row['seed'],
                                        target=target, budget=row['budget'], reason='reported_generator_failure')
                        if read(failure) == expected:
                            result['status'] = 'tool_failure'
                    termination = generation / 'termination.json'
                    if termination.exists() and confirmed_timeout(generation, row, definition, ''):
                        receipt = read(termination)
                        if receipt.get('exit_code') not in (None, 0):
                            result['status'] = 'tool_failure'
                raise ValueError('generation_process_failed')
            if row['tool'] == 'MAZE':
                module = importlib.util.spec_from_file_location('gate', envroot / 'maze_validate_generation.py')
                gate = importlib.util.module_from_spec(module)
                module.loader.exec_module(gate)
                batch = gate.validate(generation, require_finished=False)
                if batch['experiment'] != experiment or batch['mazeJarSha256'] != digest(envroot / 'maze/maze.jar') or len(batch['invocations']) != 1:
                    raise ValueError('completion_configuration_mismatch')
                evidence = batch['invocations'][0]
                completion = read(generation / 'temp' / evidence['status'])
                if completion['seed'] != row['seed'] or completion['target'] != target or evidence['timeBudget'] != row['budget']:
                    raise ValueError('completion_seed_target_budget_mismatch')
                replay = completion.get('candidateReplay', {})
                if replay.get('maxTraceEntries') != 10000 or replay.get('maxSymbolicSteps') != 10000:
                    raise ValueError('candidate_replay_limit_mismatch')
                result['completion'] = completion
                source = generation / 'temp/maze-tests'
            else:
                # External wrappers must attest to the actual seed passed into the tool.
                seed = read(generation / 'seed.json')
                if seed != {'seed': row['seed'], 'tool': row['tool'], 'version': definition['version']}:
                    raise ValueError('external_seed_receipt_mismatch')
                if 'Execution finished with no timeout' not in text:
                    raise ValueError('external_completion_missing')
                result['completion'] = seed
                source = generation / 'temp/testcases'
            if not list(source.rglob('*.java')):
                raise EmptyOutput('verified_empty_output')
            (generation / 'GENERATION_FINISHED.txt').touch()
            if phase == 'generation':
                result.update(status='generated', reason=None, suite=str(source.relative_to(root)),
                              generation_directory=str(generation.relative_to(root)))
                return finish()
        else:
            source = root / generation_record['suite']
            result['completion'] = generation_record['completion']
        if (generation / 'trdir').exists():
            shutil.copytree(generation / 'trdir', metrics / 'trdir')
        # JUGE writes compiled tests and mutation reports beside its input suite.
        # Keep generation evidence intact and all metric outputs under metrics/.
        metric_source = metrics / 'test-source'
        shutil.copytree(source, metric_source)
        code = invoke(metrics, ['--only-compute-metrics', str(metric_source)])
        result['metrics_exit'] = code
        if code:
            raise ValueError('metrics_process_failed')
        text = logs(metrics)
        if list(metrics.rglob('MUTATION_ERROR.txt')):
            raise ValueError('juge_mutation_error')
        if list(metrics.rglob('TIMEOUT.txt')):
            raise ValueError('juge_mutation_timeout')
        if 'Evaluation not completed ignore it' in text:
            raise ValueError('juge_mutation_incomplete')
        if 'Could not calculate coverage metrics!' in text:
            raise ValueError('coverage_failed')
        if row['experiment'] == 'B' and phase != 'coverage' and ('Could not calculate mutation metrics!' in text or not list(metrics.rglob('mutation_results.txt'))):
            raise ValueError('mutation_failed_or_missing')
        with (metrics / 'transcript.csv').open() as f:
            rows = [r for r in csv.DictReader(f) if (r.get('class') or '').strip()]
        if len(rows) != 1:
            raise ValueError('expected_one_transcript_row')
        raw = rows[0]
        if raw['class'] != target or raw['tool'] != tool or int(raw['run']) != row['repetition'] or int(raw['timeBudget']) != row['budget']:
            raise ValueError('transcript_coordinates_mismatch')
        result['transcript'] = raw
        total, covered = int(raw['conditionsTotal']), int(raw['conditionsCovered'])
        if not 0 <= covered <= total or total <= 0:
            raise ValueError('branch_counts_invalid')
        result.update(branch_total=total, branch_covered=covered, coverage=covered / total)
        if row['experiment'] == 'B' and phase != 'coverage':
            total, killed = int(raw['mutantsTotal']), int(raw['mutantsKilled'])
            if not 0 <= killed <= total or total <= 0:
                raise ValueError('mutant_counts_invalid_or_zero')
            result.update(mutant_count=total, mutants_killed=killed, mutation_kill=killed / total)
            reports = list(metrics.rglob('mutation_results.txt'))
            if len(reports) != 1:
                raise ValueError('expected_one_mutation_report')
            report = reports[0].read_text()
            generated_match = re.search(r'N\. of generated mutants (\d+)', report)
            ignored_match = re.search(r'N\. of ignored mutants (\d+)', report)
            if not generated_match or not ignored_match:
                raise ValueError('mutation_report_counts_missing')
            generated = int(generated_match.group(1))
            ignored = int(ignored_match.group(1))
            if generated - ignored != total:
                raise ValueError('mutant_denominator_mismatch')
            result.update(mutants_generated=generated, mutants_ignored=ignored)
        result.update(status='ok', reason=None)
    except ToolTimeout as e:
        result.update(status='tool_timeout', reason=str(e))
    except EmptyOutput as e:
        result.update(status='empty', reason=str(e))
    except (OSError, ValueError, KeyError, TypeError) as e:
        result['reason'] = str(e)
    return finish()


if __name__ == '__main__':
    root = Path('/results')
    row = next(r for r in read(root / 'manifest.json')['runs'] if r['id'] == sys.argv[1])
    phase = sys.argv[3] if len(sys.argv) > 3 else 'all'
    generation_record = read(root / sys.argv[4]) if len(sys.argv) > 4 else None
    run_one(root, row, sys.argv[2], phase, generation_record)
