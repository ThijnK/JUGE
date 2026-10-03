"""Scientific outcome policy: real failures never disappear into success-only means."""
import csv
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common
from worker import confirmed_timeout
try:
    import analyze
except ImportError:
    analyze = None


class OutcomeTests(unittest.TestCase):
    def test_only_confirmed_outcomes_are_scoreable(self):
        for status in ('tool_timeout', 'empty'):
            rec = dict(status=status)
            self.assertEqual(common.scored(rec)['coverage'], 0)
            self.assertNotIn('coverage', rec)
            self.assertIsNone(common.scored(rec)['mutant_count'])
        self.assertFalse(common.scoreable(None))
        with self.assertRaises(ValueError):
            common.scored(dict(status='excluded'))

    def test_timeout_needs_matching_invocation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            row = dict(tool='T3', subject='BinarySearch', seed=123, budget=60)
            definition = dict(version='pinned')
            self.assertFalse(confirmed_timeout(root, row, definition, 'hash'))
            common.atomic(root / 'invocation.json', dict(tool='T3', version='pinned', seed=123,
                target='nl.uu.maze.benchmarks.BinarySearch', budget=60))
            self.assertTrue(confirmed_timeout(root, row, definition, 'hash'))
            self.assertFalse(confirmed_timeout(root, dict(row, seed=124), definition, 'hash'))

    def test_selection_includes_timeouts_and_blocks_unresolved_cells(self):
        spec = dict(id='m', runs=common.matrix(), selection_rule='fixture')
        def receipt(root, row, manifest):
            if row['treatment'] == 'DFS' and row['repetition'] > 1:
                return dict(status='tool_timeout')
            return dict(status='ok', coverage=.9 if row['treatment']=='DFS' else
                        (.4 if row['treatment']=='BFS' else .1))
        with patch.object(common, 'valid_record', side_effect=receipt):
            result = common.selection(Path('.'), spec)
        self.assertEqual(result['treatment'], 'BFS')
        self.assertAlmostEqual(result['scores']['DFS'], .09)
        with patch.object(common, 'valid_record', return_value=dict(status='excluded')):
            self.assertIsNone(common.selection(Path('.'), spec))

    def test_fixed_b_treatment_never_reads_a_outcomes(self):
        spec = dict(id='m', runs=common.matrix(), b_treatment_policy=dict(common.B_TREATMENT_POLICY))
        with patch.object(common, 'valid_record', side_effect=AssertionError('A must not choose B')) as records:
            result = common.selection(Path('.'), spec)
        records.assert_not_called()
        self.assertEqual(result['treatment'], 'FOS+COS')
        self.assertEqual(result['source'], 'fixed')
        self.assertNotIn('scores', result)

    def test_fixed_b_worker_needs_no_selection_file_and_rejects_override(self):
        spec = dict(id='m', b_treatment_policy=dict(common.B_TREATMENT_POLICY))
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.assertEqual(common.b_treatment(root, spec), 'FOS+COS')
            self.assertFalse((root / 'selection.json').exists())
            common.atomic(root / 'selection.json', common.selection(root, spec))
            self.assertEqual(common.b_treatment(root, spec), 'FOS+COS')
            common.atomic(root / 'selection.json', dict(manifest_id='m', treatment='BFS'))
            with self.assertRaisesRegex(ValueError, 'conflicts'):
                common.b_treatment(root, spec)

    def test_fixed_b_manifest_cannot_choose_another_strategy(self):
        for policy in [dict(common.B_TREATMENT_POLICY, treatment='BFS'),
                       dict(common.B_TREATMENT_POLICY, mode='adaptive')]:
            with self.assertRaisesRegex(ValueError, 'Unsupported frozen B'):
                common.selection(Path('.'), dict(id='m', b_treatment_policy=policy))

    @unittest.skipIf(analyze is None, 'Run in the benchmark image for SciPy')
    def test_exports_keep_zero_outcomes_distinct_from_missing_measurements(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'env').mkdir()
            (root / 'env/subject-characteristics.csv').write_text('subject,methods\nBinarySearch,2\n')
            common.atomic(root / 'suite/feature-tags.json', {'BinarySearch':['search']})
            rows = [r for r in common.matrix() if r['subject']=='BinarySearch' and
                    ((r['experiment']=='A' and r['treatment']=='BFS' and r['budget']==10) or
                     (r['experiment']=='B' and r['tool']=='T3'))][:]
            rows = [r for r in rows if r['repetition'] <= 5]
            common.atomic(root / 'manifest.json', dict(id='m', runs=rows, statistics_policy='fixture', outcome_policy=common.OUTCOME_POLICY))
            proof = root / 'proof'; proof.write_text('fixture')
            for row in rows:
                status = {1:'ok',2:'tool_timeout',3:'empty',4:'excluded',5:None}[row['repetition']]
                if status is None: continue
                rec = dict(run=row, manifest_id='m', status=status, reason=None if status=='ok' else status,
                           evidence={'proof':common.digest(proof)})
                if status=='ok':
                    rec.update(coverage=.9, mutation_kill=.6, mutant_count=10, mutants_generated=12, mutants_ignored=2)
                rec['record_sha256'] = common.identity(rec)
                common.atomic(root / 'runs' / (row['id']+'.json'), rec)
            analyze.analyze(root)
            def table(name):
                with (root / 'stats' / name).open() as f: return list(csv.DictReader(f))
            a = table('A_all_cells.csv')[0]; b = table('B_subjects.csv')[0]
            self.assertEqual(int(a['n']), 3)
            self.assertAlmostEqual(float(a['mean']), .3)
            self.assertAlmostEqual(float(b['mean']), .2)
            self.assertEqual(b['mutant_counts'], '[10]')
            self.assertEqual(float(table('successful-only/A_all_cells.csv')[0]['mean']), .9)
            for row in table('outcomes.csv'):
                self.assertEqual([int(row[k]) for k in ('measured','tool_timeout','empty','unresolved','pending_or_unverifiable')], [1,1,1,1,1])
            self.assertFalse((root / 'selection.json').exists())


if __name__ == '__main__':
    unittest.main()
