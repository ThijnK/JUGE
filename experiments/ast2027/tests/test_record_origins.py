from pathlib import Path
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import campaign
from common import atomic, digest, identity, matrix, matching_manifest, read, valid_record


class RecordOriginTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.rows = [r for r in matrix() if r['experiment'] == 'B'][:4]
        self.retained = next(r for r in self.rows if r['tool'] == 'MAZE')
        self.replaced = next(r for r in self.rows if r['tool'] == 'T3')
        parent = dict(runs=self.rows)
        parent['id'] = identity(parent)
        self.parent = parent
        atomic(self.root / 'prior.json', parent)
        spec = dict(runs=self.rows, campaign=dict(generation_jobs=2, measurement_jobs=3),
            record_origins=[dict(path='prior.json', sha256=digest(self.root / 'prior.json'),
                manifest_id=parent['id'], retained_case_ids=[self.retained['id']])])
        spec['id'] = identity(spec)
        self.spec = spec
        atomic(self.root / 'manifest.json', spec)

    def test_only_explicit_retained_coordinates_accept_previous_identity(self):
        self.assertTrue(matching_manifest(self.root, self.retained, self.parent['id'], self.spec['id']))
        self.assertFalse(matching_manifest(self.root, self.replaced, self.parent['id'], self.spec['id']))
        self.assertFalse(matching_manifest(self.root, dict(self.retained, seed=0), self.parent['id'], self.spec['id']))
        self.assertFalse(matching_manifest(self.root, self.retained, 'unrelated', self.spec['id']))

    def test_prior_manifest_tampering_is_rejected(self):
        self.assertTrue(matching_manifest(self.root, self.retained, self.parent['id'], self.spec['id']))
        (self.root / 'prior.json').write_text('{}')
        self.assertFalse(matching_manifest(self.root, self.retained, self.parent['id'], self.spec['id']))

    def test_retained_stages_and_consolidated_observation_are_not_rewritten(self):
        evidence = self.root / 'evidence.txt'
        evidence.write_text('verified suite')
        rec = dict(run=self.retained, manifest_id=self.parent['id'], status='tool_failure',
            phase='generation', reason='confirmed_failure', evidence={'evidence.txt': digest(evidence)})
        campaign.publish(campaign.stage_path(self.root, self.retained, 'generation'), rec)
        with patch.object(campaign, 'execute') as execute:
            campaign.run_stage(self.root, self.spec, [self.retained], 'generation', threading.Event())
            execute.assert_not_called()
        self.assertTrue(campaign.assemble(self.root, self.spec, [self.retained]))
        file = self.root / 'runs' / (self.retained['id'] + '.json')
        before = file.read_bytes()
        self.assertTrue(valid_record(self.root, self.retained, self.spec['id']))
        self.assertTrue(campaign.assemble(self.root, self.spec, [self.retained]))
        self.assertEqual(file.read_bytes(), before)
