from pathlib import Path
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import campaign
from common import B_TREATMENT_POLICY, atomic, digest, identity, matrix, read, required_certificates, valid_record


class CampaignTests(unittest.TestCase):
    def test_preflight_waiver_is_explicit_and_keeps_rehearsal_gate(self):
        self.assertEqual(required_certificates({}), ('preflight.json', 'preflight-B.json', 'rehearsal.json'))
        policy = dict(version=1, full_preflights='operator_waiver', rehearsal='required', reason='operator requested no rerun')
        self.assertEqual(required_certificates(dict(validation_policy=policy)), ('rehearsal.json',))
        for changed in [dict(policy, reason=' '), dict(policy, rehearsal='waived'), dict(policy, version=2)]:
            with self.assertRaises(ValueError):
                required_certificates(dict(validation_policy=changed))

    def test_waived_cli_needs_no_fabricated_preflight_certificates(self):
        row = next(r for r in matrix() if r['experiment'] == 'B' and r['tool'] == 'MAZE')
        spec = dict(self.spec, runs=[row], environment={}, purpose='production',
                    b_treatment_policy=dict(B_TREATMENT_POLICY),
                    validation_policy=dict(version=1, full_preflights='operator_waiver',
                                           rehearsal='required', reason='operator requested no rerun'))
        atomic(self.root / 'rehearsal.json', dict(manifest_id='m', environment_id=identity({}), runs=[]))
        with patch.object(sys, 'argv', ['campaign.py', 'generate', '--results', str(self.root), '--experiment', 'B']), \
                patch.object(campaign, 'manifest', return_value=spec), \
                patch.object(campaign, 'verify_environment'), \
                patch.object(campaign, 'capacity', return_value={}), \
                patch.object(campaign, 'ProgressReporter'), \
                patch.object(campaign.signal, 'signal'), \
                patch.object(campaign, 'reconcile'), \
                patch.object(campaign, 'run_stage', return_value=True) as stages:
            campaign.main()
        self.assertEqual(stages.call_args.args[3], 'generation')
        self.assertFalse((self.root / 'preflight.json').exists())
        self.assertFalse((self.root / 'preflight-B.json').exists())

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.rows = matrix()[:4]
        self.spec = dict(id='m', campaign=dict(generation_jobs=2, measurement_jobs=2))

    def record(self, row, phase, status, **extra):
        evidence = self.root / 'fixture' / (row['id'] + phase)
        evidence.parent.mkdir(exist_ok=True)
        evidence.write_text(status)
        record = dict(run=row, manifest_id='m', status=status, phase=phase, reason=None,
                      evidence={str(evidence.relative_to(self.root)): digest(evidence)}, **extra)
        campaign.publish(campaign.stage_path(self.root, row, phase), record)
        return record

    def test_parallel_bound_and_successful_generation_never_retried(self):
        active = peak = 0
        mutex = threading.Lock()
        seen = []
        def execute(root, spec, row, phase, stop):
            nonlocal active, peak
            with mutex:
                active += 1
                peak = max(peak, active)
                seen.append(row['id'])
            time.sleep(.02)
            rec = self.record(row, phase, 'generated')
            with mutex:
                active -= 1
            return rec
        with patch.object(campaign, 'execute', side_effect=execute):
            campaign.run_stage(self.root, self.spec, self.rows, 'generation', threading.Event())
            campaign.run_stage(self.root, self.spec, self.rows, 'generation', threading.Event())
        self.assertEqual(len(seen), 4)
        self.assertEqual(peak, 2)

    def test_tool_failures_are_terminal_and_zero_scoreable(self):
        row = self.rows[0]
        self.record(row, 'generation', 'tool_failure')
        with patch.object(campaign, 'execute') as execute:
            campaign.run_stage(self.root, self.spec, [row], 'generation', threading.Event())
            campaign.run_stage(self.root, self.spec, [row], 'coverage', threading.Event())
            execute.assert_not_called()
        self.assertTrue(campaign.assemble(self.root, self.spec, [row]))
        from common import scored
        rec = valid_record(self.root, row, 'm')
        self.assertEqual(scored(rec)['coverage'], 0)
        self.assertNotIn('branch_total', rec)

    def test_missing_mutation_keeps_coverage_and_cannot_be_zero(self):
        row = next(r for r in matrix() if r['experiment'] == 'B')
        self.record(row, 'generation', 'generated')
        self.record(row, 'coverage', 'ok', coverage=.75, branch_total=4, branch_covered=3)
        self.assertFalse(campaign.assemble(self.root, self.spec, [row]))
        rec = valid_record(self.root, row, 'm')
        self.assertEqual(rec['coverage'], .75)
        self.assertEqual(rec['status'], 'excluded')
        self.assertNotIn('mutation_kill', rec)

    def test_corrupted_generation_stops_before_measurement(self):
        row = self.rows[0]
        rec = self.record(row, 'generation', 'generated')
        (self.root / next(iter(rec['evidence']))).write_text('changed')
        with patch.object(campaign, 'execute') as execute:
            with self.assertRaisesRegex(ValueError, 'Changed attempt evidence'):
                campaign.run_stage(self.root, self.spec, [row], 'coverage', threading.Event())
            execute.assert_not_called()

    def test_only_proven_startup_failure_allows_generation_retry(self):
        for reason in ('worker_failed', 'outer_watchdog_timeout', 'generation_process_failed'):
            self.assertFalse(campaign.retryable(dict(status='excluded', reason=reason), 'generation'))
        self.assertTrue(campaign.retryable(dict(status='excluded', reason='container_start_failed'), 'generation'))

    def test_retry_budget_is_finite(self):
        row = self.rows[0]
        self.record(row, 'generation', 'generated')
        calls = []
        def execute(root, spec, row, phase, stop):
            calls.append(phase)
            (root / 'attempts' / row['id'] / (phase + '-' + str(len(calls)))).mkdir(parents=True)
            rec = self.record(row, phase, 'excluded')
            rec['reason'] = 'worker_failed'
            campaign.publish(campaign.stage_path(root, row, phase), rec)
            return rec
        with patch.object(campaign, 'execute', side_effect=execute):
            campaign.run_stage(self.root, self.spec, [row], 'coverage', threading.Event())
            campaign.run_stage(self.root, self.spec, [row], 'coverage', threading.Event())
        self.assertEqual(calls, ['coverage', 'coverage'])

    def test_stop_launches_nothing(self):
        (self.root / 'STOP').touch()
        with patch.object(campaign, 'execute') as execute:
            self.assertFalse(campaign.run_stage(self.root, self.spec, self.rows, 'generation', threading.Event()))
            execute.assert_not_called()

    def test_lost_checkpoint_does_not_regenerate_a_previous_attempt(self):
        row = self.rows[0]
        (self.root / 'attempts' / row['id'] / 'generation-old').mkdir(parents=True)
        with patch.object(campaign, 'execute') as execute:
            with self.assertRaisesRegex(ValueError, 'Attempt exists without a checkpoint'):
                campaign.run_stage(self.root, self.spec, [row], 'generation', threading.Event())
            execute.assert_not_called()

    def test_reconcile_leaves_running_worker_alone(self):
        row = self.rows[0]
        active = dict(id=row['id'], phase='generation', attempt='attempts/example', container='fixture', started_at=1)
        with patch.object(campaign, 'docker_json', return_value=dict(Running=True)), patch.object(campaign.subprocess, 'run') as run:
            with self.assertRaisesRegex(ValueError, 'Worker still running'):
                campaign.finish_attempt(self.root, self.spec, row, active)
            run.assert_not_called()

    def test_collect_completed_orphan_without_regenerating(self):
        row = self.rows[0]
        work = self.root / 'attempts/example'
        work.mkdir(parents=True)
        raw = work / 'suite.java'
        raw.write_text('saved suite')
        record = dict(run=row, manifest_id='m', phase='generation', status='generated', reason=None,
                      evidence={'attempts/example/suite.java': digest(raw)})
        atomic(work / 'result.json', record)
        active = dict(id=row['id'], phase='generation', attempt='attempts/example', container='fixture', started_at=1)
        atomic(self.root / 'active' / (row['id'] + '.json'), active)
        with patch.object(campaign, 'docker_json', return_value=dict(Running=False, StartedAt='2026-01-01', ExitCode=0)), patch.object(campaign.subprocess, 'run') as run:
            rec = campaign.finish_attempt(self.root, self.spec, row, active)
            self.assertEqual(rec['status'], 'generated')
            self.assertEqual(run.call_args.args[0], ['docker', 'rm', 'fixture'])
        self.assertEqual(campaign.verified(self.root, campaign.stage_path(self.root, row, 'generation'))['status'], 'generated')
        self.assertFalse(list((self.root / 'active').glob('*.json')))

    def test_capacity_rejects_oversubscription(self):
        spec = dict(campaign=dict(generation_jobs=2, measurement_jobs=2, memory_gb=4, cpus=2))
        with patch.object(campaign, 'docker_json', return_value=dict(NCPU=8, MemTotal=8*1024**3)):
            with self.assertRaisesRegex(ValueError, 'exceeds Docker resources'):
                campaign.capacity(spec)

    def test_b_stages_are_independent_of_a_and_generate_never_measures(self):
        row = next(r for r in matrix() if r['experiment'] == 'B' and r['tool'] == 'MAZE')
        spec = dict(self.spec, runs=[self.rows[0], row], environment={},
                    purpose='production', b_treatment_policy=dict(B_TREATMENT_POLICY))
        for name in ('preflight.json', 'preflight-B.json', 'rehearsal.json'):
            atomic(self.root / name, dict(manifest_id='m', environment_id=identity({}), run_ids=[]))
        for command, expected in [('generate', ['generation']), ('measure', ['coverage', 'mutation'])]:
            with self.subTest(command=command), \
                    patch.object(sys, 'argv', ['campaign.py', command, '--results', str(self.root), '--experiment', 'B']), \
                    patch.object(campaign, 'manifest', return_value=spec), \
                    patch.object(campaign, 'verify_environment'), \
                    patch.object(campaign, 'capacity', return_value={}), \
                    patch.object(campaign, 'ProgressReporter'), \
                    patch.object(campaign.signal, 'signal'), \
                    patch.object(campaign, 'reconcile'), \
                    patch.object(campaign, 'run_stage', return_value=True) as stages, \
                    patch.object(campaign, 'assemble', return_value=True) as assemble:
                campaign.main()
                self.assertEqual([call.args[3] for call in stages.call_args_list], expected)
                self.assertTrue(all(call.args[2] == [row] for call in stages.call_args_list))
                if command == 'generate':
                    assemble.assert_not_called()
            self.assertEqual(read(self.root / 'selection.json')['treatment'], 'FOS+COS')
        self.assertFalse((self.root / 'runs').exists())

    def test_full_fixed_campaign_generates_both_experiments_before_measurement(self):
        b_row = next(r for r in matrix() if r['experiment'] == 'B' and r['tool'] == 'MAZE')
        spec = dict(self.spec, runs=[self.rows[0], b_row], environment={},
                    purpose='production', b_treatment_policy=dict(B_TREATMENT_POLICY))
        for name in ('preflight.json', 'preflight-B.json', 'rehearsal.json'):
            atomic(self.root / name, dict(manifest_id='m', environment_id=identity({}), run_ids=[]))
        with patch.object(sys, 'argv', ['campaign.py', 'run', '--results', str(self.root)]), \
                patch.object(campaign, 'manifest', return_value=spec), \
                patch.object(campaign, 'verify_environment'), \
                patch.object(campaign, 'capacity', return_value={}), \
                patch.object(campaign, 'ProgressReporter'), \
                patch.object(campaign.signal, 'signal'), \
                patch.object(campaign, 'reconcile'), \
                patch.object(campaign, 'run_stage', return_value=True) as stages, \
                patch.object(campaign, 'assemble', return_value=True):
            campaign.main()
        self.assertEqual([(call.args[2][0]['experiment'], call.args[3]) for call in stages.call_args_list],
                         [('A', 'generation'), ('B', 'generation'), ('A', 'coverage'),
                          ('B', 'coverage'), ('B', 'mutation')])
