"""Offline gates/templates and port contracts; never SSH or run an installer."""
import json, os, subprocess, tempfile, unittest
from pathlib import Path
import yaml
ROOT = Path(__file__).resolve().parents[1]

class PhysicalRKE2Tests(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.work = Path(self.tmp.name)
        self.inventory = self.work / 'hosts.yaml'
        self.inventory.write_text(yaml.safe_dump({'all': {'vars': {'ansible_user': 'UNCONFIGURED'}, 'children': {'rke2_servers': {'hosts': {'fixture-control': {'ansible_host': '192.0.2.10'}}}, 'rke2_agents': {'hosts': {'fixture-worker': {'ansible_host': '192.0.2.11'}}}}}}))
        self.marker = self.work / 'connection-attempt'
        for tool in ['ssh', 'scp', 'sftp', 'kubectl', 'curl']:
            p = self.work / tool
            p.write_text('#!/bin/sh\ntouch "' + str(self.marker) + '"\nexit 99\n')
            p.chmod(448)

    def run_play(self, check=False, **values):
        p = subprocess.run(['ansible-playbook', '-i', str(self.inventory), str(ROOT / 'playbooks/install-rke2.yml'), '-e', json.dumps(values), *(['--check'] if check else [])], text=True, capture_output=True, timeout=20, env={**os.environ, 'PATH': str(self.work) + ':' + os.environ['PATH'], 'ANSIBLE_LOCAL_TEMP': str(self.work / 'ansible'), 'ANSIBLE_NOCOLOR': '1'})
        self.assertFalse(self.marker.exists(), 'No test may contact a host or run installation tooling')
        return p

    def test_default_and_check_mode_never_select_remote_hosts(self):
        for values in [{}, {'check': True, 'rke2_install_apply': True}]:
            p = self.run_play(**values)
            self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
            self.assertIn('changed=0', p.stdout)

    def test_unset_operator_inputs_fail_before_connections(self):
        p = self.run_play(rke2_install_apply=True)
        self.assertNotEqual(p.returncode, 0)
        self.assertIn('physical_operator_inputs_complete', p.stdout)

    def test_missing_ssh_identity_fails_even_with_deliberate_install_flag(self):
        p = self.run_play(rke2_install_apply=True, physical_operator_inputs_complete=True, rke2_network_prerequisites_reviewed=True, rke2_cluster_id='fixture-cluster', rke2_private_output_dir=str(self.work / 'private'))
        self.assertNotEqual(p.returncode, 0)
        self.assertIn('Refuse unset host or SSH user', p.stdout)

    def test_recovered_ordering_and_secret_handling_contracts(self):
        plays = yaml.safe_load((ROOT / 'playbooks/install-rke2.yml').read_text())
        self.assertEqual([p['hosts'] for p in plays], ['localhost', 'rke2_approved_servers', 'rke2_approved_agents', 'localhost'])
        self.assertTrue(all((p['gather_facts'] is False for p in plays)))
        self.assertEqual(plays[2]['serial'], 1)
        server = plays[1]['tasks'][0]['block']
        token = next((x for x in server if 'ansible.builtin.slurp' in x))
        self.assertTrue(token['no_log'])
        fetch = next((x for x in server if x.get('name', '').startswith('Fetch only')))
        self.assertTrue(fetch['no_log'])
        node = yaml.safe_load((ROOT / 'tasks/rke2-node.yml').read_text())
        names = [x.get('name', '') for x in node]
        self.assertLess(names.index('Never adopt an unowned existing RKE2 installation'), names.index('Install only the RKE2 installer prerequisites'))
        self.assertLess(names.index('Existing managed configuration changes require separate maintenance review'), names.index('Install only the RKE2 installer prerequisites'))
        installer = next((x for x in node if 'ansible.builtin.get_url' in x))
        self.assertIn('checksum', installer['ansible.builtin.get_url'])
        service = next((x for x in node if 'ansible.builtin.service' in x))
        self.assertEqual(service['ansible.builtin.service']['state'], 'started')
        for task in node:
            if 'ansible.builtin.template' in task:
                self.assertTrue(task['no_log'])

    def test_native_templates_preserve_join_token_as_one_yaml_scalar(self):
        template = ROOT / 'templates/rke2-agent.yaml.j2'
        fixture = 'synthetic:"token\nonly'
        values = {'rke2_server_ip': '192.0.2.10', 'rke2_join_token': fixture, 'rke2_node_ip': '192.0.2.11'}
        arg = json.dumps({'msg': "{{ lookup('ansible.builtin.template', '" + str(template) + "') }}"})
        p = subprocess.run(['ansible', 'localhost', '-i', 'localhost,', '-m', 'ansible.builtin.debug', '-a', arg, '-e', json.dumps(values)], text=True, capture_output=True, timeout=15, env={**os.environ, 'ANSIBLE_LOCAL_TEMP': str(self.work / 'render')})
        self.assertEqual(p.returncode, 0, p.stderr)
        response, _ = json.JSONDecoder().raw_decode(p.stdout[p.stdout.index('{'):])
        d = yaml.safe_load(response['msg'])
        self.assertEqual(d['token'], fixture)
        self.assertEqual(d['server'], 'https://192.0.2.10:9345')
        self.assertTrue(d['selinux'])
if __name__ == '__main__':
    unittest.main()
