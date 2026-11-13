"""Offline safety tests; not evidence of live Keycloak behavior or native grants."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
import yaml

ROOT = Path(__file__).resolve().parents[2] / 'configuration/authorization'

class PortalRoleMapping(unittest.TestCase):
    def run_play(self, extra, check=False):
        with tempfile.TemporaryDirectory() as d:
            inventory = Path(d) / 'hosts'
            inventory.write_text('[bootstrap_clusters]\nlocal ansible_connection=local\n')
            env = {**os.environ, 'ANSIBLE_LOCAL_TEMP': d + '/tmp', 'ANSIBLE_NOCOLOR': '1'}
            command = ['ansible-playbook', '-i', str(inventory), str(ROOT / 'portal-role-mapping.yaml'), '-e', json.dumps(extra)]
            if check:
                command.append('--check')
            return subprocess.run(command, env=env, text=True, capture_output=True, timeout=30)

    def test_defaults_and_check_mode_never_authenticate(self):
        for extra, check in [({}, False), ({}, True), ({'pr_apply': True}, True), ({'pr_inspect': True}, True)]:
            result = self.run_play(extra, check)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn('changed=0', result.stdout)

    def test_unpinned_apply_and_inspection_fail_before_credentials(self):
        for mode in ['pr_apply', 'pr_inspect']:
            result = self.run_play({mode: True})
            self.assertNotEqual(result.returncode, 0)
            self.assertNotIn('TASK [Authenticate', result.stdout)
            self.assertNotIn('TASK [Verify physical', result.stdout)

    def test_reject_role_or_context_substitution(self):
        for extra in [{'pr_roles': ['tenant-portal-admin']}, {'paas_context': {'id': 'other'}}]:
            result = self.run_play(extra)
            self.assertNotEqual(result.returncode, 0)

    def test_write_surface_is_additive_and_gated(self):
        play = yaml.safe_load((ROOT / 'portal-role-mapping.yaml').read_text())[0]
        gated = play['tasks'][2]
        self.assertIn('not ansible_check_mode', gated['when'])
        private = next(t for t in gated['block'] if t.get('no_log'))
        self.assertTrue(private['no_log'])
        requests = [t for t in private['block'] if 'ansible.builtin.uri' in t]
        writes = [t for t in requests if t['ansible.builtin.uri'].get('method', 'GET') != 'GET']
        self.assertEqual(len(writes), 3)  # authentication, create role, map role
        for task in writes[1:]:
            self.assertEqual(task['when'], 'pr_apply | bool')
            self.assertEqual(task['ansible.builtin.uri']['method'], 'POST')
        self.assertEqual(writes[1]['ansible.builtin.uri']['body']['composite'], False)
        self.assertEqual(writes[1]['ansible.builtin.uri']['body']['clientRole'], False)
        self.assertIn('always', private)
        for filename in ['portal-role-group.yaml', 'portal-role-definition.yaml']:
            for task in yaml.safe_load((ROOT / 'tasks' / filename).read_text()):
                if 'ansible.builtin.uri' in task:
                    self.assertEqual(task['ansible.builtin.uri'].get('method', 'GET'), 'GET')

    def test_checks_pin_identity_ownership_and_exact_mappings(self):
        group = (ROOT / 'tasks/portal-role-group.yaml').read_text()
        role = (ROOT / 'tasks/portal-role-definition.yaml').read_text()
        for marker in ['pr_group_current.json.id == pr_group.value', 'pr_group_current.json.path == pr_group.key', 'clientMappings', '/realm/composite', "map(attribute='id')", 'pr_verify']:
            self.assertIn(marker, group)
        for marker in ['containerId == pr_realm_id', 'not pr_definition.json.composite', 'not pr_definition.json.clientRole', 'pr_definition.json.attributes ==']:
            self.assertIn(marker, role)

if __name__ == '__main__':
    unittest.main()
