"""Numerical fixtures: ties, unequal samples, incomplete blocks and bytecode counts."""
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
try:
    import analyze
except ImportError:
    analyze = None
from common import B_TREATMENT_POLICY, atomic, digest, identity, matrix, read, TREATMENTS


@unittest.skipIf(analyze is None, 'Run in the benchmark image for SciPy')
class StatisticsTests(unittest.TestCase):
    def test_fixed_b_configuration_is_exported_without_a_observations(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'env').mkdir()
            (root / 'env/subject-characteristics.csv').write_text('subject,methods\nBinarySearch,2\n')
            atomic(root / 'suite/feature-tags.json', {'BinarySearch': ['search']})
            atomic(root / 'manifest.json', dict(id='m', runs=matrix(), statistics_policy='fixture',
                b_treatment_policy=dict(B_TREATMENT_POLICY)))
            analyze.analyze(root)
            self.assertEqual(read(root / 'selection.json')['treatment'], 'FOS+COS')
            availability = read(root / 'stats/availability.json')
            self.assertEqual(availability['scored'], 0)
            self.assertEqual(len(availability['missing']), 3600)

    def test_known_effect_sizes_and_ties(self):
        self.assertEqual(analyze.compare([1, 1], [0, 0])['a12'], 1.)
        self.assertEqual(analyze.compare([0, 0], [1, 1])['a12'], 0.)
        tied = analyze.compare([.5, .5], [.5, .5])
        self.assertEqual(tied['a12'], .5)
        self.assertEqual(tied['p'], 1.)
        self.assertEqual(analyze.describe([.25, .75])['mean'], .5)
        self.assertAlmostEqual(analyze.describe([.25, .75])['sd'], 2**.5 / 4)

    def test_all_tied_blocks_partial_matrix_and_missing_selection(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'env').mkdir()
            (root / 'env/subject-characteristics.csv').write_text('subject,methods\nBinarySearch,2\n')
            atomic(root / 'suite/feature-tags.json', {'BinarySearch': ['search']})
            rows = [r for r in matrix() if r['experiment'] == 'A' and r['subject'] in ('BinarySearch', 'BinaryTree') and r['budget'] == 10 and r['repetition'] == 1]
            spec = dict(id='m', runs=rows, statistics_policy='fixture')
            atomic(root / 'manifest.json', spec)
            proof = root / 'proof'
            proof.write_text('fixture')
            for row in rows:
                rec = dict(run=row, manifest_id='m', status='ok', coverage=.5, evidence={'proof': digest(proof)})
                rec['record_sha256'] = identity(rec)
                atomic(root / 'runs' / (row['id'] + '.json'), rec)
            analyze.analyze(root)
            self.assertEqual(read(root / 'stats/availability.json')['valid'], 14)
            self.assertEqual(len(read(root / 'stats/A_all_distinct_winners.json')['10']), 7)
            self.assertFalse((root / 'selection.json').exists())
            import csv
            with (root / 'stats/A_all_friedman.csv').open() as f:
                result = list(csv.DictReader(f))[0]
            self.assertEqual(float(result['statistic']), 0.)
            self.assertEqual(float(result['p']), 1.)
            self.assertGreater(float(result['critical_difference']), 0)
            # A modified raw number is excluded by integrity validation.
            path = root / 'runs' / (rows[0]['id'] + '.json')
            damaged = read(path)
            damaged['coverage'] = .9
            atomic(path, damaged)
            analyze.analyze(root)
            self.assertEqual(read(root / 'stats/availability.json')['valid'], 13)
            self.assertEqual(len(read(root / 'stats/availability.json')['missing']), 1)


if __name__ == '__main__':
    unittest.main()
