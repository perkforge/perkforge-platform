"""Execute gated management Ansible against isolated CLI fixtures, never a cluster."""
import json, os, shutil, subprocess, tempfile, unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
TESTS = ROOT / 'tests'

class RancherManagementTests(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.work = Path(self.tmp.name)
        self.state = self.work / 'state.json'
        self.state.write_text(json.dumps({'auth': [{'metadata': {'name': 'local'}, 'enabled': True}, {'metadata': {'name': 'genericoidc', 'resourceVersion': '1'}, 'enabled': False, 'type': 'genericOIDCConfig', 'serverAdded': 'preserve'}]}))
        for name in ['kubectl-fixture']:
            shutil.copy2(TESTS / 'fixtures/rancher-cli.py', self.work / name)
            (self.work / name).chmod(448)
        self.secret = self.work / 'secret'
        self.secret.write_text('synthetic-fixture-only')
        self.secret.chmod(384)
        self.vars = {'rancher_kubectl': str(self.work / 'kubectl-fixture'), 'rancher_kubeconfig': '/fixture/kubeconfig', 'rancher_context': 'fixture', 'rancher_cluster_uid': 'fixture-cluster', 'rancher_hostname': 'rancher.test.invalid', 'rancher_oidc_issuer': 'https://identity.test.invalid/realms/platform', 'rancher_oidc_secret_file': str(self.secret)}

    def run_play(self, name='configure-rancher-oidc', **overrides):
        check = overrides.pop('check', False)
        values = {**self.vars, **overrides}
        p = subprocess.run(['ansible-playbook', '-i', 'localhost,', str(ROOT / 'configuration/ansible' / f'{name}.yaml'), '-e', json.dumps(values), *(['--check'] if check else [])], text=True, capture_output=True, timeout=30, env={**os.environ, 'ANSIBLE_LOCAL_TEMP': str(self.work / 'ansible'), 'ANSIBLE_NOCOLOR': '1', 'ANSIBLE_REMOTE_TEMP': str(self.work / 'remote'), 'RANCHER_FIXTURE_STATE': str(self.state)})
        self.assertNotIn('synthetic-fixture-only', p.stdout + p.stderr)
        self.assertNotIn('UNREACHABLE!', p.stdout + p.stderr)
        return p

    def data(self):
        return json.loads(self.state.read_text())

    def test_defaults_and_check_mode_never_contact_cluster_or_read_missing_secret(self):
        self.secret.unlink()
        for name, flag in [('configure-rancher-oidc', 'rancher_oidc_apply')]:
            for values in [{}, {flag: True, 'check': True}]:
                p = self.run_play(name, **values)
                self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertEqual(self.data().get('events', []), [])

    def test_provider_and_exact_admin_binding_are_idempotent_and_keep_breakglass(self):
        for _ in range(2):
            p = self.run_play(rancher_oidc_apply=True)
            self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        d = self.data()
        a = next((x for x in d['auth'] if x['metadata']['name'] == 'genericoidc'))
        self.assertEqual(d['providerWrites'], 1)
        self.assertEqual(a['accessMode'], 'required')
        self.assertEqual(a['allowedPrincipalIds'], ['genericoidc_group:///platform/admins'])
        self.assertEqual(a['serverAdded'], 'preserve')
        self.assertTrue(d['auth'][0]['enabled'])
        self.assertEqual(a['rancherUrl'], 'https://rancher.test.invalid/verify-auth')
        self.assertEqual(a['groupsClaim'], 'groups')
        for key in ['issuer', 'authEndpoint', 'tokenEndpoint', 'userInfoEndpoint', 'jwksUrl']:
            self.assertTrue(a[key].startswith('https://'))
        self.assertEqual(d['bindings'][0]['globalRoleName'], 'admin')
        self.assertEqual(d['bindings'][0]['groupPrincipalName'], 'genericoidc_group:///platform/admins')

    def test_tenant_developer_principals_and_broad_admin_mapping_are_refused(self):
        for group in ['genericoidc_group:///tenants/home/admins', 'genericoidc_group:///platform/developers']:
            p = self.run_play(rancher_oidc_apply=True, rancher_management_groups=[group])
            self.assertNotEqual(p.returncode, 0)
        p = self.run_play(rancher_oidc_apply=True, rancher_management_groups=['genericoidc_group:///platform/engineers'], rancher_management_bindings=[{'name': 'engineers', 'groupPrincipalName': 'genericoidc_group:///platform/engineers', 'globalRoleName': 'admin'}])
        self.assertNotEqual(p.returncode, 0)
        self.assertNotIn('providerWrites', self.data())

    def test_exposed_credential_and_wrong_cluster_never_write(self):
        self.secret.chmod(420)
        p = self.run_play(rancher_oidc_apply=True)
        self.assertNotEqual(p.returncode, 0)
        self.secret.chmod(384)
        self.secret.write_text('  \n')
        p = self.run_play(rancher_oidc_apply=True)
        self.assertNotEqual(p.returncode, 0)
        self.secret.write_text('synthetic-fixture-only')
        p = self.run_play(rancher_oidc_apply=True, rancher_cluster_uid='another-cluster')
        self.assertNotEqual(p.returncode, 0)
        self.assertNotIn('providerWrites', self.data())

    def test_competing_provider_or_disabled_local_auth_or_unowned_settings_refused(self):
        initial = self.data()
        variants = []
        d = json.loads(json.dumps(initial))
        d['auth'].append({'metadata': {'name': 'github'}, 'enabled': True})
        variants.append(d)
        d = json.loads(json.dumps(initial))
        d['auth'][0]['enabled'] = False
        variants.append(d)
        d = json.loads(json.dumps(initial))
        d['auth'][1]['clientId'] = 'foreign'
        variants.append(d)
        for d in variants:
            self.state.write_text(json.dumps(d))
            p = self.run_play(rancher_oidc_apply=True)
            self.assertNotEqual(p.returncode, 0)
            self.assertNotIn('providerWrites', self.data())

    def test_conflicting_binding_is_refused_before_provider_write(self):
        d = self.data()
        d['bindings'] = [{'metadata': {'name': 'platform-admins'}, 'groupPrincipalName': 'genericoidc_group:///foreign', 'globalRoleName': 'admin'}]
        self.state.write_text(json.dumps(d))
        p = self.run_play(rancher_oidc_apply=True)
        self.assertNotEqual(p.returncode, 0)
        self.assertNotIn('providerWrites', self.data())
if __name__ == '__main__':
    unittest.main()
