from pathlib import Path
import sys
import unittest
import tempfile
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import MEASUREMENT_POLICY
from worker import mutation_properties, resource_counters


class MutationBudgetTests(unittest.TestCase):
    def test_worker_uses_frozen_allowances_and_preserves_total_cap(self):
        policy = dict(MEASUREMENT_POLICY, child_budget=dict(MEASUREMENT_POLICY['child_budget'], minimum_seconds=181))
        props = mutation_properties(dict(measurement_policy=policy), Path('/metrics'))
        self.assertEqual(props['mutantProcessTimeoutPolicy'], 'suite-v1')
        self.assertEqual(props['mutantProcessTimeoutMinMs'], '181000')
        self.assertEqual(props['mutationTimeoutMs'], '3600000')
        self.assertNotIn('mutantProcessTimeoutMs', props)

    def test_old_policy_remains_fixed_and_unknown_policy_is_rejected(self):
        self.assertEqual(mutation_properties({}, Path('/metrics'))['mutantProcessTimeoutMs'], '180000')
        policy = dict(MEASUREMENT_POLICY, child_budget=dict(MEASUREMENT_POLICY['child_budget'], policy='unknown'))
        with self.assertRaises(ValueError):
            mutation_properties(dict(measurement_policy=policy), Path('/metrics'))

    def test_docker_cgroup_v1_retains_oom_peak_and_cpu_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'memory').mkdir(); (root / 'cpu').mkdir()
            (root / 'memory/memory.oom_control').write_text('oom_kill 1\n')
            (root / 'memory/memory.max_usage_in_bytes').write_text('4294967296\n')
            (root / 'cpu/cpu.stat').write_text('nr_throttled 2\n')
            counters = resource_counters(root)
            self.assertEqual(counters['memory-oom-control.txt'], 'oom_kill 1\n')
            self.assertEqual(counters['memory.peak'], '4294967296\n')
            self.assertIn('cpu.stat', counters)

    def test_cgroup_v2_keeps_existing_evidence_and_missing_counters_are_optional(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.assertEqual(resource_counters(root), {})
            (root / 'memory.events').write_text('oom_kill 0\n')
            (root / 'memory.peak').write_text('123\n')
            self.assertEqual(resource_counters(root), {'memory-events.txt': 'oom_kill 0\n', 'memory.peak': '123\n'})
