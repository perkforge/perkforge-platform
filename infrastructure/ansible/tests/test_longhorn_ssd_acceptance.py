"""Offline probe cleanup/refusal and owner-playbook gating tests."""
import importlib.util
import ast
import os
from pathlib import Path
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import yaml

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('runtime_probe', ROOT / 'files/verify-longhorn-runtime-io.py')
probe = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(probe)


class ProbeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.fd = os.open(self.root, os.O_RDONLY | os.O_DIRECTORY)
        self.addCleanup(os.close, self.fd)
        self.device = os.fstat(self.fd).st_dev
        (self.root / 'unrelated').write_bytes(b'keep')

    def assert_preserved(self):
        self.assertEqual(sorted(p.name for p in self.root.iterdir()), ['unrelated'])
        self.assertEqual((self.root / 'unrelated').read_bytes(), b'keep')

    def test_bounded_roundtrip_and_cleanup_preserve_other_files(self):
        result = probe.probe(self.fd, self.device)
        self.assertEqual(result, {'verified_bytes': 16 * 1024 * 1024, 'checksum_match': True})
        self.assert_preserved()

    def test_runtime_helper_remains_compatible_with_older_manager_python(self):
        source = (ROOT / 'files/verify-longhorn-runtime-io.py').read_text()
        ast.parse(source, feature_version=(3, 6))

    def test_path_replacement_cannot_redirect_anchored_probe_or_cleanup(self):
        original = self.root
        moved = self.root.with_name(self.root.name + '-moved')
        original.rename(moved)
        original.mkdir()
        (original / 'replacement').write_bytes(b'leave replacement alone')
        try:
            result = probe.probe(self.fd, self.device)
            self.assertTrue(result['checksum_match'])
            self.assertEqual(sorted(p.name for p in moved.iterdir()), ['unrelated'])
            self.assertEqual((original / 'replacement').read_bytes(), b'leave replacement alone')
        finally:
            (original / 'replacement').unlink()
            original.rmdir()
            moved.rename(original)

    def test_wrong_device_refused_before_creation(self):
        with self.assertRaises(ValueError):
            probe.probe(self.fd, self.device + 1)
        self.assert_preserved()

    def test_collision_does_not_reuse_or_remove_existing_directory(self):
        existing = self.root / '.pf-ssd-acceptance-collision'
        existing.mkdir()
        (existing / 'keep').touch()
        with patch.object(probe.secrets, 'token_hex', return_value='collision'), self.assertRaises(FileExistsError):
            probe.probe(self.fd, self.device)
        self.assertTrue((existing / 'keep').exists())

    def test_corrupt_readback_fails_and_cleans_only_owned_entries(self):
        real_open = os.open

        def corrupt(name, flags, *args, **kwargs):
            if name == 'probe.bin' and flags == os.O_RDONLY | os.O_NOFOLLOW:
                fd = real_open(name, os.O_WRONLY | os.O_TRUNC, dir_fd=kwargs['dir_fd'])
                os.write(fd, b'corrupt fixture')
                os.close(fd)
            return real_open(name, flags, *args, **kwargs)

        with patch.object(probe.os, 'open', corrupt), self.assertRaises(ValueError):
            probe.probe(self.fd, self.device)
        self.assert_preserved()

    def test_unreviewed_write_refused_before_host_inspection(self):
        with self.assertRaises(ValueError):
            probe.inspect(SimpleNamespace(apply=True, reviewed=False))


class OwnerGateTests(unittest.TestCase):
    def test_default_check_and_unreviewed_apply_never_connect(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            marker = root / 'connection-attempt'
            ssh = root / 'ssh'
            ssh.write_text('#!/bin/sh\ntouch "' + str(marker) + '"\nexit 99\n')
            ssh.chmod(0o700)
            inventory = root / 'inventory.yml'
            inventory.write_text(yaml.safe_dump({'all': {'children': {'rke2_agents': {'hosts': {
                'worker-1': {'ansible_host': '192.0.2.1', 'ansible_user': 'fixture',
                             'ansible_ssh_executable': str(ssh)}}}}}}))
            config = root / 'ansible.cfg'
            config.write_text('[defaults]\n')
            env = dict(os.environ, ANSIBLE_CONFIG=str(config), ANSIBLE_LOCAL_TEMP=d, ANSIBLE_NOCOLOR='1')
            for extra, success in (([], True), (['--check', '-e', 'ssd_acceptance_apply=true'], True),
                                   (['-e', 'ssd_acceptance_apply=true'], False)):
                result = subprocess.run(['ansible-playbook', '-i', str(inventory),
                                         str(ROOT / 'tests/longhorn-unused-ssd.yml'), *extra],
                                        text=True, capture_output=True, env=env)
                self.assertEqual(result.returncode == 0, success, result.stdout + result.stderr)
                self.assertFalse(marker.exists())

    def test_no_force_no_lazy_unmount_and_guard_precedes_remount(self):
        play = yaml.safe_load((ROOT / 'tests/longhorn-unused-ssd.yml').read_text())[0]
        self.assertEqual(play['serial'], 1)
        tasks = play['tasks'][0]['block']
        commands = [t['ansible.builtin.command']['argv'] for t in tasks if 'ansible.builtin.command' in t]
        self.assertEqual(commands, [['hostname'], ['umount', '{{ ssd_spec.path }}'], ['mount', '{{ ssd_spec.path }}']])
        names = [t.get('name', '') for t in tasks]
        self.assertLess(names.index('Verify the uncovered recorded inode and prove root writes are refused'),
                        names.index('Remount the exact verified fstab entry'))


if __name__ == '__main__':
    unittest.main()
