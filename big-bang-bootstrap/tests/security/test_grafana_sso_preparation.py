"""Offline Ansible payload contract; no live clients or credentials."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
import yaml

ROOT = Path(__file__).resolve().parents[3]
SSO = ROOT / 'big-bang-bootstrap/configuration/authorization/sso'

class GrafanaPreparation(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.directory = Path(self.tmp.name)
        self.output = self.directory / 'review'
        self.inputs = dict(grafana_sso_render=True, grafana_sso_output=str(self.output),
                          grafana_sso_origin='https://grafana.example.test',
                          grafana_sso_issuer='https://identity.example.test/auth/realms/perkforge')

    def run_play(self, inputs, check=False, success=True):
        env = dict(os.environ, KUBECONFIG='/dev/null',
                   ANSIBLE_LOCAL_TEMP=str(self.directory / 'ansible'),
                   ANSIBLE_REMOTE_TEMP=str(self.directory / 'remote'))
        args = ['ansible-playbook', str(SSO / 'grafana/prepare.yaml'), '-e', json.dumps(inputs)]
        if check:
            args.append('--check')
        result = subprocess.run(args, env=env, text=True, capture_output=True)
        self.assertEqual(result.returncode == 0, success, result.stdout + result.stderr)

    def test_default_and_check_are_inert(self):
        self.run_play({})
        self.run_play(self.inputs, check=True)
        self.assertFalse(self.output.exists())
        tasks = yaml.safe_load((SSO / 'grafana/prepare.yaml').read_text())[0]['tasks']
        def modules(items):
            for task in items:
                yield from (k for k in task if k.startswith('ansible.builtin.'))
                yield from modules(task.get('block', []))
        self.assertEqual(set(modules(tasks)), {'ansible.builtin.assert', 'ansible.builtin.debug',
                         'ansible.builtin.stat', 'ansible.builtin.file',
                         'ansible.builtin.copy', 'ansible.builtin.template'})

    def test_disabled_client_and_exact_provider_pair(self):
        self.run_play(self.inputs)
        client = json.loads((self.output / 'client.json').read_text())
        self.assertEqual(client['clientId'], 'grafana')
        for flag in ['enabled', 'publicClient', 'fullScopeAllowed', 'implicitFlowEnabled',
                     'directAccessGrantsEnabled', 'serviceAccountsEnabled']:
            self.assertFalse(client[flag])
        self.assertEqual(client['redirectUris'], ['https://grafana.example.test/login/generic_oauth'])
        self.assertEqual(client['webOrigins'], [])
        self.assertEqual(client['defaultClientScopes'], ['basic', 'profile', 'email'])
        self.assertEqual(client['optionalClientScopes'], [])
        self.assertEqual(client['attributes']['pkce.code.challenge.method'], 'S256')
        self.assertNotIn('secret', client)
        self.assertNotIn('roles', client)
        mapper = client['protocolMappers'][1]
        self.assertEqual(mapper['protocolMapper'], 'oidc-usermodel-client-role-mapper')
        self.assertEqual(mapper['config']['usermodel.clientRoleMapping.clientId'], 'grafana')
        self.assertEqual(mapper['config']['claim.name'], 'groups')
        values = yaml.safe_load((self.output / 'values.yaml').read_text())
        self.assertFalse(values['grafana']['enabled'])
        self.assertTrue(values['grafana']['flux']['suspend'])
        self.assertFalse(values['grafana']['values']['sso']['enabled'])
        ini = values['grafana']['values']['upstream']['grafana.ini']
        self.assertEqual(ini['server']['root_url'], self.inputs['grafana_sso_origin'])
        self.assertFalse(ini['auth']['disable_login_form'])
        self.assertTrue(ini['auth.basic']['enabled'])
        oauth = ini['auth.generic_oauth']
        self.assertFalse(oauth['enabled'])
        self.assertTrue(oauth['role_attribute_strict'])
        self.assertFalse(oauth['tls_skip_verify_insecure'])
        for name, suffix in [('auth_url', 'auth'), ('token_url', 'token'), ('api_url', 'userinfo')]:
            self.assertEqual(oauth[name], self.inputs['grafana_sso_issuer'] + '/protocol/openid-connect/' + suffix)
        self.assertEqual(oauth['client_secret'], '$__env{GRAFANA_OIDC_CLIENT_SECRET}')
        self.assertEqual(self.output.stat().st_mode & 0o777, 0o700)
        for file in self.output.iterdir():
            self.assertEqual(file.stat().st_mode & 0o777, 0o600)

    def test_unsafe_or_placeholder_endpoints_refused_before_output(self):
        cases = [dict(grafana_sso_origin=v) for v in [
            'http://grafana.example.test', 'https://grafana.example.test/path',
            'https://*.example.test', 'https://user@grafana.example.test',
            'https://grafana.example.invalid', 'https://grafana.EXAMPLE.INVALID:443',
            'https://IDENTITY.example.test', 'https://identity.example.test:443',
            'https://grafana.example.test:0', 'https://grafana.example.test:65536']]
        cases += [dict(grafana_sso_issuer=v) for v in [
            'http://identity.example.test/realms/perkforge',
            'https://identity.example.test/realms/foreign',
            'https://identity.example.invalid/realms/perkforge',
            'https://identity.EXAMPLE.INVALID:443/realms/perkforge',
            'https://identity.example.test/realms/perkforge?x=1',
            'https://identity.example.test:0/realms/perkforge',
            'https://identity.example.test:65536/realms/perkforge']]
        cases.append(dict(grafana_sso_origin='https://identity.example.test',
                          grafana_sso_issuer='https://identity.example.test:443/realms/perkforge'))
        for changes in cases:
            with self.subTest(changes=changes):
                self.run_play(self.inputs | changes, success=False)
                self.assertFalse(self.output.exists())

    def test_unsafe_output_and_existing_symlink_refused(self):
        for output in ['relative', '/UNCONFIGURED/review', '/']:
            self.run_play(self.inputs | {'grafana_sso_output': output}, success=False)
        target = self.directory / 'preserve'
        target.mkdir()
        (target / 'sentinel').write_text('keep')
        self.output.symlink_to(target, target_is_directory=True)
        self.run_play(self.inputs, success=False)
        self.assertEqual((target / 'sentinel').read_text(), 'keep')
        self.assertEqual(list(target.iterdir()), [target / 'sentinel'])

    def test_repeat_preserves_existing_payloads(self):
        self.run_play(self.inputs)
        before = {p.name: p.read_bytes() for p in self.output.iterdir()}
        self.run_play(self.inputs, success=False)
        self.assertEqual(before, {p.name: p.read_bytes() for p in self.output.iterdir()})

    def test_no_auth_prefix_is_supported(self):
        self.run_play(self.inputs | {'grafana_sso_issuer': 'https://identity.example.test/realms/perkforge'})
        self.assertIn('https://identity.example.test/realms/perkforge/protocol/openid-connect/auth',
                      (self.output / 'values.yaml').read_text())

    def test_provider_retains_existing_review_policy(self):
        original = (ROOT / 'big-bang-bootstrap/configuration/observability/grafana-sso-values.yaml').read_text()
        expected = original.replace(original.splitlines()[0], '# Offline review payload only; no client grants or source selection.')
        expected = expected.replace('https://grafana.UNCONFIGURED.invalid', '{{ grafana_sso_origin }}')
        expected = expected.replace('https://identity.UNCONFIGURED.invalid/auth/realms/perkforge', '{{ grafana_sso_issuer }}')
        expected = expected.replace('auth.generic_oauth:\n          enabled: true', 'auth.generic_oauth:\n          enabled: false')
        self.assertEqual((SSO / 'grafana/values.yaml.j2').read_text(), expected)

    @unittest.skipUnless(os.environ.get('PREFLIGHT_SOURCES_DIR'), 'requires pinned public chart fixtures')
    def test_generated_values_render_with_pinned_grafana(self):
        from fixtures.observability import metrics_render
        self.run_play(self.inputs)
        objects = metrics_render(ROOT / 'big-bang-bootstrap', [self.output / 'values.yaml'])['grafana'][1]
        ini = '\n'.join(str(v) for obj in objects if obj['kind'] == 'ConfigMap'
                        for v in obj.get('data', {}).values())
        self.assertIn('root_url = https://grafana.example.test', ini)
        self.assertIn('client_secret = $__env{GRAFANA_OIDC_CLIENT_SECRET}', ini)
        self.assertIn('disable_login_form = false', ini)
        self.assertIn('role_attribute_strict = true', ini)
        self.assertIn('[auth.generic_oauth]\n', ini)
        oauth = ini.split('[auth.generic_oauth]\n', 1)[1].split('\n[', 1)[0]
        self.assertIn('enabled = false', oauth)
