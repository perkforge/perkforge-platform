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
                    return self.reply(200, s['scope'] or ({'clientMappings': {'grafana': {'id': 'gf-id', 'client': 'grafana', 'mappings': s['scope_roles']}}} if s['scope_roles'] else {}))
                if p == '/clients/gf-id/scope-mappings/clients/gf-id':
                    return self.reply(200, s['scope_roles'])
                if p == '/clients/gf-id/roles/%2Fplatform%2Fadmins/groups':
                    return self.reply(200, s['groups'])
                if p == '/clients/gf-id/roles/%2Fplatform%2Fadmins/users':
                    return self.reply(200, [dict(id=u) for u,r in s['members'].items() if r] + s['extra_members'])
                if p.startswith('/users/'):
                    u = p.split('/')[2]
                    if p == '/users/' + u:
                        return self.reply(200, s['users'].get(u, dict(id=u, enabled=True)))
                    if p.endswith('/role-mappings/clients/gf-id'):
                        return self.reply(200, s['members'].get(u, []))
                    if p.endswith('/role-mappings/clients/gf-id/composite'):
                        return self.reply(200, s['members'].get(u, []) + s['inherited'].get(u, []))
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
                if self.headers.get('Authorization') != 'Bearer fixture-operator-token':
                    return self.reply(403, {})
                if self.command == 'POST' and p == '/clients/gf-id/roles':
                    data = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                    s['roles'].append(dict(data, id='admin-role-id', containerId='gf-id'))
                    return self.reply(503 if s['lost_role'] else 201)
                if self.command == 'POST' and p == '/clients/gf-id/scope-mappings/clients/gf-id':
                    s['scope_roles'] = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                    return self.reply(204)
                if self.command in ['POST', 'DELETE'] and p.startswith('/users/') and p.endswith('/role-mappings/clients/gf-id'):
                    u = p.split('/')[2]
                    data = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                    s['members'][u] = data if self.command == 'POST' else []
                    return self.reply(204)
                if self.command == 'PUT' and p == '/clients/gf-id':
                    data = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                    if set(data) != {'enabled'}:
                        return self.reply(400, {})
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
        for op in ['configure','members','rollback']:
            self.run_play(op, extra={'grafana_client_approval': 'UNAPPROVED'}, success=False)
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


