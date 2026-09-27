"""Failure/restart and integrity regression tests; these do not launch Docker."""
import contextlib
import io
import json
from pathlib import Path
import signal
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bench
from worker import instantiate
from common import BASE, OPTIONS, SUBJECTS, atomic, digest, identity, matrix, read, valid_record


class MatrixTests(unittest.TestCase):
    def test_attempts_share_dependencies_but_keep_outputs_separate(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            template = root / "env/tool"
            (template / "lib").mkdir(parents=True)
            (template / "lib/runtime.jar").write_bytes(b"frozen")
            (template / "runtool").write_text("wrapper")
            for name in ("generation", "metrics"):
                instantiate(template, root / name)
                self.assertTrue((root / name / "lib").is_symlink())
                self.assertEqual((root / name / "lib/runtime.jar").read_bytes(), b"frozen")
            (root / "generation/output").write_text("test")
            self.assertFalse((root / "metrics/output").exists())

    def test_design_and_order(self):
        rows = matrix()
        self.assertEqual(len(rows), 3600)
        self.assertEqual(len({r['id'] for r in rows}), 3600)
        a = [r for r in rows if r['experiment'] == 'A']
        self.assertEqual(len(a), 2800)
        self.assertEqual({r['repetition'] for r in a[:280]}, {1})
        self.assertEqual({r['repetition'] for r in a[280:560]}, {2})
        for r in a:
            self.assertEqual(r['kind'], 'combinator' if r['treatment'] == 'FOS+COS' else 'base')
        for subject in SUBJECTS:
            self.assertEqual(len({r['seed'] for r in a if r['subject'] == subject and r['budget'] == 10}), 10)
        self.assertEqual(len(matrix(5)), 3200)

    def test_corrupted_artifact_and_coordinates_force_retry(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            row = matrix()[0]
            proof = root / 'proof'
            proof.write_text('fresh completion')
            record = dict(run=row, manifest_id='m', status='ok', evidence={'proof': digest(proof)})
            record['record_sha256'] = identity(record)
            atomic(root / 'runs' / (row['id'] + '.json'), record)
            self.assertIsNotNone(valid_record(root, row, 'm'))
            self.assertIsNone(valid_record(root, row, 'different'))
            self.assertIsNone(valid_record(root, dict(row, seed=123), 'm'))
            proof.write_text('stale')
            self.assertIsNone(valid_record(root, row, 'm'))

    def test_exclusion_is_terminal_but_interruption_is_not(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            row = matrix()[0]
            proof = root / 'proof'
            proof.write_text('failed process')
            for status, expected in [('excluded', True), ('incomplete', False)]:
                record = dict(run=row, manifest_id='m', status=status, evidence={'proof': digest(proof)})
                record['record_sha256'] = identity(record)
                atomic(root / 'runs' / (row['id'] + '.json'), record)
                self.assertEqual(valid_record(root, row, 'm') is not None, expected)

    def test_signal_stops_container_and_does_not_publish_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            row = matrix()[0]
            class Process:
                returncode = -15
                def poll(self):
                    signal.raise_signal(signal.SIGTERM)
                    return None
                def wait(self, **kwargs):
                    return -15
            with patch.object(bench.subprocess, 'Popen', return_value=Process()), patch.object(bench, 'remove_container') as cleanup:
                result = bench.execute(root, {'image': 'frozen'}, row, 30)
                self.assertIsNone(result)
                self.assertTrue(cleanup.call_args.args[0].startswith('ast2027-'))
            self.assertFalse((root / 'runs').exists())
            self.assertTrue((root / 'incomplete' / (row['id'] + '.json')).exists())
            self.assertFalse((root / 'active.json').exists())

    def test_manifest_edit_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            spec = {'runs': matrix()}
            spec['id'] = identity(spec)
            atomic(root / 'manifest.json', spec)
            self.assertEqual(bench.manifest(root), spec)
            spec['runs'][0]['budget'] = 1
            atomic(root / 'manifest.json', spec)
            with self.assertRaises(SystemExit):
                bench.manifest(root)

    def test_resume_is_noop_for_verified_terminal_runs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            row = matrix()[0]
            spec = dict(id='m', purpose='production', environment={}, suite={}, runs=[row])
            atomic(root / 'preflight.json', dict(environment_id=identity({})))
            proof = root / 'proof'
            proof.write_text('completed')
            rec = dict(run=row, manifest_id='m', status='ok', evidence={'proof': digest(proof)})
            rec['record_sha256'] = identity(rec)
            atomic(root / 'runs' / (row['id'] + '.json'), rec)
            args = SimpleNamespace(command='run', experiment='A', hours=1, max_runs=5, min_free_gb=0, retry_excluded=False)
            with patch.object(bench, 'execute') as execute:
                self.assertEqual(bench.run(args, root, spec), 0)
                execute.assert_not_called()
            self.assertEqual(read(root / 'runs' / (row['id'] + '.json')), rec)

    def test_environment_changes_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'env').mkdir()
            (root / 'env/tool.jar').write_text('changed')
            with self.assertRaises(SystemExit):
                bench.verify_environment(root, {'environment': {}, 'suite': {}})


if __name__ == '__main__':
    unittest.main()
