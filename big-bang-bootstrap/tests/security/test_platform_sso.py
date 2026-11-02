"""Execute the non-network SSO renderer and inspect application boundaries."""
import copy
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
import yaml

ROOT = Path(__file__).resolve().parents[2]
PLAY = ROOT / 'configuration/authorization/sso/prepare.yaml'


@unittest.skipUnless(os.environ.get('RUN_PLATFORM_SSO_TESTS'), 'enable isolated SSO job explicitly')
class PlatformSSO(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='platform-sso-test-')
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.output = self.base / 'review'
        self.env = dict(os.environ, ANSIBLE_LOCAL_TEMP=str(self.base / 'local'),
                        ANSIBLE_REMOTE_TEMP=str(self.base / 'remote'), ANSIBLE_NOCOLOR='1')
        self.vars = {'sso_render': True, 'sso_environment': 'example',
                     'sso_output_directory': str(self.output),
                     'sso_public_ca_file': '/review/public-ca.pem',
                     'sso_keycloak_origin': 'https://identity.example.test',
                     'sso_apps': {app: {'client_id': app+'-example',
                                        'origin': 'https://'+app+'.example.test', 'apply': False}
                                  for app in ('headlamp', 'rancher', 'openbao')}}

    def run_play(self, values=None, check=False):
        inputs = self.base / 'inputs.yaml'
        inputs.write_text(yaml.safe_dump(self.vars if values is None else values))
        return subprocess.run(['ansible-playbook', str(PLAY), '-e', '@'+str(inputs)]
                              + (['--check'] if check else []), env=self.env,
                              capture_output=True, text=True, timeout=60)

    def render(self):
        result = self.run_play()
        self.assertEqual(result.returncode, 0, result.stdout+result.stderr)
        return {name: yaml.safe_load((self.output/(name+'.yaml')).read_text())
                for name in ('clients', 'headlamp', 'rancher', 'openbao')}

    def test_defaults_and_check_do_not_render_or_access_credentials(self):
        for values, check in (({}, False), (self.vars, True)):
            result = self.run_play(values, check)
            self.assertEqual(result.returncode, 0, result.stdout+result.stderr)
            self.assertFalse(self.output.exists())
        source = PLAY.read_text()
        self.assertNotIn('ansible.builtin.uri', source)
        self.assertNotIn('ansible.builtin.command', source)
        self.assertNotIn("lookup('file'", source)

    def test_clients_have_distinct_audiences_and_no_cross_app_group_mapper(self):
        data = self.render()
        for app, item in data['clients']['clients'].items():
            c = item['representation']
            self.assertFalse(c['enabled'])
            for key in ('publicClient','implicitFlowEnabled','directAccessGrantsEnabled',
                        'serviceAccountsEnabled','fullScopeAllowed'):
                self.assertFalse(c[key], key)
            self.assertEqual(c['attributes']['pkce.code.challenge.method'], 'S256')
            self.assertEqual(c['defaultClientScopes'], ['basic','profile','email'])
            self.assertEqual(c['optionalClientScopes'], [])
            self.assertNotIn('secret', c)
            mapper, audience = c['protocolMappers']
            self.assertEqual(mapper['protocolMapper'], 'oidc-usermodel-client-role-mapper')
            self.assertEqual(mapper['config']['usermodel.clientRoleMapping.clientId'], c['clientId'])
            self.assertEqual(audience['config']['included.client.audience'], c['clientId'])
            self.assertEqual(item['groupRoleMappings'], [{'group':'/platform/admins', 'roles':['/platform/admins']}])
            self.assertEqual(item['scopeRoles'], ['/platform/admins'])
            self.assertNotIn('*', c['redirectUris'][0])
            self.assertNotIn('localhost', c['redirectUris'][0])

    def test_headlamp_api_boundary_and_rancher_provider_are_distinct(self):
        data = self.render()
        h, r = data['headlamp'], data['rancher']
        self.assertEqual(h['api_prerequisites']['audience'], h['client_id'])
        self.assertEqual(h['api_prerequisites']['required_azp'], h['client_id'])
        self.assertFalse(h['api_prerequisites']['restart_allowed'])
        self.assertIn('oidc-client-id='+h['client_id'],h['provisioning_fragment']['kube-apiserver-arg+'])
        self.assertNotIn('kube-apiserver-extra-mount+',h['provisioning_fragment'])
        self.assertEqual(h['rbac']['subjects'][0]['name'], 'oidc:/platform/admins')
        self.assertEqual(r['provider_type'], 'genericOIDCConfig')
        self.assertEqual(r['allowed_principals'], ['genericoidc_group:///platform/admins'])
        self.assertTrue(r['local_recovery_required'])
        self.assertFalse(r['provider_migration_allowed'])
        self.assertTrue(r['installed_schema_verification_required'])

    def test_openbao_preserves_platform_tenant_and_machine_boundaries(self):
        bao = self.render()['openbao']
        role = bao['roles']['platform-admin']
        self.assertEqual(role['bound_audiences'], [bao['client_id']])
        self.assertEqual(role['bound_claims'], {'groups':['/platform/admins']})
        self.assertTrue(role['token_no_default_policy'])
        self.assertEqual(bao['default_role'], '')
        self.assertEqual(bao['tenant_roles'], [])
        self.assertFalse(bao['machine_auth_changes_allowed'])
        self.assertEqual(role['token_policies'], ['perkforge-sso-platform-admin'])
        policy = bao['policies']['perkforge-sso-platform-admin']
        self.assertNotIn('tenants/data', policy)
        self.assertIn('path "tenants/metadata/*" { capabilities = ["list"] }', policy)
        for forbidden in ('sys/', 'auth/', 'destroy/', 'human-platform-tenant-access'):
            self.assertNotIn(forbidden, policy)

    def test_live_activation_bad_targets_and_duplicate_clients_refuse(self):
        variants=[]
        for app in self.vars['sso_apps']:
            v=copy.deepcopy(self.vars); v['sso_apps'][app]['apply']=True; variants.append(v)
        v=copy.deepcopy(self.vars); v['sso_apps']['rancher']['client_id']=v['sso_apps']['headlamp']['client_id']; variants.append(v)
        v=copy.deepcopy(self.vars); v['sso_apps']['rancher']['origin']='http://rancher.example.test'; variants.append(v)
        v=copy.deepcopy(self.vars); v['sso_keycloak_origin']='https://identity.example.test/other'; variants.append(v)
        v=copy.deepcopy(self.vars); v['sso_realm']='master'; variants.append(v)
        for v in variants:
            with self.subTest(v=v):
                self.assertNotEqual(self.run_play(v).returncode, 0)
                self.assertFalse(self.output.exists())

    def test_preserves_output_and_uses_private_permissions(self):
        self.render()
        original=(self.output/'clients.yaml').read_bytes()
        self.assertEqual(self.output.stat().st_mode & 0o777, 0o700)
        self.assertEqual((self.output/'clients.yaml').stat().st_mode & 0o777, 0o600)
        self.assertNotEqual(self.run_play().returncode, 0)
        self.assertEqual((self.output/'clients.yaml').read_bytes(), original)

    def test_environment_inputs_change_payload_without_template_edits(self):
        self.vars['sso_keycloak_origin']='https://login.other.test:8443'
        self.vars['sso_keycloak_path']=''
        self.vars['sso_apps']['headlamp']['origin']='https://dashboard.other.test'
        data=self.render()
        self.assertEqual(data['headlamp']['issuer'], 'https://login.other.test:8443/realms/perkforge')
        self.assertEqual(data['headlamp']['callback'], 'https://dashboard.other.test/oidc-callback')


if __name__ == '__main__':
    unittest.main()
