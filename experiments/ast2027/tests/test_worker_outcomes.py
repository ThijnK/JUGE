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
    def exercise(self, timeout=False, receipt=True, seed_matches=True):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            row=next(r for r in matrix() if r['tool']=='T3')
            atomic(root/'manifest.json',dict(id='m',host={}))
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
                (directory/'temp/testcases').mkdir(parents=True)
                return SimpleNamespace(returncode=1 if timeout else 0)
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
