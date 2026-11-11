"""Offline safety contract for the physical-lab staging playbook."""
import pathlib
import unittest
import yaml

PATH = pathlib.Path(__file__).parents[1] / 'playbooks/prepare-backup-target.yml'

class BackupTargetTests(unittest.TestCase):
    def setUp(self):
        self.text = PATH.read_text()
        self.play = yaml.safe_load(self.text)[0]
        self.tasks = self.play['tasks'][0]['block']

    def test_default_and_check_modes_skip_connections(self):
        self.assertFalse(self.play['gather_facts'])
        self.assertFalse(self.play['vars']['backup_prepare_apply'])
        self.assertFalse(self.play['vars']['backup_prepare_reviewed'])
        condition = self.play['tasks'][0]['when']
        for required in ('backup_prepare_apply', 'backup_prepare_reviewed', 'not ansible_check_mode'):
            self.assertIn(required, condition)

    def test_never_enables_or_starts_services(self):
        for task in self.tasks:
            if 'ansible.builtin.systemd_service' in task:
                self.assertEqual(task['ansible.builtin.systemd_service'], {'daemon_reload': True})
            command = task.get('ansible.builtin.command', '')
            self.assertNotIn('systemctl start', command)
            self.assertNotIn('systemctl enable', command)
            self.assertNotIn('exportfs', command)

    def test_guard_precedes_export_and_checks_uuid(self):
        guard = next(t['ansible.builtin.copy']['content'] for t in self.tasks
                     if t.get('ansible.builtin.copy', {}).get('dest', '').endswith('nfs-server.service.d/90-perkforge-backup.conf'))
        self.assertLess(guard.index('ExecStartPre=/usr/bin/findmnt'), guard.index('ExecStartPre=/usr/sbin/exportfs'))
        self.assertIn('--source UUID={{ backup_uuid }}', guard)
        self.assertIn('BindsTo=', guard)
        self.assertIn('mountpoint={{ backup_mount }}', self.text)
        self.assertIn('x-systemd.device-bound', self.text)

    def test_protocol_restrictions_and_no_secret_storage(self):
        for restriction in ('vers3=n', 'vers4=y', 'udp=n', 'rdma=n', '--no-tcp --no-udp'):
            self.assertIn(restriction, self.text)
        self.assertIn("lookup('env', 'PF_APPROVED_BECOME_PASSWORD')", self.text)
        self.assertNotIn('SUDO_PASSWORD', self.text)
        self.assertNotIn('192.168.', self.text)

if __name__ == '__main__':
    unittest.main()
