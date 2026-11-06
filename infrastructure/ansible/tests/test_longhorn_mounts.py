"""Offline refusal/gating checks; no devices, sudo or worker connections."""
import importlib.util
import errno
import os
import stat
from pathlib import Path
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import yaml

ROOT = Path(__file__).resolve().parents[1]
MODULE = importlib.util.spec_from_file_location('mount_verify', ROOT / 'files/verify-longhorn-mount.py')
verify = importlib.util.module_from_spec(MODULE)
MODULE.loader.exec_module(verify)


class FstabTests(unittest.TestCase):
    def setUp(self):
        self.spec = SimpleNamespace(uuid='11111111-2222-3333-4444-555555555555',
                                    label='test-t7', path='/mnt/test-t7')
        self.line = f'UUID={self.spec.uuid} {self.spec.path} xfs {verify.OPTIONS} 0 0'

    def test_unrelated_entries_preserved(self):
        verify.validate_fstab('/dev/mapper/root / xfs defaults 0 0\n# comment', self.spec, False)

    def test_exact_owned_entry_accepted(self):
        block = f'# BEGIN PerkForge Longhorn {self.spec.path}\n{self.line}\n# END PerkForge Longhorn {self.spec.path}'
        verify.validate_fstab(block, self.spec, True)

    def test_owned_entry_moved_outside_block_refused(self):
        with self.assertRaises(ValueError):
            verify.validate_fstab(self.line, self.spec, True)

    def test_orphan_management_marker_refused(self):
        with self.assertRaises(ValueError):
            verify.validate_fstab(f'# BEGIN PerkForge Longhorn {self.spec.path}', self.spec, True)

    def test_unmanaged_exact_entry_refused(self):
        with self.assertRaises(ValueError):
            verify.validate_fstab(self.line, self.spec, False)

    def test_duplicate_and_foreign_entries_refused(self):
        for text in (self.line + '\n' + self.line,
                     '/dev/other /mnt/test-t7 xfs defaults 0 0',
                     f'UUID={self.spec.uuid} /mnt/elsewhere xfs defaults 0 0',
                     'LABEL=test-t7 /mnt/elsewhere xfs defaults 0 0',
                     self.line.replace('nofail,', '')):
            with self.subTest(text=text), self.assertRaises(ValueError):
                verify.validate_fstab(text, self.spec, True)

    def test_device_alias_refused(self):
        with tempfile.TemporaryDirectory() as d:
            # /dev/null is a harmless existing source alias for this pure parser test.
            with self.assertRaises(ValueError):
                verify.validate_fstab('/dev/null /mnt/elsewhere xfs defaults 0 0',
                                      self.spec, True, Path('/dev/null').resolve())


