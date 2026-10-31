"""Offline assertions only: never invoke apt, systemd, sudo or sockets."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
import yaml

PLAY = Path(__file__).resolve().parents[1] / 'transport/install-nginx.yml'

class NginxInstallTests(unittest.TestCase):
    def test_resolver_guard_accepts_only_approved_transaction(self):
        play = yaml.safe_load(PLAY.read_text())[0]
        guard = next(t for t in play['tasks'] if t['name'].startswith('Reject upgrades'))
        version = play['vars']['nginx_version']
        lines = [f'Inst nginx ({version} Debian:13/stable [amd64])',
                 f'Inst nginx-common ({version} Debian:13/stable [all])',
                 '0 upgraded, 2 newly installed, 0 to remove and 9 not upgraded.']
        cases = [(lines, True), (lines + ['Inst extra (1 Debian [all])'], False),
                 ([line.replace(version, '9.9') for line in lines], False),
                 ([line.replace('0 to remove', '1 to remove') for line in lines], False)]
        with tempfile.TemporaryDirectory() as tmp:
            for index, (output, accepted) in enumerate(cases):
                fixture = [{'hosts': 'localhost', 'connection': 'local', 'gather_facts': False,
                            'vars': {'nginx_version': version, 'transaction': {
                                'stdout': '\n'.join(output), 'stdout_lines': output}},
                            'tasks': [guard]}]
                path = Path(tmp) / f'case{index}.yml'
                path.write_text(yaml.safe_dump(fixture))
                result = subprocess.run(['ansible-playbook', '-i', 'localhost,', str(path)],
                    env={**os.environ, 'ANSIBLE_LOCAL_TEMP': tmp}, capture_output=True, text=True)
                self.assertEqual(result.returncode == 0, accepted, result.stdout + result.stderr)

    def test_mutations_are_narrow_and_policy_check_is_always(self):
        play = yaml.safe_load(PLAY.read_text())[0]
        self.assertEqual(play['hosts'], 'localhost')
        self.assertEqual(play['connection'], 'local')
        mask = next(t['ansible.builtin.systemd_service'] for t in play['tasks']
                    if 'ansible.builtin.systemd_service' in t)
        self.assertEqual(mask, {'name': 'nginx.service', 'masked': True})
        block = next(t for t in play['tasks'] if 'block' in t)
        apt = block['block'][0]['ansible.builtin.apt']
        self.assertEqual(apt['policy_rc_d'], 101)
        for flag in ['update_cache', 'install_recommends', 'autoremove', 'auto_install_module_deps']:
            self.assertIs(apt[flag], False)
        self.assertTrue(apt['fail_on_autoremove'])
        self.assertIn('always', block)
