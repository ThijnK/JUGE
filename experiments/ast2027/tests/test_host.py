from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import bench
import campaign
import host
from common import atomic,digest


class HostTests(unittest.TestCase):
    def test_capacity_reserves_memory_and_does_not_sum_separate_phases(self):
        config=dict(generation_jobs=2,measurement_jobs=1,cpus=2,memory_gb=4)
        host.check_capacity(dict(NCPU=4,MemTotal=9*1024**3),config)
        with self.assertRaises(ValueError):
            host.check_capacity(dict(NCPU=4,MemTotal=8*1024**3),config)
        with self.assertRaises(ValueError):
            host.check_capacity(dict(NCPU=3,MemTotal=9*1024**3),config)

    def test_workers_and_preflight_match_nonroot_host_ownership(self):
        config=dict(generation_jobs=1,measurement_jobs=1,cpus=2,memory_gb=4)
        with tempfile.TemporaryDirectory() as tmp, patch.object(host.os,'getuid',return_value=1000), patch.object(host.os,'getgid',return_value=1001):
            root=Path(tmp)
            atomic(root/'manifest.json',dict(campaign=config))
            self.assertIn('--user=1000:1001',bench.docker(root,'frozen'))
            active=dict(container='case',phase='generation',id='row',attempt='attempt')
            self.assertIn('--user=1000:1001',campaign.command(root,dict(campaign=config,image='frozen'),active))

    def test_wsl_rejects_windows_filesystem_before_docker(self):
        with patch.object(host.platform,'system',return_value='Linux'), patch.object(host.platform,'release',return_value='microsoft-standard-WSL2'), patch.object(host.os,'access',return_value=True), patch.object(host,'output') as output:
            with self.assertRaisesRegex(ValueError,'Linux filesystem'):
                host.inspect_host(Path('/mnt/c/projects/results'),{})
            output.assert_not_called()

    def test_recorded_machine_metadata_is_verified(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            (root/'env').mkdir();(root/'suite').mkdir()
            atomic(root/'host-machine.json',dict(cpu='original'))
            spec=dict(environment={},suite={},host_record=dict(path='host-machine.json',sha256=digest(root/'host-machine.json')))
            bench.verify_environment(root,spec)
            atomic(root/'host-machine.json',dict(cpu='edited'))
            with self.assertRaisesRegex(SystemExit,'machine record changed'):
                bench.verify_environment(root,spec)

    def test_validation_copies_machine_record_but_never_repairs_corrupt_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            parent=Path(tmp)
            (parent/'env').mkdir();(parent/'suite').mkdir()
            atomic(parent/'host-machine.json',dict(cpu='original'))
            spec=dict(id='m',environment={},suite={},host_record=dict(path='host-machine.json',sha256=digest(parent/'host-machine.json')))
            root=parent/'preflight-data'
            bench.prepare_validation(parent,root,spec)
            self.assertEqual(digest(root/'host-machine.json'),spec['host_record']['sha256'])
            atomic(root/'host-machine.json',dict(cpu='corrupt'))
            with self.assertRaisesRegex(SystemExit,'machine record changed'):
                bench.prepare_validation(parent,root,spec)
