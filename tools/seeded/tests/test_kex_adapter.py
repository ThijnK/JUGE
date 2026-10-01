import contextlib
import io
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

class KexAdapterTests(unittest.TestCase):
    def invoke(self, failed):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            script = root / 'runtool'
            shutil.copy2(Path(__file__).resolve().parents[1] / 'kex/runtool', script)
            home = root / 'lib/kex'
            jar = home / 'kex-runner/target/kex-runner-0.0.11-jar-with-dependencies.jar'
            jar.parent.mkdir(parents=True)
            jar.touch()
            (home / 'kex.ini').write_text(''.join('['+n+']\nx = 1\n\n' for n in ('easy-random','ksmt','concolic','kex','testGen','executor')))
            module = runpy.run_path(str(script))
            def run(*args, **kwargs):
                kwargs['stdout'].write('[ERROR] Failed to generate random trace\n')
                if failed:
                    raise subprocess.CalledProcessError(1, args[0])
            output = io.StringIO()
            previous = Path.cwd()
            try:
                os.chdir(root)
                with patch.dict(os.environ, JUGE_TOOL_SEED='42'), patch('platform.system', return_value='Linux'), patch('platform.machine', return_value='x86_64'), patch('sys.stdin', io.StringIO('BENCHMARK\nsrc\nclasses\n0\n1\n60\nExample\n')), patch.object(generation, 'run', side_effect=run), contextlib.redirect_stdout(output):
                    if failed:
                        with self.assertRaises(subprocess.CalledProcessError):
                            module['main']()
                    else:
                        module['main']()
                return output.getvalue().splitlines().count('READY'), (root / 'seed.json').exists()
            finally:
                os.chdir(previous)

    def test_recoverable_log_error_does_not_override_successful_exit(self):
        self.assertEqual(self.invoke(False), (2, True))

    def test_actual_generator_failure_never_signals_completion(self):
        self.assertEqual(self.invoke(True), (1, False))
