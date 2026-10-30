"""Offline checks; synthetic API fixtures never target a live cluster."""
from collections import Counter
from copy import deepcopy
import os, subprocess, tempfile, unittest, base64, uuid
from pathlib import Path
import yaml
from fixtures.render_helpers import build, child_values, helm, ordered_values, release_name
from fixtures.resource_inventory import inventory
from fixtures.lookup_server import lookup_server, secret_allowed
ROOT = Path(__file__).resolve().parents[2]
EXAMPLES = ROOT
EX = ROOT
CLUSTER = ROOT / 'clusters/local'
STAGE = ROOT / 'configuration/identity'
from fixtures.package_context import IdentityFixture

class IdentityBootstrapTests(IdentityFixture):
    def test_one_shot_realm_claims_and_gated_ansible(self):
        # Parse without rendering secret lookups; never read private files offline.
        realm = yaml.safe_load((EX / 'configuration/packages/keycloak/realm.yaml').read_text())
        client = realm['clients'][0]
        self.assertTrue(client['standardFlowEnabled'])
        for key in ['publicClient', 'implicitFlowEnabled', 'directAccessGrantsEnabled', 'serviceAccountsEnabled', 'fullScopeAllowed']:
            self.assertFalse(client[key])
        self.assertEqual(client['attributes']['pkce.code.challenge.method'], 'S256')
        self.assertEqual(client['protocolMappers'][0]['config']['full.path'], 'true')
        self.assertEqual([u['groups'] for u in realm['users']], [['/platform/admins'], ['/platform/developers'], []])
        for name in ['keycloak-prerequisites', 'keycloak-realm', 'identity-verify']:
            play = yaml.safe_load((EX / 'configuration/ansible' / (name + '.yaml')).read_text())[0]
            self.assertFalse(next(v for k, v in play['vars'].items() if k.endswith('_apply') or k == 'identity_verify'))
            with tempfile.TemporaryDirectory() as temp:
                env = {**os.environ, 'ANSIBLE_LOCAL_TEMP': temp + '/local', 'ANSIBLE_REMOTE_TEMP': temp + '/remote'}
                result = subprocess.run(['ansible-playbook', '-i', str(EX / 'configuration/ansible/inventory.yaml'),
                                         str(EX / 'configuration/ansible' / (name + '.yaml')), '--limit', 'local', '--check'],
                                        env=env, text=True, capture_output=True)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertNotIn('UNCONFIGURED/id-tokens', result.stdout)
                self.assertIn('changed=0', result.stdout)
