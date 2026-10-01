"""Progress is informational: no imputation, retries, or evidence mutation."""
import contextlib
import io
from pathlib import Path
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import campaign
import progress
from common import atomic, fingerprint, read


class ProgressTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.rows = [dict(id='case-' + str(i), experiment='B') for i in range(4)]
        self.spec = dict(runs=self.rows)

    def stage(self, index, phase, outcome, **extra):
        atomic(self.root/'stages'/phase/(self.rows[index]['id']+'.json'),
               dict(status=outcome, finished_at=10, **extra))

    def test_tool_zeros_unresolved_and_pending_stay_distinct(self):
        self.stage(0, 'generation', 'tool_timeout')
        self.stage(1, 'generation', 'excluded', reason='worker_failed')
        self.stage(2, 'generation', 'generated')
        self.stage(2, 'coverage', 'ok')
        before = fingerprint(self.root/'stages')
        with contextlib.redirect_stdout(io.StringIO()), progress.ProgressReporter(self.root,self.spec,'run'):
            pass
        report = progress.snapshot(self.root,self.rows)
        self.assertEqual(report['phases']['B generation']['resolved'],2)
        self.assertEqual(report['phases']['B coverage']['outcomes'],
                         dict(not_required=1,blocked_by_generation=1,ok=1,pending=1))
        self.assertEqual(report['phases']['B mutation']['outcomes'],
                         dict(not_required=1,blocked_by_generation=1,pending=2))
        self.assertEqual(report['unresolved_reasons'],dict(worker_failed=1))
        self.assertEqual(before,fingerprint(self.root/'stages'))

    def test_schedule_and_final_error_report(self):
        with contextlib.redirect_stdout(io.StringIO()), patch.object(progress.time,'monotonic',return_value=100) as clock:
            reporter=progress.ProgressReporter(self.root,self.spec,'run',interval=30)
            with self.assertRaisesRegex(RuntimeError,'worker evidence invalid'):
                with reporter:
                    clock.return_value=129
                    reporter.report()
                    clock.return_value=130
                    reporter.report()
                    raise RuntimeError('worker evidence invalid')
        import json
        records=[json.loads(line) for line in reporter.log.read_text().splitlines()]
        self.assertEqual([r['event'] for r in records],['started','progress','failed'])
        self.assertEqual(records[1]['elapsed_seconds'],30)
        self.assertEqual(records[-1]['error'],'worker evidence invalid')

    def test_stop_is_not_reported_as_success(self):
        reporter=progress.ProgressReporter(self.root,self.spec,'run')
        reporter.stop=threading.Event()
        with contextlib.redirect_stdout(io.StringIO()), reporter:
            reporter.stop.set()
        import json
        self.assertEqual(json.loads(reporter.log.read_text().splitlines()[-1])['event'],'stopped')

    def test_reporting_failure_does_not_hide_worker_exception(self):
        with contextlib.redirect_stdout(io.StringIO()) as output:
            with patch.object(progress,'snapshot',side_effect=OSError('cannot read status')):
                with self.assertRaisesRegex(RuntimeError,'worker failed'):
                    with progress.ProgressReporter(self.root,self.spec,'run'):
                        raise RuntimeError('worker failed')
        self.assertIn('report_error: cannot read status',output.getvalue())
        self.assertIn('error: worker failed',output.getvalue())

    def test_long_running_worker_gets_periodic_report_before_completion(self):
        row=self.rows[0]
        spec=dict(id='fixture',runs=[row],campaign=dict(generation_jobs=1))
        reporter=progress.ProgressReporter(self.root,spec,'run',interval=.05)
        atomic(self.root/'active'/'case-0.json',dict(id=row['id'],phase='generation',started_at=time.time()))
        def execute(root,spec,row,phase,stop):
            time.sleep(1.2)
            return dict(status='generated',reason=None)
        with contextlib.redirect_stdout(io.StringIO()), patch.object(campaign,'execute',side_effect=execute), reporter:
            self.assertTrue(campaign.run_stage(self.root,spec,[row],'generation',threading.Event(),reporter))
        import json
        periodic=[json.loads(s) for s in reporter.log.read_text().splitlines() if json.loads(s)['event']=='progress']
        self.assertTrue(periodic)
        self.assertEqual(periodic[0]['active'][0]['id'],row['id'])
        self.assertEqual(periodic[0]['phases']['B generation']['resolved'],0)
