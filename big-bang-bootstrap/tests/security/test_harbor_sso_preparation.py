"""Offline public payload preparation; no credentials or live API calls."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
import yaml

ROOT = Path(__file__).resolve().parents[3]
SSO = ROOT / 'big-bang-bootstrap/configuration/authorization/sso/harbor'

class HarborPreparation(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.d = Path(self.tmp.name)
        self.output = self.d / 'review'
        self.v = dict(harbor_sso_render=True, harbor_sso_output=str(self.output),
                      harbor_sso_origin='https://harbor.example.test',
                      harbor_sso_issuer='https://identity.example.test/auth/realms/perkforge')

    def run_play(self, extra=None, check=False, success=True):
        v = self.v | (extra or {})
        p = subprocess.run(['ansible-playbook', str(SSO / 'prepare.yaml'), '-e', json.dumps(v)]
                           + (['--check'] if check else []),
                           env=dict(os.environ, KUBECONFIG='/dev/null',
                                    ANSIBLE_LOCAL_TEMP=str(self.d / 'local'),
                                    ANSIBLE_REMOTE_TEMP=str(self.d / 'remote')),
                           capture_output=True, text=True, timeout=45)
        self.assertEqual(p.returncode == 0, success, p.stdout + p.stderr)

    def test_default_and_check_no_output(self):
        self.run_play(dict(harbor_sso_render=False))
        self.run_play(check=True)
        self.assertFalse(self.output.exists())
        tasks = yaml.safe_load((SSO / 'prepare.yaml').read_text())[0]['tasks']
        def modules(items):
            for t in items:
                yield from (k for k in t if k.startswith('ansible.builtin.'))
                yield from modules(t.get('block', []))
        self.assertEqual(set(modules(tasks)), {'ansible.builtin.assert', 'ansible.builtin.debug',
                                             'ansible.builtin.stat', 'ansible.builtin.file', 'ansible.builtin.copy'})

    def test_exact_disabled_client_and_repeat_preservation(self):
        self.run_play()
        f = self.output / 'client.json'
        c = json.loads(f.read_text())
        self.assertEqual(c['clientId'], 'harbor')
        for flag in ['enabled', 'publicClient', 'fullScopeAllowed', 'implicitFlowEnabled',
                     'directAccessGrantsEnabled', 'serviceAccountsEnabled']:
            self.assertFalse(c[flag])
        self.assertEqual(c['redirectUris'], [self.v['harbor_sso_origin'] + '/c/oidc/callback'])
        self.assertEqual(c['attributes']['post.logout.redirect.uris'], self.v['harbor_sso_origin'] + '/account/sign-in')
        self.assertEqual(c['attributes']['pkce.code.challenge.method'], 'S256')
        self.assertEqual(c['protocolMappers'][1]['config']['usermodel.clientRoleMapping.rolePrefix'], '/platform/')
        self.assertEqual(c['protocolMappers'][1]['config']['usermodel.clientRoleMapping.clientId'], 'harbor')
        self.assertNotIn('secret', c)
        self.assertNotIn('roles', c)
        self.assertEqual(c['webOrigins'], [])
        self.assertEqual(c['optionalClientScopes'], [])
        self.assertEqual(c['defaultClientScopes'], ['basic', 'profile', 'email'])
        before = f.read_bytes()
        self.run_play(success=False)
        self.assertEqual(f.read_bytes(), before)
        self.assertEqual(self.output.stat().st_mode & 0o777, 0o700)
        self.assertEqual(f.stat().st_mode & 0o777, 0o600)

    def test_invalid_identity_and_existing_symlink_refused(self):
        for origin in ['http://harbor.test', 'https://harbor.example.invalid',
                       'https://harbor.example.test\n', 'https://*.example.test',
                       'https://identity.example.test:443', 'https://harbor.test/path']:
            self.run_play(dict(harbor_sso_origin=origin), success=False)
            self.assertFalse(self.output.exists())
        target = self.d / 'keep'; target.mkdir()
        (target / 'sentinel').write_text('keep')
        self.output.symlink_to(target, target_is_directory=True)
        self.run_play(success=False)
        self.assertEqual(list(target.iterdir()), [target / 'sentinel'])
