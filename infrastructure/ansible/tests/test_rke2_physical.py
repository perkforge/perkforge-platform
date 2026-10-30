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
        p = self.run_play(rke2_install_apply=True, physical_operator_inputs_complete=True, rke2_network_prerequisites_reviewed=True, rke2_credential_lifecycle_reviewed=True, rke2_cluster_id='fixture-cluster', rke2_private_output_dir=str(self.work / 'private'))
        self.assertNotEqual(p.returncode, 0)
        self.assertIn('Refuse unset host or SSH user', p.stdout)

    def test_credential_review_blocks_apply_before_any_remote_connection(self):
        p = self.run_play(rke2_install_apply=True, physical_operator_inputs_complete=True,
                          rke2_network_prerequisites_reviewed=True)
        self.assertNotEqual(p.returncode, 0)
        self.assertIn('rke2_credential_lifecycle_reviewed', p.stdout)

    def test_host_preparation_scaffold_never_connects_even_with_nonempty_inventory(self):
        for check in [False, True]:
            p = subprocess.run(['ansible-playbook', '-i', str(self.inventory),
                                str(ROOT / 'playbooks/configure-hosts.yml'),
                                *(['--check'] if check else [])], text=True,
                               capture_output=True, timeout=20,
                               env={**os.environ, 'PATH': str(self.work) + ':' + os.environ['PATH'],
                                    'ANSIBLE_LOCAL_TEMP': str(self.work / 'host-ansible')})
            self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
            self.assertFalse(self.marker.exists())
            self.assertIn('scaffolding only', p.stdout)

    def test_kubeconfig_rewrite_changes_only_the_loopback_address(self):
        plays = yaml.safe_load((ROOT / 'playbooks/install-rke2.yml').read_text())
        server = plays[1]['tasks'][0]['block']
        task = next(x for x in server if x.get('name', '').startswith('Set the selected'))['block'][0]
        replace = task['ansible.builtin.replace']
        import re
        self.assertEqual(re.sub(replace['regexp'], 'https://192.0.2.10:6443',
                               'server: https://127.0.0.1:6443'),
                         'server: https://192.0.2.10:6443')
        self.assertEqual(re.sub(replace['regexp'], 'changed', 'https://127x0x0x1:6443'),
                         'https://127x0x0x1:6443')
        create = next(x for x in server if x.get('name', '').startswith('Precreate private'))
        fetch = next(x for x in server if x.get('name', '').startswith('Fetch only'))
        self.assertLess(server.index(create), server.index(fetch))
        self.assertEqual(create['ansible.builtin.copy']['mode'], '0600')

    def test_invalid_agent_credential_fails_before_connections(self):
        secret = self.work / 'agent-input'
        for content, mode in [('synthetic-short', 0o600), ('synthetic_' * 5, 0o644),
                              ('synthetic_' * 5 + '\n', 0o600)]:
            secret.write_text(content)
            secret.chmod(mode)
            p = self.run_play(rke2_install_apply=True, physical_operator_inputs_complete=True,
                              rke2_network_prerequisites_reviewed=True,
                              rke2_credential_lifecycle_reviewed=True, ansible_user='fixture',
                              rke2_cluster_id='fixture-cluster', rke2_private_output_dir=str(self.work / 'private'),
                              rke2_agent_token_file=str(secret))
            self.assertNotEqual(p.returncode, 0)
            self.assertNotIn(content, p.stdout + p.stderr)

    def test_agent_token_separation_with_synthetic_server_state(self):
        import base64
        plays = yaml.safe_load((ROOT / 'playbooks/install-rke2.yml').read_text())
        task = next(x for x in plays[1]['tasks'][0]['block']
                    if x.get('name', '').startswith('Refuse worker enrollment'))
        agent = 'K10' + 'a' * 64 + '::server:synthetic-agent-only'
        server = 'K10' + 'a' * 64 + '::server:synthetic-server-only'
        for server_value, valid in [(agent, False), (server, True)]:
            def encoded(value):
                return {'content': base64.b64encode(value.encode()).decode()}
            play = self.work / 'separation.yml'
            play.write_text(yaml.safe_dump([{'hosts': 'localhost', 'gather_facts': False,
                'connection': 'local', 'vars': {'rke2_agent_join_token': encoded(agent),
                    'rke2_admin_token_check': encoded(server_value)}, 'tasks': [task]}]))
            result = subprocess.run(['ansible-playbook', '-i', 'localhost,', str(play)],
                capture_output=True, text=True, timeout=20,
                env={**os.environ, 'ANSIBLE_LOCAL_TEMP': str(self.work / 'separation')})
            self.assertEqual(result.returncode == 0, valid, result.stdout + result.stderr)
            self.assertNotIn('synthetic-agent-only', result.stdout + result.stderr)
            self.assertNotIn('synthetic-server-only', result.stdout + result.stderr)
        agent_play = plays[2]
        self.assertIn('rke2_agent_join_token.content', agent_play['vars']['rke2_join_token'])
        self.assertNotIn('rke2_admin_token_check', str(agent_play))
        server_template = (ROOT / 'templates/rke2-server.yaml.j2').read_text()
        self.assertIn('agent-token:', server_template)

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
