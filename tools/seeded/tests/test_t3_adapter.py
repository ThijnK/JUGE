import contextlib
import io
import json
import os
from pathlib import Path
import runpy
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import generation


class T3AdapterTests(unittest.TestCase):
    def invoke(self, mode):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            script = root / 'runtool'
            shutil.copy2(Path(__file__).resolve().parents[1] / 't3/runtool', script)
            (root / 'lib').mkdir()
            (root / 'lib/t3.jar').touch()
            module = runpy.run_path(str(script))
            real_run = generation.run
            def execute(command, **kwargs):
                self.assertEqual(command[-12:], ['42', 'generate', 'Example', 'classes',
                    'trdir', 'temp/testcases', '60000', 'random', 'evo', '5', 'true', 'false'])
                self.assertEqual(kwargs['timeout'], 120)
                code = 'import pathlib,sys,time; '
                if mode not in ('crash', 'deadline', 'watchdog_empty'):
                    code += "pathlib.Path('temp/testcases').mkdir(parents=True); pathlib.Path('temp/testcases/Test.java').write_text('class Test {}'); "
                if mode.startswith('watchdog'):
                    code += "print('WARNING: ** G2 has timeout! (70000). Performing system exit...',flush=True); "
                if mode == 'fatal':
                    code += "print('Exception in thread \"main\" java.lang.Error',flush=True); "
                if mode == 'deadline':
                    code += 'time.sleep(30); '
                code += 'sys.exit(255 if ' + repr(mode != 'crash') + ' else 1)'
                return real_run([sys.executable, '-c', code], **dict(kwargs, timeout=.1 if mode == 'deadline' else 3))
            output = io.StringIO()
            previous = Path.cwd()
            try:
                os.chdir(root)
                with patch.dict(os.environ, JUGE_TOOL_SEED='42'), patch('sys.stdin', io.StringIO('BENCHMARK\nsrc\nclasses\n0\n1\n60\nExample\n')), patch.object(generation, 'run', side_effect=execute), contextlib.redirect_stdout(output):
                    if mode in ('crash', 'fatal', 'watchdog_empty'):
                        with self.assertRaises(subprocess.CalledProcessError):
                            module['main']()
                    elif mode == 'deadline':
                        with self.assertRaises(subprocess.TimeoutExpired):
                            module['main']()
                    else:
                        module['main']()
                return (output.getvalue().splitlines().count('READY'),
                        json.loads((root / 't3-outcome.json').read_text()),
                        (root / 'seed.json').exists(), (root / 'timeout.json').exists())
            finally:
                os.chdir(previous)

    def test_normal_upstream_minus_one_is_accepted_with_saved_tests(self):
        ready, receipt, seeded, timeout = self.invoke('normal')
        self.assertEqual((ready, seeded, timeout), (2, True, False))
        self.assertEqual(receipt['outcome'], 'normal_completion')
        self.assertEqual(receipt['exit_code'], 255)

    def test_upstream_watchdog_keeps_partial_saved_suite(self):
        ready, receipt, seeded, timeout = self.invoke('watchdog')
        self.assertEqual((ready, seeded, timeout), (2, True, False))
        self.assertEqual(receipt['outcome'], 'upstream_watchdog')
        self.assertTrue(receipt['generated_tests'])

    def test_outer_deadline_remains_terminal_timeout(self):
        ready, receipt, seeded, timeout = self.invoke('deadline')
        self.assertEqual((ready, seeded, timeout), (1, False, True))
        self.assertEqual(receipt['outcome'], 'adapter_timeout')

    def test_crash_and_fatal_partial_output_are_not_accepted(self):
        for mode in ('crash', 'fatal'):
            with self.subTest(mode=mode):
                ready, receipt, seeded, timeout = self.invoke(mode)
                self.assertEqual((ready, seeded, timeout), (1, False, False))
                self.assertEqual(receipt['outcome'], 'tool_failure')

    def test_watchdog_without_saved_tests_is_not_successful_empty(self):
        ready, receipt, seeded, timeout = self.invoke('watchdog_empty')
        self.assertEqual((ready, seeded, timeout), (1, False, False))
        self.assertEqual(receipt['outcome'], 'upstream_watchdog')
