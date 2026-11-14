"""Default metadata access is inert and source routes remain bounded."""
from pathlib import Path
import subprocess
import unittest
import yaml
SOURCE=Path(__file__).resolve().parents[3]/'big-bang-bootstrap/configuration/authorization/sso/grafana/orgs'
class Metadata(unittest.TestCase):
    def test_default_and_check_no_access(self):
        for args in [[],['--check','-e','grafana_org_inspect_run=true']]:
            run=subprocess.run(['ansible-playbook','-i','localhost,',str(SOURCE/'inspect.yaml')]+args,capture_output=True,text=True)
            self.assertEqual(run.returncode,0,run.stdout+run.stderr)
            self.assertIn('changed=0',run.stdout)
    def test_exact_get_routes_and_no_humans(self):
        play=yaml.safe_load((SOURCE/'inspect.yaml').read_text())[0]
        uris=[t['ansible.builtin.uri'] for t in play['tasks'][0]['block'] if 'ansible.builtin.uri' in t]
        self.assertEqual(len(uris),4)
        self.assertTrue(all(t.get('method','GET')=='GET' for t in uris))
        self.assertFalse(any('/users' in t['url'] or '/members' in t['url'] for t in uris))
        self.assertTrue(play['module_defaults']['ansible.builtin.uri']['validate_certs'])
        self.assertEqual(play['module_defaults']['ansible.builtin.uri']['follow_redirects'],'none')
    def test_unconnected_writers_are_exact_additive_only(self):
        files=['ensure-org.yaml','ensure-entitlement.yaml','ensure-role-binding.yaml']
        for name in files:
            tasks=yaml.safe_load((SOURCE/name).read_text())
            for task in tasks:
                if 'ansible.builtin.uri' not in task: continue
                uri=task['ansible.builtin.uri']
                self.assertIn(uri.get('method','GET'),['GET','POST'])
                self.assertTrue(task.get('no_log'), name)
                self.assertNotIn('/users',uri['url'])
        source=(SOURCE/'inspect.yaml').read_text()
        self.assertNotIn('include_tasks',source)
        binding=(SOURCE/'ensure-role-binding.yaml').read_text()
        self.assertIn('entitlement_binding_before.json',binding)
        self.assertIn('unique | sort',binding)
