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
from urllib.request import Request, urlopen
import yaml

ROOT = Path(__file__).resolve().parents[3]
SSO = ROOT / 'big-bang-bootstrap/configuration/authorization/sso'
PLAY = SSO / 'mattermost/reconcile-client.yaml'


class MattermostClient(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.d = Path(self.tmp.name)
        subprocess.run(['openssl', 'req', '-x509', '-newkey', 'rsa:2048', '-nodes', '-days', '1',
                        '-subj', '/CN=localhost', '-addext', 'subjectAltName=DNS:localhost',
                        '-keyout', str(self.d / 'key'), '-out', str(self.d / 'ca')],
                       check=True, capture_output=True)
        self.s = dict(client=None, calls=[], writes=[], toggle_bodies=[], roles=[], scope={}, optional=[],
                      scope_roles=[], users={}, members={}, inherited={}, groups=[], extra_members=[], lost_role=False, lost_enable=False, scopes=['basic', 'profile', 'email'], lost_create=False, secret='fixture-existing-client-secret')
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
                    return self.reply(200, [] if s['client'] is None else [dict(id=s.get('lookup_id', 'mm-id'), clientId='mattermost')])
                if p == '/clients/mm-id':
                    return self.reply(200, s['client'])
                if p == '/clients/mm-id/default-client-scopes':
                    return self.reply(200, [dict(id=n, name=n) for n in s['scopes']])
                if p == '/clients/mm-id/optional-client-scopes':
                    return self.reply(200, s['optional'])
                if p == '/clients/mm-id/protocol-mappers/models':
                    return self.reply(200, s['client']['protocolMappers'])
                if p == '/clients/mm-id/scope-mappings':
                    return self.reply(200, s['scope'] or ({'clientMappings': {'mattermost': {'id': 'mm-id', 'client': 'mattermost', 'mappings': s['scope_roles']}}} if s['scope_roles'] else {}))
                if p == '/clients/mm-id/scope-mappings/clients/mm-id':
                    return self.reply(200, s['scope_roles'])
                if p == '/clients/mm-id/roles/%2Fplatform%2Fadmins/groups':
                    return self.reply(200, s['groups'])
                if p == '/clients/mm-id/roles/%2Fplatform%2Fadmins/users':
                    return self.reply(200, [dict(id=u) for u,r in s['members'].items() if r] + s['extra_members'])
                if p.startswith('/users/'):
                    u = p.split('/')[2]
                    if p == '/users/' + u:
                        return self.reply(200, s['users'].get(u, dict(id=u, enabled=True)))
                    if p.endswith('/role-mappings/clients/mm-id'):
                        return self.reply(200, s['members'].get(u, []))
                    if p.endswith('/role-mappings/clients/mm-id/composite'):
                        return self.reply(200, s['members'].get(u, []) + s['inherited'].get(u, []))
                if p == '/clients/mm-id/roles':
                    return self.reply(200, s['roles'])
                if p == '/clients/mm-id/client-secret':
                    return self.reply(200, dict(value=s['secret']))
                return self.reply(404, {})

            def mutate(self):
                p = urlsplit(self.path).path.removeprefix('/auth/admin/realms/perkforge')
                s['writes'].append((self.command, p))
                if self.command == 'POST' and p == '/clients':
                    data = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                    s['secret'] = data.pop('secret')
                    s['client'] = dict(data, id='mm-id')
                    return self.reply(503 if s['lost_create'] else 201)
                if self.headers.get('Authorization') != 'Bearer fixture-operator-token':
                    return self.reply(403, {})
                if self.command == 'POST' and p == '/clients/mm-id/roles':
                    data = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                    s['roles'].append(dict(data, id='admin-role-id', containerId='mm-id'))
                    return self.reply(503 if s['lost_role'] else 201)
                if self.command == 'POST' and p == '/clients/mm-id/scope-mappings/clients/mm-id':
                    s['scope_roles'] = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                    return self.reply(204)
                if self.command in ['POST', 'DELETE'] and p.startswith('/users/') and p.endswith('/role-mappings/clients/mm-id'):
                    u = p.split('/')[2]
                    data = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                    s['members'][u] = data if self.command == 'POST' else []
                    return self.reply(204)
                if self.command == 'PUT' and p == '/clients/mm-id':
                    data = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                    if set(data) not in ({'enabled'}, {'enabled','webOrigins'}):
                        return self.reply(400, {})
                    s['toggle_bodies'].append(copy.deepcopy(data))
                    # Keycloak 26.8.1 RepresentationToModel: omitted empty origins
                    # are defaulted from redirect URI origins during an update.
                    if 'webOrigins' not in data and not s['client']['webOrigins']:
                        s['client']['webOrigins'] = sorted({urlsplit(u).scheme + '://' + urlsplit(u).netloc
                                                           for u in s['client']['redirectUris']})
                    s['client'].update(data)
                    return self.reply(503 if s['lost_enable'] else 204)
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
        self.v = dict(mattermost_client_run=True, mattermost_recovery_verified=True,
                      mattermost_sso_origin='https://mattermost.example.test',
                      mattermost_sso_issuer=f'https://localhost:{self.server.server_port}/auth/realms/perkforge',
                      mattermost_operator_token_file=str(self.d / 'token'),
                      mattermost_client_secret_file=str(self.d / 'secret'), mattermost_ca_file=str(self.d / 'ca'))

    def run_play(self, op='prepare', extra=None, success=True, check=False):
        v = dict(self.v, mattermost_client_operation=op, mattermost_client_approval=f'mattermost-client-{op}-v1')
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
        self.s['client'] = json.loads((SSO / 'mattermost/client.json').read_text())
        self.s['client'].update(id='mm-id', redirectUris=['https://mattermost.example.test/signup/openid/complete'])

    def test_default_check_and_approval_never_contact(self):
        self.run_play(extra={'mattermost_client_run': False, 'mattermost_operator_token_file': '/missing'})
        self.run_play(check=True, extra={'mattermost_operator_token_file': '/missing'})
        self.run_play(extra={'mattermost_client_approval': 'UNAPPROVED'}, success=False)
        self.run_play('activate', success=False)
        self.assertEqual(self.s['calls'], [])

    def test_prepare_repeat_inspect_and_secret_mismatch(self):
        self.run_play()
        self.assertFalse(self.s['client']['enabled'])
        self.assertIn('changed=0', self.run_play().stdout)
        self.run_play('inspect', extra={'mattermost_client_secret_file': '/missing'})
        self.assertEqual(self.s['writes'], [('POST', '/clients')])
        self.s['secret'] = 'different-secret'
        self.run_play(success=False)
        self.assertEqual(self.s['writes'], [('POST', '/clients')])

    def test_drift_and_unexpected_scope_refuse_without_mutation(self):
        self.seed()
        original = copy.deepcopy(self.s['client'])
        for changes in [dict(publicClient=True), dict(fullScopeAllowed=True), dict(attributes={}),
                        dict(webOrigins=['*']), dict(authenticationFlowBindingOverrides={'browser':'foreign'})]:
            self.s['client'] = dict(copy.deepcopy(original), **changes)
            self.run_play(success=False)
        self.s['client'] = original
        for field,value in [('roles',[{'name':'admin'}]),('scope',{'clientMappings':{'mattermost':{}}}),
                            ('optional',[{'name':'roles'}])]:
            old = self.s[field]; self.s[field] = value
            self.run_play('inspect', success=False); self.s[field] = old
        self.assertEqual(self.s['writes'], [])

    def test_activate_and_rollback_only_enabled_flag_preserving_secret(self):
        self.seed()
        before = copy.deepcopy(self.s['client'])
        gates = dict(mattermost_native_ready=True, mattermost_edition_verified=True, mattermost_linking_verified=True)
        self.run_play('activate', extra=gates)
        self.assertEqual(self.s['client'], dict(before, enabled=True))
        self.assertEqual(self.s['toggle_bodies'], [{'enabled':True,'webOrigins':[]}])
        self.assertIn('changed=0', self.run_play('activate', extra=gates).stdout)
        self.run_play('rollback')
        self.assertEqual(self.s['client'], before)
        self.assertEqual(self.s['secret'], 'fixture-existing-client-secret')

    def test_interrupted_create_resumes_without_duplicate(self):
        self.s['lost_create'] = True
        self.run_play(success=False)
        self.s['lost_create'] = False
        self.run_play()
        self.assertEqual(self.s['writes'], [('POST', '/clients')])

    def test_scope_drift_and_private_file_permissions_block(self):
        self.s['mappers']['profile'].append(dict(name='groups', protocol='openid-connect',protocolMapper='oidc-group-membership-mapper',config={}))
        self.run_play(success=False)
        self.assertEqual(self.s['writes'], [])
        self.d.chmod(0o755)
        self.run_play(success=False)
        self.assertEqual(self.s['writes'], [])