class MountTests(unittest.TestCase):
    def test_expected_mount_and_absence(self):
        row = {'target': '/mnt/test', 'fstype': 'xfs', 'maj:min': '8:1',
               'options': 'rw,noatime,nosuid,nodev,attr2'}
        self.assertTrue(verify.validate_mounts([row], '/mnt/test', '8:1'))
        self.assertFalse(verify.validate_mounts([], '/mnt/test', '8:1'))

    def test_wrong_device_readonly_nested_or_elsewhere_refused(self):
        row = {'target': '/mnt/test', 'fstype': 'xfs', 'maj:min': '8:1',
               'options': 'rw,noatime,nosuid,nodev'}
        for changes in ({'maj:min': '8:2'}, {'fstype': 'ext4'},
                        {'options': 'ro,noatime,nosuid,nodev'}, {'options': 'rw'},
                        {'target': '/mnt/test/nested'}, {'target': '/elsewhere'}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                verify.validate_mounts([dict(row, **changes)], '/mnt/test', '8:1')


class GuardTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name, 'guard')
        self.path.mkdir(mode=0o700)
        self.root_device = self.path.stat().st_dev
        actual_lstat = Path.lstat

        def root_lstat(path):
            values = list(actual_lstat(path))
            values[4] = 0  # Fixture owns its directory as simulated root.
            return os.stat_result(values)

        self.owner = patch.object(Path, 'lstat', root_lstat)
        self.owner.start()
        self.addCleanup(self.owner.stop)

    def inspect(self, path=None, marker=None, prove=False):
        return verify.inspect_guard(path or self.path, '11111111-2222-3333-4444-555555555555',
                                    marker, prove, self.root_device)

    @staticmethod
    def immutable(fd, request, flags, mutate):
        flags[0] = 0x10

    def test_unset_guard_reports_false(self):
        with patch.object(verify.fcntl, 'ioctl', return_value=0):
            self.assertFalse(self.inspect()['immutable'])

    def test_guard_reports_durable_identity_without_device_number(self):
        with patch.object(verify.fcntl, 'ioctl', self.immutable):
            guard = self.inspect()
        self.assertEqual(guard['root_filesystem_uuid'], '11111111-2222-3333-4444-555555555555')
        self.assertEqual(guard['inode'], self.path.stat().st_ino)
        self.assertNotIn('device', guard)

    def test_nonempty_and_symlink_refused(self):
        (self.path / 'existing').touch()
        with self.assertRaises(ValueError):
            self.inspect()
        alias = self.path.parent / 'alias'
        alias.symlink_to(self.path)
        with self.assertRaises(ValueError):
            self.inspect(alias)

    def test_old_inode_marker_refused(self):
        with patch.object(verify.fcntl, 'ioctl', self.immutable), self.assertRaises(ValueError):
            self.inspect(marker={'root_filesystem_uuid': '11111111-2222-3333-4444-555555555555',
                                 'root_inode': -1})

    def test_missing_recorded_directory_refused(self):
        self.path.rmdir()
        with self.assertRaises(ValueError):
            self.inspect(marker={'root_filesystem_uuid': 'fixture', 'root_inode': 1})

    def test_root_identity_survives_device_number_change(self):
        root_uuid = '11111111-2222-3333-4444-555555555555'
        marker = {'root_filesystem_uuid': root_uuid, 'root_inode': 123}
        # Both hypothetical boots have the same filesystem/inode, different runtime dev_t.
        for runtime_device in (os.makedev(253, 0), os.makedev(253, 7)):
            with self.subTest(runtime_device=runtime_device), \
                    patch.object(verify.os, 'stat', return_value=SimpleNamespace(st_dev=runtime_device)), \
                    patch.object(Path, 'resolve', return_value=Path('/dev/mock-root')), \
                    patch.object(Path, 'stat', return_value=SimpleNamespace(st_mode=stat.S_IFBLK, st_rdev=runtime_device)), \
                    patch.object(verify, 'command', return_value=f'TYPE=xfs\nUUID={root_uuid}'):
                identity = verify.root_filesystem_identity()
                self.assertEqual(identity, root_uuid)
                verify.validate_guard_identity(marker, identity, 123, True)
        self.assertNotIn('root_device', marker)

    def test_replaced_root_and_cleared_guard_refused(self):
        marker = {'root_filesystem_uuid': 'original-root', 'root_inode': 123}
        for root_uuid, inode, immutable in (('replaced-root', 123, True),
                                            ('original-root', 124, True),
                                            ('original-root', 123, False)):
            with self.subTest(root_uuid=root_uuid, inode=inode, immutable=immutable), self.assertRaises(ValueError):
                verify.validate_guard_identity(marker, root_uuid, inode, immutable)

    def test_unexpected_write_success_cleans_only_own_probe_and_fails(self):
        with patch.object(verify.fcntl, 'ioctl', self.immutable), self.assertRaises(ValueError):
            self.inspect(prove=True)
        self.assertEqual(list(self.path.iterdir()), [])

    def test_permission_denied_is_required_for_proof(self):
        actual_open = os.open

        def denied(path, flags, *args, **kwargs):
            if kwargs.get('dir_fd') is not None:
                raise PermissionError(errno.EPERM, 'fixture')
            return actual_open(path, flags, *args, **kwargs)

        with patch.object(verify.fcntl, 'ioctl', self.immutable), patch.object(verify.os, 'open', denied):
            self.assertTrue(self.inspect(prove=True)['immutable'])


class PlaybookTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        config = Path(self.temp.name, 'ansible.cfg')
        config.write_text('[defaults]\n')
        self.env = dict(os.environ, ANSIBLE_LOCAL_TEMP=self.temp.name,
                        ANSIBLE_CONFIG=str(config), ANSIBLE_NOCOLOR='1')

    def test_default_and_check_never_connect(self):
        play = ROOT / 'playbooks/mount-longhorn-disks.yml'
        with tempfile.TemporaryDirectory() as d:
            marker = Path(d, 'connection-attempt')
            ssh = Path(d, 'ssh')
            ssh.write_text('#!/bin/sh\ntouch "' + str(marker) + '"\nexit 99\n')
            ssh.chmod(0o700)
            inventory = Path(d, 'hosts.yml')
            inventory.write_text(yaml.safe_dump({'all': {'children': {
                'rke2_agents': {'hosts': {'worker-1': {
                    'ansible_host': '192.0.2.1', 'ansible_user': 'test',
                    'ansible_ssh_executable': str(ssh)}}}, 'rke2_servers': {'hosts': {}}}}}))
            for args in ([], ['--check', '-e', 'longhorn_mount_apply=true']):
                result = subprocess.run(['ansible-playbook', '-i', str(inventory), str(play), *args],
                                        text=True, capture_output=True, env=self.env)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertFalse(marker.exists())

    def test_apply_without_review_fails_before_connection(self):
        result = subprocess.run(['ansible-playbook', '-i', str(ROOT / 'inventory/hosts.yml'),
                                 str(ROOT / 'playbooks/mount-longhorn-disks.yml'),
                                 '-e', 'longhorn_mount_apply=true'], text=True, capture_output=True, env=self.env)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('longhorn_mount_reviewed', result.stdout)

    def test_reviewed_controller_accepts_only_complete_worker_identity(self):
        controller = yaml.safe_load((ROOT / 'playbooks/mount-longhorn-disks.yml').read_text())[0]
        with tempfile.TemporaryDirectory() as d:
            play = Path(d, 'controller.yml')
            play.write_text(yaml.safe_dump([controller]))
            inventory = Path(d, 'hosts.yml')
            inventory.write_text(yaml.safe_dump({'all': {'children': {
                'rke2_agents': {'hosts': {'worker-1': {'ansible_host': '192.0.2.1', 'ansible_user': 'test'}}},
                'rke2_servers': {'hosts': {'control-1': {}}}}}}))
            plan = {'node': 'worker-1', 'uuid': '11111111-2222-3333-4444-555555555555',
                    'usb_serial': 'FIXTURE123', 'label': 'test-t7', 'raw_size_bytes': 500000000000,
                    'path': '/mnt/test-t7'}
            for changes, success in (({}, True), ({'node': 'control-1'}, False),
                                     ({'uuid': 'UNCONFIGURED'}, False),
                                     ({'path': '/'}, False), ({'raw_size_bytes': 0}, False)):
                variables = {'longhorn_mount_apply': True, 'longhorn_mount_reviewed': True,
                             'longhorn_mount_guard_reviewed': True,
                             'longhorn_mount_plan': [dict(plan, **changes)]}
                import json
                result = subprocess.run(['ansible-playbook', '-i', str(inventory), str(play),
                                         '-e', json.dumps(variables)], text=True,
                                        capture_output=True, env=self.env)
                self.assertEqual(result.returncode == 0, success, result.stdout + result.stderr)

    def test_guard_precedes_fstab_and_mount_and_never_touches_mounted_root(self):
        tasks = yaml.safe_load((ROOT / 'tasks/longhorn-mount.yml').read_text())
        names = [t.get('name', '') for t in tasks]
        proof = names.index('Prove root writes to the immutable underlying directory are denied')
        persist = names.index('Persist only the reviewed UUID entry, preserving all other fstab entries')
        mount = names.index('Mount only the reviewed path, never mount all filesystems')
        self.assertLess(proof, persist)
        self.assertLess(persist, mount)
        for t in tasks:
            if 'attributes' in t.get('ansible.builtin.file', {}):
                self.assertIn('not longhorn_mount_state.mounted', t['when'])


if __name__ == '__main__':
    unittest.main()
