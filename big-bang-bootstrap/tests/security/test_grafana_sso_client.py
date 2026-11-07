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
PLAY = SSO / 'grafana/reconcile-client.yaml'


class GrafanaClient(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.d = Path(self.tmp.name)
        subprocess.run(['openssl', 'req', '-x509', '-newkey', 'rsa:2048', '-nodes', '-days', '1',
                        '-subj', '/CN=localhost', '-addext', 'subjectAltName=DNS:localhost',
                        '-keyout', str(self.d / 'key'), '-out', str(self.d / 'ca')],
                       check=True, capture_output=True)
        self.s = dict(client=None, calls=[], writes=[], roles=[], scope={}, optional=[],
                      scopes=['basic', 'profile', 'email'], lost_create=False, secret='fixture-existing-client-secret')
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
                    return self.reply(200, [] if s['client'] is None else [dict(id=s.get('lookup_id', 'gf-id'), clientId='grafana')])
                if p == '/clients/gf-id':
                    return self.reply(200, s['client'])
                if p == '/clients/gf-id/default-client-scopes':
                    return self.reply(200, [dict(id=n, name=n) for n in s['scopes']])
                if p == '/clients/gf-id/optional-client-scopes':
                    return self.reply(200, s['optional'])
                if p == '/clients/gf-id/protocol-mappers/models':
                    return self.reply(200, s['client']['protocolMappers'])
                if p == '/clients/gf-id/scope-mappings':
                    return self.reply(200, s['scope'])
                if p == '/clients/gf-id/roles':
                    return self.reply(200, s['roles'])
                if p == '/clients/gf-id/client-secret':
                    return self.reply(200, dict(value=s['secret']))
                return self.reply(404, {})

            def mutate(self):
                p = urlsplit(self.path).path.removeprefix('/auth/admin/realms/perkforge')
                s['writes'].append((self.command, p))
                if self.command == 'POST' and p == '/clients':
                    data = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                    s['secret'] = data.pop('secret')
                    s['client'] = dict(data, id='gf-id')
                    return self.reply(503 if s['lost_create'] else 201)
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
        self.v = dict(grafana_client_run=True, grafana_recovery_verified=True,
                      grafana_sso_origin='https://grafana.example.test',
                      grafana_sso_issuer=f'https://localhost:{self.server.server_port}/auth/realms/perkforge',
                      grafana_operator_token_file=str(self.d / 'token'),
                      grafana_client_secret_file=str(self.d / 'secret'), grafana_ca_file=str(self.d / 'ca'))

    def run_play(self, op='prepare', extra=None, success=True, check=False):
        v = dict(self.v, grafana_client_operation=op, grafana_client_approval=f'grafana-client-{op}-v1')
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
        self.s['client'] = json.loads((SSO / 'grafana/client.json').read_text())
        self.s['client'].update(id='gf-id', redirectUris=['https://grafana.example.test/login/generic_oauth'])

    def test_default_check_and_approval_never_contact(self):
        self.run_play(extra={'grafana_client_run': False, 'grafana_operator_token_file': '/nonexistent'})
        self.run_play(check=True, extra={'grafana_operator_token_file': '/nonexistent'})
        for extra in [dict(grafana_client_approval='UNAPPROVED'), dict(grafana_recovery_verified=False),
                      dict(grafana_sso_origin='https://grafana.EXAMPLE.INVALID:443'),
                      dict(grafana_sso_origin="https://grafana.example.test\n"),
                      dict(grafana_sso_origin='https://localhost:' + str(self.server.server_port)),
                      dict(grafana_sso_issuer='https://localhost:65536/realms/perkforge')]:
            self.run_play(extra=extra, success=False)
        self.run_play('activate', success=False)
        self.assertEqual(self.s['calls'], [])
        self.assertEqual(self.s['writes'], [])

    def test_prepare_repeat_and_metadata_inspect(self):
        self.run_play()
        self.assertFalse(self.s['client']['enabled'])
        self.assertIn('changed=0', self.run_play().stdout)
        self.s['calls'].clear()
        self.run_play('inspect', extra={'grafana_client_secret_file': '/nonexistent'})
        self.assertNotIn(('GET', '/clients/gf-id/client-secret'), self.s['calls'])
        self.assertEqual(self.s['writes'], [('POST', '/clients')])

    def test_missing_inspect_and_interrupted_create(self):
        self.run_play('inspect', success=False)
        self.assertEqual(self.s['writes'], [])
        self.s['lost_create'] = True
        self.run_play(success=False)
        self.assertFalse(self.s['client']['enabled'])
        self.s['lost_create'] = False
        self.assertIn('changed=0', self.run_play().stdout)
        self.assertEqual(self.s['writes'], [('POST', '/clients')])

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
        self.s["lookup_id"] = "gf-id\n"
        self.run_play("inspect", success=False)
        self.assertNotIn(("GET", "/clients/gf-id"), self.s["calls"])
        self.assertEqual(self.s["writes"], [])

    def test_scope_and_role_drift_never_mutate(self):
        self.seed()
        for field, value in [('roles', [{'name': '/platform/admins'}]), ('optional', [{'name': 'roles'}]),
                             ('scopes', ['basic']), ('scope', {'realmMappings': [{'name': 'admin'}]}),
                             ('scope', {'clientMappings': {'grafana': {}}})]:
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
