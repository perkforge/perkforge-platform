"""Real Ansible against a disposable HTTPS fixture; no live credentials or clients."""
import copy
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import ssl
import subprocess
import tempfile
import threading
import unittest
from urllib.parse import urlsplit
import yaml

ROOT = Path(__file__).resolve().parents[3]
SSO = ROOT / 'big-bang-bootstrap/configuration/authorization/sso'
PLAY = SSO / 'harbor/reconcile-client.yaml'
CLIENT = '11111111-1111-4111-8111-111111111111'
ROLE = '22222222-2222-4222-8222-222222222222'
GROUP = '33333333-3333-4333-8333-333333333333'

def role():
    return dict(id=ROLE, name='admins', description='harbor-sso-review-v1',
                clientRole=True, composite=False, containerId=CLIENT)



class HarborClient(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.d = Path(self.tmp.name)
        subprocess.run(['openssl', 'req', '-x509', '-newkey', 'rsa:2048', '-nodes', '-days', '1',
                        '-subj', '/CN=localhost', '-addext', 'subjectAltName=DNS:localhost',
                        '-keyout', str(self.d / 'key'), '-out', str(self.d / 'ca')],
                       check=True, capture_output=True)
        self.s = dict(client=None, calls=[], writes=[], roles=[], scope={}, optional=[],
                      scopes=['basic', 'profile', 'email'], lost_create=False, group_roles=[], role_users=[], role_groups=[], composites=[],
                      group_path='/platform/admins', inherited=[], secret='fixture-existing-client-secret')
        self.s['mappers'] = yaml.safe_load((SSO / 'client-scopes.yaml').read_text())['sso_expected_client_scopes']
        s = self.s

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def reply(self, status, value=None):
                self.send_response(status)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                if value is not None:
                    self.wfile.write(json.dumps(value).encode())

            def do_GET(self):
                p = urlsplit(self.path).path.removeprefix('/auth/admin/realms/perkforge')
                s['calls'].append(('GET', p))
                if self.headers.get('Authorization') != 'Bearer fixture-operator-token':
                    return self.reply(403, {})
                if p == '':
                    return self.reply(200, dict(realm='perkforge', enabled=True, attributes={
                        'perkforge-managed': 'true', 'perkforge-purpose': 'realm-foundation-v1'}))
                if p == '/client-scopes':
                    return self.reply(200, [dict(id=n, name=n, protocol='openid-connect') for n in s['mappers']])
                if p.startswith('/client-scopes/'):
                    return self.reply(200, s['mappers'][p.split('/')[2]])
                if p == '/clients':
                    return self.reply(200, [] if s['client'] is None else [dict(id=s.get('lookup_id', CLIENT), clientId='harbor')])
                if p == '/clients/' + CLIENT:
                    return self.reply(200, s['client'])
                if p == '/clients/' + CLIENT + '/default-client-scopes':
                    return self.reply(200, [dict(id=n, name=n) for n in s['scopes']])
                if p == '/clients/' + CLIENT + '/optional-client-scopes':
                    return self.reply(200, s['optional'])
                if p == '/clients/' + CLIENT + '/protocol-mappers/models':
                    return self.reply(200, s['client']['protocolMappers'])
                if p == '/clients/' + CLIENT + '/scope-mappings':
                    return self.reply(200, s['scope'])
                if p == '/clients/' + CLIENT + '/roles':
                    return self.reply(200, s['roles'])
                if p == '/clients/' + CLIENT + '/client-secret':
                    return self.reply(200, dict(value=s['secret']))
                if p == '/clients/' + CLIENT + '/scope-mappings/clients/' + CLIENT:
                    return self.reply(200, s['scope'].get('clientMappings', {}).get('harbor', {}).get('mappings', []))
                if p == '/roles-by-id/' + ROLE + '/composites':
                    return self.reply(200, s['composites'])
                if p == '/clients/' + CLIENT + '/roles/admins/users':
                    return self.reply(200, s['role_users'])
                if p == '/clients/' + CLIENT + '/roles/admins/groups':
                    return self.reply(200, s['role_groups'])
                if p == '/groups/' + GROUP:
                    return self.reply(200, dict(id=GROUP, path=s['group_path'], name='admins'))
                if p == '/groups/' + GROUP + '/role-mappings/clients/' + CLIENT:
                    return self.reply(200, s['group_roles'])
                if p == '/groups/' + GROUP + '/role-mappings/clients/' + CLIENT + '/composite':
                    return self.reply(200, s['group_roles'] + s['inherited'])
                return self.reply(404, {})

            def mutate(self):
                p = urlsplit(self.path).path.removeprefix('/auth/admin/realms/perkforge')
                s['writes'].append((self.command, p))
                if self.command == 'POST' and p == '/clients':
                    data = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                    s['secret'] = data.pop('secret')
                    s['client'] = dict(data, id=CLIENT)
                    return self.reply(503 if s['lost_create'] else 201)
                data = json.loads(self.rfile.read(int(self.headers.get('Content-Length', '0'))) or b'{}')
                if self.command == 'POST' and p == '/clients/' + CLIENT + '/roles':
                    s['roles'] = [dict(data, id=ROLE, containerId=CLIENT, clientRole=True)]
                    return self.reply(201)
                if self.command == 'POST' and p == '/clients/' + CLIENT + '/scope-mappings/clients/' + CLIENT:
                    s['scope'] = dict(clientMappings={'harbor': dict(id=CLIENT, client='harbor', mappings=data)})
                    return self.reply(204)
                if self.command == 'POST' and p == '/groups/' + GROUP + '/role-mappings/clients/' + CLIENT:
                    s['group_roles'] = data
                    s['role_groups'] = [dict(id=GROUP, name='admins', path='/platform/admins')]
                    return self.reply(204)
                if self.command == 'PUT' and p == '/clients/' + CLIENT:
                    if set(data) != {'enabled'}:
                        return self.reply(400)
                    s['client'].update(data)
                    return self.reply(204)
                return self.reply(405, {})

            do_POST = mutate
            do_PUT = mutate
            do_DELETE = mutate

        self.server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(self.d / 'ca', self.d / 'key')
        self.server.socket = context.wrap_socket(self.server.socket, server_side=True)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)
        for name, value in [('token', 'fixture-operator-token'), ('secret', 'fixture-existing-client-secret')]:
            (self.d / name).write_text(value)
            (self.d / name).chmod(0o600)
        self.v = dict(harbor_client_run=True, harbor_recovery_verified=True, harbor_client_uuid=CLIENT,
                      harbor_admin_group_uuid=GROUP,
                      harbor_sso_origin='https://harbor.example.test',
                      harbor_sso_issuer=f'https://localhost:{self.server.server_port}/auth/realms/perkforge',
                      harbor_operator_token_file=str(self.d / 'token'),
                      harbor_client_secret_file=str(self.d / 'secret'), harbor_ca_file=str(self.d / 'ca'))

    def run_play(self, op='prepare', extra=None, success=True, check=False):
        v = dict(self.v, harbor_client_operation=op, harbor_client_approval=f'harbor-client-{op}-v1')
        v.update(extra or {})
        p = subprocess.run(['ansible-playbook', str(PLAY), '-e', json.dumps(v)] + (['--check'] if check else []),
                           env=dict(os.environ, KUBECONFIG='/dev/null', ANSIBLE_LOCAL_TEMP=str(self.d / 'local'),
                                    ANSIBLE_REMOTE_TEMP=str(self.d / 'remote')),
                           capture_output=True, text=True, timeout=120)
        self.assertEqual(p.returncode == 0, success, p.stdout + p.stderr)
        for secret in ['fixture-operator-token', 'fixture-existing-client-secret']:
            self.assertNotIn(secret, p.stdout + p.stderr)
        return p

    def seed(self):
        self.s['client'] = json.loads((SSO / 'harbor/client.json').read_text())
        self.s['client'].update(id=CLIENT, redirectUris=['https://harbor.example.test/c/oidc/callback'])
        self.s['client']['attributes']['post.logout.redirect.uris'] = 'https://harbor.example.test/account/sign-in'
        self.s['roles'] = [role()]
        self.s['scope'] = dict(clientMappings={'harbor': dict(id=CLIENT, client='harbor', mappings=[role()])})

    def test_default_check_and_approval_never_contact(self):
        self.run_play(extra={'harbor_client_run': False, 'harbor_operator_token_file': '/nonexistent'})
        self.run_play(check=True, extra={'harbor_operator_token_file': '/nonexistent'})
        for extra in [dict(harbor_client_approval='UNAPPROVED'), dict(harbor_recovery_verified=False),
                      dict(harbor_sso_origin='https://harbor.EXAMPLE.INVALID:443'),
                      dict(harbor_sso_origin="https://harbor.example.test\n"),
                      dict(harbor_sso_origin='https://localhost:' + str(self.server.server_port)),
                      dict(harbor_sso_issuer='https://localhost:65536/realms/perkforge')]:
            self.run_play(extra=extra, success=False)
        self.run_play('activate', success=False)
        self.assertEqual(self.s['calls'], [])
        self.assertEqual(self.s['writes'], [])

    def test_prepare_repeat_and_metadata_inspect(self):
        self.run_play()
        self.assertFalse(self.s['client']['enabled'])
        self.assertIn('changed=0', self.run_play().stdout)
        self.s['calls'].clear()
        self.run_play('inspect', extra={'harbor_client_secret_file': '/nonexistent'})
        self.assertNotIn(('GET', '/clients/' + CLIENT + '/client-secret'), self.s['calls'])
        self.assertEqual(self.s['writes'], [('POST', '/clients'), ('POST', '/clients/' + CLIENT + '/roles'),
                                                    ('POST', '/clients/' + CLIENT + '/scope-mappings/clients/' + CLIENT)])

    def test_missing_inspect_and_interrupted_create(self):
        self.run_play('inspect', success=False)
        self.assertEqual(self.s['writes'], [])
        self.s['lost_create'] = True
        self.run_play(success=False)
        self.assertFalse(self.s['client']['enabled'])
        self.s['lost_create'] = False
        self.assertIn('changed=2', self.run_play().stdout)
        self.assertIn('changed=0', self.run_play().stdout)
        self.assertEqual(self.s['writes'], [('POST', '/clients'), ('POST', '/clients/' + CLIENT + '/roles'),
                                                    ('POST', '/clients/' + CLIENT + '/scope-mappings/clients/' + CLIENT)])

    def test_client_and_mapper_drift_never_mutate(self):
        self.seed()
        original = copy.deepcopy(self.s['client'])
        for changes in [dict(enabled=True), dict(fullScopeAllowed=True), dict(publicClient=True),
                        dict(redirectUris=['https://foreign.test/']), dict(attributes={}),
                        dict(authenticationFlowBindingOverrides={'browser': 'foreign'}),
                        dict(authorizationServicesEnabled=True)]:
            self.s['client'] = dict(copy.deepcopy(original), **changes)
            self.run_play(success=False)
        self.s['client'] = original
        self.s['client']['protocolMappers'][1]['config']['usermodel.clientRoleMapping.clientId'] = 'foreign'
        self.run_play(success=False)
        self.assertEqual(self.s['writes'], [])

    def test_malformed_lookup_id_refused_before_target_read(self):
        self.seed()
        self.s["lookup_id"] = CLIENT + '\n'
        self.run_play("inspect", success=False)
        self.assertNotIn(("GET", "/clients/" + CLIENT), self.s["calls"])
        self.assertEqual(self.s["writes"], [])

    def test_scope_and_role_drift_never_mutate(self):
        self.seed()
        for field, value in [('roles', [{'name': '/platform/admins'}]), ('optional', [{'name': 'roles'}]),
                             ('scopes', ['basic']), ('scope', {'realmMappings': [{'name': 'admin'}]}),
                             ('scope', {'clientMappings': {'harbor': {}}})]:
            old = self.s[field]
            self.s[field] = value
            self.run_play('inspect', success=False)
            self.s[field] = old
        self.assertEqual(self.s['writes'], [])

    def test_hidden_shared_scope_mapper_blocks_creation(self):
        self.s['mappers']['profile'].append(dict(name='groups', protocol='openid-connect',
                                                protocolMapper='oidc-group-membership-mapper', config={}))
        self.run_play(success=False)
        self.assertEqual(self.s['writes'], [])

    def test_secret_mismatch_does_not_rotate_and_private_modes_refuse(self):
        self.seed()
        self.s['secret'] = 'different-secret'
        self.run_play(success=False)
        self.d.chmod(0o755)
        self.run_play(success=False)
        self.d.chmod(0o700)
        (self.d / 'token').chmod(0o644)
        self.s['calls'].clear()
        self.run_play(success=False)
        self.assertEqual(self.s['calls'], [])
        self.assertEqual(self.s['writes'], [])

    def test_group_grant_enable_and_disable_are_exact_and_repeatable(self):
        self.seed()
        approval = dict(harbor_admin_grant_approval='harbor-platform-admin-group-v1')
        self.run_play('activate', extra=approval | dict(harbor_native_verified=True), success=False)
        self.assertEqual(self.s['writes'], [])
        self.run_play('grant-admin-group', extra=approval)
        self.assertIn('changed=0', self.run_play('grant-admin-group', extra=approval).stdout)
        before = copy.deepcopy(self.s['client'])
        self.run_play('activate', extra=approval | dict(harbor_native_verified=True))
        self.assertTrue(self.s['client']['enabled'])
        self.assertIn('changed=0', self.run_play('activate', extra=approval | dict(harbor_native_verified=True, harbor_client_expected_enabled=True)).stdout)
        self.run_play('disable', extra=dict(harbor_client_expected_enabled=True))
        self.assertEqual(self.s['client'], before)
        self.assertEqual(self.s['group_roles'], [role()])
        self.assertEqual(self.s['writes'], [('POST', '/groups/' + GROUP + '/role-mappings/clients/' + CLIENT),
                                          ('PUT', '/clients/' + CLIENT), ('PUT', '/clients/' + CLIENT)])

    def test_foreign_grants_scope_group_and_uuid_never_mutate(self):
        self.seed()
        approval = dict(harbor_admin_grant_approval='harbor-platform-admin-group-v1')
        for key, value in [('role_users', [dict(id='foreign')]),
                           ('role_groups', [dict(id=GROUP, path='/foreign')]),
                           ('composites', [dict(id='foreign')]), ('group_path', '/foreign'),
                           ('inherited', [dict(id='foreign')])]:
            old = copy.deepcopy(self.s[key]); self.s[key] = value
            self.run_play('grant-admin-group', extra=approval, success=False)
            self.s[key] = old
        self.run_play('inspect', extra=dict(harbor_client_uuid='99999999-9999-4999-8999-999999999999'), success=False)
        self.s['scope'] = dict(clientMappings={'foreign': dict(id='foreign', mappings=[])})
        self.s['roles'] = []
        self.run_play(success=False)
        self.assertEqual(self.s['writes'], [])

    def test_partial_role_and_scope_creation_resumes_without_recreating_client(self):
        self.seed()
        self.s['roles'] = []
        self.s['scope'] = {}
        self.run_play()
        self.assertNotIn(('POST', '/clients'), self.s['writes'])
        self.assertEqual(len(self.s['writes']), 2)
        self.assertIn('changed=0', self.run_play().stdout)

    def test_tls_verification_and_secret_redaction(self):
        (self.d / 'wrongca').write_text('not a certificate')
        self.run_play(extra=dict(harbor_ca_file=str(self.d / 'wrongca')), success=False)
        self.assertEqual(self.s['calls'], [])
        self.assertEqual(self.s['writes'], [])
