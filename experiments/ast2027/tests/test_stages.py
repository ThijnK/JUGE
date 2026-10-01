"""Exercise actual worker stages without starting a generator twice."""
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import atomic, fingerprint, matrix
import worker

class StagesTests(unittest.TestCase):
    def test_measurement_uses_immutable_suite_without_generator_invocation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            row = next(r for r in matrix() if r['tool'] == 'T3')
            atomic(root/'manifest.json', dict(id='m', host={}, campaign={}))
            atomic(root/'env/versions.json', {})
            atomic(root/'env/tools.json', {'T3':dict(version='v', seed_env='JUGE_TOOL_SEED')})
            (root/'env/tools/T3').mkdir(parents=True)
            (root/'env/tools/T3/runtool').write_text('fixture')
            calls = []
            def juge(command, **kwargs):
                calls.append(command)
                directory = kwargs['cwd']
                if '--only-generate-tests' in command:
                    kwargs['stdout'].write('Execution finished with no timeout')
                    atomic(directory/'seed.json', dict(seed=row['seed'], tool='T3', version='v'))
                    (directory/'temp/testcases').mkdir(parents=True)
                    (directory/'temp/testcases/Example.java').write_text('class Example {}')
                else:
                    self.assertIn('--only-compute-metrics', command)
                    (directory/'transcript.csv').write_text('class,tool,run,timeBudget,conditionsTotal,conditionsCovered\n'
                        + 'nl.uu.maze.benchmarks.' + row['subject'] + ',t3,1,60,4,3\n')
                return SimpleNamespace(returncode=0)
            with patch.object(worker.subprocess, 'run', side_effect=juge):
                generated = worker.run_one(root, row, 'attempts/gen', 'generation')
                self.assertEqual(generated['status'], 'generated')
                before = fingerprint(root/'attempts/gen')
                cov = worker.run_one(root, row, 'attempts/cov', 'coverage', generated)
                again = worker.run_one(root, row, 'attempts/cov2', 'coverage', generated)
                self.assertEqual(cov['coverage'], .75)
                self.assertEqual(again['coverage'], .75)
                self.assertEqual(before, fingerprint(root/'attempts/gen'))
            self.assertEqual(sum('--only-generate-tests' in c for c in calls), 1)
