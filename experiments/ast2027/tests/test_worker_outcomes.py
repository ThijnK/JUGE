"""Exercise worker receipts/classification with JUGE's process boundary replaced."""
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from common import atomic, matrix
import worker

class WorkerOutcomeTests(unittest.TestCase):
    def exercise(self, timeout=False, receipt=True, seed_matches=True, exit_code=0, watchdog=False):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            row=next(r for r in matrix() if r['tool']=='T3')
            atomic(root/'manifest.json',dict(id='m',host={},campaign={'enabled':True}))
            atomic(root/'env/versions.json',{})
            atomic(root/'env/tools.json',{'T3':dict(version='v',seed_env='JUGE_TOOL_SEED')})
            (root/'env/tools/T3').mkdir(parents=True)
            (root/'env/tools/T3/runtool').write_text('fixture')
            (root/'env/maze').mkdir()
            (root/'env/maze/maze.jar').write_bytes(b'fixture')
            def juge(command, **kwargs):
                directory=kwargs['cwd']
                kwargs['stdout'].write('A timeout occurred waiting for signal READY' if timeout else 'Execution finished with no timeout')
                atomic(directory/'seed.json',dict(seed=row['seed'] if seed_matches else 0,tool='T3',version='v'))
                if receipt:
                    atomic(directory/'invocation.json',dict(tool='T3',version='v',seed=row['seed'] if seed_matches else 0,
                        target='nl.uu.maze.benchmarks.'+row['subject'],budget=row['budget']))
                if watchdog:
                    atomic(directory/'t3-outcome.json', dict(outcome='upstream_watchdog', generated_tests=[]))
                atomic(directory/'termination.json',dict(exit_code=exit_code))
                (directory/'temp/testcases').mkdir(parents=True)
                return SimpleNamespace(returncode=1 if timeout else exit_code)
            with patch.object(worker.subprocess,'run',side_effect=juge) as call:
                result=worker.run_one(root,row,'artifacts/attempt')
            self.assertEqual(call.call_count,1, 'empty/timeout must not fabricate measurement calls')
            self.assertTrue(result['evidence'])
            self.assertNotIn('coverage',result)
            self.assertNotIn('mutant_count',result)
            return result

    def test_verified_empty_is_an_outcome_without_fabricated_counts(self):
        self.assertEqual(self.exercise()['status'],'empty')
        self.assertEqual(self.exercise(seed_matches=False)['status'],'excluded')

    def test_timeout_requires_matching_start_evidence(self):
        self.assertEqual(self.exercise(timeout=True)['status'],'tool_timeout')
        self.assertEqual(self.exercise(timeout=True,receipt=False)['status'],'excluded')
        self.assertEqual(self.exercise(timeout=True,seed_matches=False)['status'],'excluded')

    def test_confirmed_native_failure_is_zero_scoreable_without_measurement(self):
        self.assertEqual(self.exercise(exit_code=7)['status'], 'tool_failure')
        self.assertEqual(self.exercise(exit_code=7, receipt=False)['status'], 'excluded')
        self.assertEqual(self.exercise(exit_code=7, seed_matches=False)['status'], 'excluded')

    def test_upstream_t3_watchdog_without_suite_is_timeout_not_empty(self):
        result = self.exercise(exit_code=255, watchdog=True)
        self.assertEqual(result['status'], 'tool_timeout')
        self.assertEqual(result['reason'], 't3_upstream_watchdog_without_saved_tests')
        self.assertEqual(self.exercise(exit_code=255, watchdog=True, receipt=False)['status'], 'excluded')
