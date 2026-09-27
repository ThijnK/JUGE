import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import generation

class GenerationTests(unittest.TestCase):
    def invoke(self, code, timeout=3):
        return generation.run([sys.executable, '-c', code], tool='fixture', version='1',
                              seed=42, target='Example', budget=1, timeout=timeout,
                              stdout=subprocess.DEVNULL)

    def test_success_and_deadline_have_distinct_evidence(self):
        previous=Path.cwd()
        with tempfile.TemporaryDirectory() as tmp:
            try:
                os.chdir(tmp)
                self.invoke('pass')
                self.assertEqual(json.loads(Path('invocation.json').read_text())['seed'],42)
                self.assertFalse(Path('timeout.json').exists())
                with self.assertRaises(subprocess.TimeoutExpired):
                    self.invoke('import time; time.sleep(5)', timeout=.1)
                self.assertEqual(json.loads(Path('timeout.json').read_text())['reason'],'adapter_generation_timeout')
            finally:
                os.chdir(previous)

    def test_process_failure_is_not_a_timeout(self):
        previous=Path.cwd()
        with tempfile.TemporaryDirectory() as tmp:
            try:
                os.chdir(tmp)
                with self.assertRaises(subprocess.CalledProcessError):
                    self.invoke('raise SystemExit(2)')
                self.assertTrue(Path('invocation.json').exists())
                self.assertFalse(Path('timeout.json').exists())
            finally:
                os.chdir(previous)