class GrafanaActivation(unittest.TestCase):
    setUp = GrafanaClient.setUp
    run_play = GrafanaClient.run_play
    seed = GrafanaClient.seed
    # Keep lifecycle-specific cases separate without repeating inherited tests.
    def configured(self):
        self.seed()
        self.role = dict(name='/platform/admins', description='grafana-explicit-admin-only-v1',
                         composite=False, clientRole=True, containerId='gf-id', id='admin-role-id')
        self.s['roles'] = [copy.deepcopy(self.role)]
        self.s['scope_roles'] = [copy.deepcopy(self.role)]
        self.admin = '11111111-1111-1111-1111-111111111111'
        self.other = '22222222-2222-2222-2222-222222222222'
        self.policy = dict(grafana_role_policy_approval='grafana-explicit-admin-only-v1',
                           grafana_native_ready=True,
                           grafana_subjects=[dict(sub=self.admin, role='admin')])

    def test_configure_repeat_and_interrupted_role_resume(self):
        self.seed()
        policy = {'grafana_role_policy_approval': 'grafana-explicit-admin-only-v1'}
        self.s['lost_role'] = True
        self.run_play('configure', extra=policy, success=False)
        self.assertEqual(len(self.s['roles']), 1)
        self.assertFalse(self.s['client']['enabled'])
        self.s['lost_role'] = False
        self.run_play('configure', extra=policy)
        self.assertIn('changed=0', self.run_play('configure', extra=policy).stdout)
        self.assertEqual(self.s['writes'], [('POST','/clients/gf-id/roles'),
                                          ('POST','/clients/gf-id/scope-mappings/clients/gf-id')])
        self.s['calls'].clear()
        self.run_play('inspect', extra={'grafana_client_secret_file': '/nonexistent'})
        self.assertNotIn(('GET','/clients/gf-id/client-secret'), self.s['calls'])

    def test_configuration_and_activation_gates_never_write(self):
        self.configured()
        self.run_play('configure', success=False)
        self.run_play('activate', extra=self.policy | {'grafana_native_ready': False}, success=False)
        self.run_play('activate', extra=self.policy | {'grafana_subjects': []}, success=False)
        for role in ['viewer','engineer','tenant','owner']:
            self.run_play('members', extra=self.policy | {'grafana_subjects':[dict(sub=self.admin,role=role)]}, success=False)
        self.assertEqual(self.s['writes'], [])

    def test_members_activate_rollback_and_repeat_preserve_client(self):
        self.configured()
        before = copy.deepcopy(self.s['client'])
        self.run_play('activate', extra=self.policy, success=False)
        self.run_play('members', extra=self.policy)
        self.assertIn('changed=0', self.run_play('members', extra=self.policy).stdout)
        self.run_play('activate', extra=self.policy)
        self.assertEqual(self.s['client'], before | {'enabled':True})
        self.assertIn('changed=0', self.run_play('activate', extra=self.policy).stdout)
        self.run_play('rollback', extra={'grafana_client_secret_file':'/nonexistent'})
        self.assertEqual(self.s['client'], before)
        self.assertEqual(self.s['members'][self.admin], [self.role])
        self.assertIn('changed=0', self.run_play('rollback').stdout)
        self.assertEqual(self.s['writes'], [('POST',f'/users/{self.admin}/role-mappings/clients/gf-id'),
                                          ('PUT','/clients/gf-id'),('PUT','/clients/gf-id')])
        self.assertNotIn(('GET','/clients/gf-id/client-secret'), self.s['calls'])

    def test_unreviewed_or_inherited_grants_block_before_writes(self):
        self.configured()
        self.s['members'][self.admin] = [self.role]
        for field, value in [('groups',[dict(id='foreign-group')]),
                             ('extra_members',[dict(id=self.other)]),
                             ('inherited',{self.admin:[dict(id='foreign-role')]}),
                             ('users',{self.admin:dict(id=self.admin,enabled=False)})]:
            previous = copy.deepcopy(self.s[field])
            self.s[field] = value
            self.run_play('activate', extra=self.policy, success=False)
            self.run_play('members', extra=self.policy, success=False)
            self.s[field] = previous
        self.assertEqual(self.s['writes'], [])

    def test_all_recipients_preflight_before_any_grant(self):
        self.configured()
        self.s['users'][self.other] = dict(id=self.other, enabled=False)
        self.run_play('members', extra=self.policy | {'grafana_subjects':[
            dict(sub=self.admin,role='admin'),dict(sub=self.other,role='admin')]}, success=False)
        self.assertEqual(self.s['writes'], [])

    def test_offboarding_requires_native_session_and_admin_revocation(self):
        self.configured()
        self.s['members'][self.admin] = [self.role]
        policy = self.policy | {'grafana_subjects':[dict(sub=self.admin,role='absent')]}
        self.run_play('members', extra=policy, success=False)
        self.assertEqual(self.s['writes'], [])
        policy['grafana_native_revoked_subjects'] = [self.admin]
        self.run_play('members', extra=policy)
        self.assertEqual(self.s['members'][self.admin], [])
        self.assertIn('changed=0', self.run_play('members', extra=policy).stdout)
        self.assertEqual(self.s['writes'], [('DELETE',f'/users/{self.admin}/role-mappings/clients/gf-id')])

    def test_lost_activation_reply_inspect_then_repeat_does_not_rewrite(self):
        self.configured()
        self.s['members'][self.admin] = [self.role]
        self.s['lost_enable'] = True
        self.run_play('activate', extra=self.policy, success=False)
        self.assertTrue(self.s['client']['enabled'])
        self.s['lost_enable'] = False
        self.run_play('inspect')
        self.assertIn('changed=0', self.run_play('activate', extra=self.policy).stdout)
        self.assertEqual(self.s['writes'], [('PUT','/clients/gf-id')])

    def test_foreign_role_scope_or_client_drift_blocks_rollback(self):
        self.configured()
        self.s['client']['enabled'] = True
        self.s['roles'][0]['description'] = 'foreign'
        self.run_play('rollback', success=False)
        self.assertTrue(self.s['client']['enabled'])
        self.assertEqual(self.s['writes'], [])
