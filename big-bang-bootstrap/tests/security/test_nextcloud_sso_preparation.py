import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
import yaml

ROOT = Path(__file__).resolve().parents[3]

class SsoPreparation(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.directory = Path(self.tmp.name)
        self.env = dict(os.environ, ANSIBLE_LOCAL_TEMP=str(self.directory / 'ansible'),
                        ANSIBLE_REMOTE_TEMP=str(self.directory / 'remote'))

    def run_play(self, inputs=None, check=False, success=True):
        args = ['ansible-playbook', str(ROOT / PLAY), '-e', json.dumps(inputs or {})]
        if check:
            args.append('--check')
        result = subprocess.run(args, env=self.env, text=True, capture_output=True)
        self.assertEqual(result.returncode == 0, success, result.stdout + result.stderr)
        return result

    def test_default_and_check_do_not_read_inputs_or_write_output(self):
        self.run_play()
        self.run_play({FLAG: True, OUTPUT: str(self.directory / 'check')}, check=True)
        self.assertFalse((self.directory / 'check').exists())

    def test_disabled_exact_client_and_deny_all_provider(self):
        output = self.directory / 'review'
        inputs = {FLAG: True, OUTPUT: str(output),
                  'nextcloud_sso_origin': 'https://files.example.test',
                  'nextcloud_sso_issuer': 'https://identity.example.test/auth/realms/perkforge'}
        self.run_play(inputs)
        client = json.loads((output / 'client.json').read_text())
        self.assertFalse(client['enabled'])
        self.assertEqual(client['redirectUris'], ['https://files.example.test/index.php/apps/user_oidc/code'])
        self.assertEqual(client['attributes']['post.logout.redirect.uris'], 'https://files.example.test/')
        self.assertFalse(client['fullScopeAllowed'])
        self.assertEqual(client['defaultClientScopes'], ['basic'])
        for key in ['implicitFlowEnabled', 'directAccessGrantsEnabled', 'serviceAccountsEnabled']:
            self.assertFalse(client[key])
        self.assertEqual(client['attributes']['pkce.code.challenge.method'], 'S256')
        self.assertEqual(client['protocolMappers'][1]['config']['usermodel.clientRoleMapping.clientId'], 'nextcloud')
        self.assertEqual(len(client['protocolMappers']), 3)
        self.assertEqual(client['protocolMappers'][2]['name'], 'nextcloud-display-name')
        self.assertEqual(client['protocolMappers'][2]['config'], {'id.token.claim':'true', 'access.token.claim':'false', 'userinfo.token.claim':'false', 'introspection.token.claim':'false'})
        provider = yaml.safe_load((output / 'provider.yaml').read_text())
        self.assertEqual(provider['mapping_uid'], 'sub')
        self.assertEqual(provider['mapping_display_name'], 'name')
        self.assertTrue(provider['unique_uid'])
        self.assertFalse(provider['soft_auto_provision'])
        self.assertEqual(provider['provisioning_decision'], 'UNAPPROVED')
        self.assertEqual(provider['group_whitelist_regex'], '/^(?!)$/')
        before = (output / 'client.json').read_bytes()
        self.run_play(inputs, success=False)
        self.assertEqual(before, (output / 'client.json').read_bytes())
        self.assertEqual(output.stat().st_mode & 0o777, 0o700)
        self.assertEqual((output / 'client.json').stat().st_mode & 0o777, 0o600)

    def test_issuer_callback_conflicts_refused(self):
        for changes in [ {'nextcloud_sso_origin': 'https://files.example.test/other'},
                         {'nextcloud_sso_issuer': 'https://identity.example.test/realms/foreign'},
                         {'nextcloud_sso_origin': 'https://same.example.test',
                          'nextcloud_sso_issuer': 'https://same.example.test/realms/perkforge'}]:
            self.run_play(changes, success=False)

PLAY = 'big-bang-bootstrap/configuration/authorization/sso/nextcloud/prepare.yaml'
FLAG = 'nextcloud_sso_render'
OUTPUT = 'nextcloud_sso_output'
