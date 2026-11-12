"""Offline safety contract for the physical-lab staging playbook."""
import pathlib
import unittest
import yaml
import re
from jinja2 import Environment, StrictUndefined

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

    def test_pod_exception_is_default_off_and_requires_review(self):
        self.assertEqual(self.play['vars']['backup_local_pod_cidr'], '')
        self.assertFalse(self.play['vars']['backup_local_pod_cidr_reviewed'])
        guard = next(t['ansible.builtin.assert']['that'] for t in self.tasks
                     if t['name'].startswith('Require separate review'))
        env = Environment(undefined=StrictUndefined)
        env.filters['bool'] = bool
        env.tests['match'] = lambda value, pattern: re.match(pattern, value) is not None
        for cidr, reviewed, accepted in [('', False, True), ('10.20.30.0/24', True, True),
                                        ('10.20.30.0/24', False, False),
                                        ('10.20.0.0/16', True, False), ('*', True, False),
                                        ('999.20.30.0/24', True, False),
                                        ('10.20.30.1/24', True, False),
                                        ('10.20.30.0/24 10.0.0.0/8', True, False)]:
            with self.subTest(cidr=cidr, reviewed=reviewed):
                actual = all(env.compile_expression(x)(backup_local_pod_cidr=cidr,
                             backup_local_pod_cidr_reviewed=reviewed) for x in guard)
                self.assertEqual(actual, accepted)

    def test_export_render_preserves_nodes_and_adds_only_selected_subnet(self):
        template = next(t['ansible.builtin.copy']['content'] for t in self.tasks
                        if t.get('ansible.builtin.copy', {}).get('dest', '').endswith('perkforge-backup.exports'))
        nodes = ['198.51.100.1', '198.51.100.2', '198.51.100.3']
        for subnet in ('', '10.20.30.0/24'):
            rendered = Environment(undefined=StrictUndefined).from_string(template).render(
                backup_mount='/srv/perkforge-backup', backup_clients=nodes,
                backup_local_pod_cidr=subnet)
            entries = rendered.split()[1:]
            self.assertEqual([entry.split('(')[0] for entry in entries],
                             nodes + ([subnet] if subnet else []))
            self.assertTrue(all(entry.endswith('(rw,sync,no_subtree_check,no_root_squash,mountpoint=/srv/perkforge-backup)') for entry in entries))

    def test_protocol_restrictions_and_no_secret_storage(self):
        for restriction in ('vers3=n', 'vers4=y', 'udp=n', 'rdma=n', '--no-tcp --no-udp'):
            self.assertIn(restriction, self.text)
        self.assertIn("lookup('env', 'PF_APPROVED_BECOME_PASSWORD')", self.text)
        self.assertNotIn('SUDO_PASSWORD', self.text)
        self.assertNotIn('192.168.', self.text)

if __name__ == '__main__':
    unittest.main()
