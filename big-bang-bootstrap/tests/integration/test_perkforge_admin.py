"""Actual Ansible, isolated synthetic HTTPS; never proof of live authorization."""
import copy
import json
import os
from pathlib import Path
import shutil
import ssl
import subprocess
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[2]
PLAY = ROOT / 'configuration/authorization/administer-perkforge.yaml'
INV = ROOT / 'configuration/ansible/inventory.yaml'
NAMES = ['realm-admin']
CHILDREN = ['create-client', 'impersonation', 'manage-authorization', 'manage-clients', 'manage-events', 'manage-identity-providers', 'manage-organizations', 'manage-realm', 'manage-users', 'query-clients', 'query-groups', 'query-organizations', 'query-realms', 'query-users', 'view-authorization', 'view-clients', 'view-events', 'view-identity-providers', 'view-organizations', 'view-realm', 'view-users']


class AdminDefaults(unittest.TestCase):
    def test_defaults_check_mode_and_unapproved_apply_make_no_connections(self):
        with tempfile.TemporaryDirectory() as d:
            for extra, check, success in [({}, False, True), ({'perkforge_admin_apply': True}, True, True),
                                          ({'perkforge_admin_apply': True}, False, False)]:
                result = subprocess.run(['ansible-playbook', '-i', str(INV), str(PLAY), '-e', json.dumps(extra)]
                                        + (['--check'] if check else []), capture_output=True, text=True,
                                        env={**os.environ, 'ANSIBLE_LOCAL_TEMP': d + '/local'}, timeout=40)
                self.assertEqual(result.returncode == 0, success, result.stdout + result.stderr)
                if success:
                    self.assertIn('changed=0', result.stdout)


@unittest.skipUnless(os.environ.get('RUN_PLATFORM_CONFIG_TESTS') and shutil.which('ansible-playbook'),
                     'enable isolated HTTPS fixtures explicitly')
class AdminAPI(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.d = Path(temporary.name)
        subprocess.run(['openssl', 'req', '-x509', '-newkey', 'rsa:2048', '-nodes', '-days', '1',
                        '-subj', '/CN=localhost', '-addext', 'subjectAltName=DNS:localhost',
                        '-keyout', str(self.d / 'key'), '-out', str(self.d / 'ca')], check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self.roles = {name: {'name': name, 'id': 'role-' + name, 'clientRole': True,
                             'containerId': 'management-id', 'composite': name == 'realm-admin'} for name in NAMES + CHILDREN}
        parent = {'id': 'parent-id', 'name': 'platform', 'path': '/platform',
                  'attributes': {'perkforge-managed': ['true'], 'perkforge-foundation': ['v1']}}
        leaf = {'id': 'admin-id', 'name': 'admins', 'path': '/platform/admins',
                'attributes': {**parent['attributes'], 'perkforge-role': ['platform-admin']}}
        self.s = {'parent': parent, 'leaf': leaf, 'realm': {'realm': 'perkforge', 'enabled': True,
                  'attributes': {'perkforge-managed': 'true', 'perkforge-purpose': 'realm-foundation-v1'}},
                  'parentMappings': {}, 'otherClients': {}, 'realmMappings': [], 'mapped': [],
                  'defaults': [], 'children': [], 'tokenDeny': False, 'clients': [{'clientId': 'realm-management', 'id': 'management-id'}],
                  'compositeRoles': [copy.deepcopy(self.roles[name]) for name in CHILDREN],
                  'writes': [], 'calls': [], 'deny': False, 'failAfterWrite': False}
        state, roles = self.s, self.roles
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass
            def respond(self, code, value=None):
                data = json.dumps(value).encode() if value is not None else b''
                self.send_response(code)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(data)
            def do_GET(self):
                path = urlsplit(self.path).path
                state['calls'].append(('GET', path))
                if state['deny']:
                    return self.respond(403, {})
                api = '/auth/admin/realms/perkforge'
                if path == api:
                    return self.respond(200, state['realm'])
                if path == api + '/group-by-path/platform':
                    return self.respond(200, state['parent'])
                if path == api + '/group-by-path/platform/admins':
                    return self.respond(200, state['leaf'])
                if path == api + '/default-groups':
                    return self.respond(200, state['defaults'])
                if path == api + '/groups/admin-id/children':
                    return self.respond(200, state['children'])
                if path == api + '/clients':
                    return self.respond(200, state['clients'])
                if path == api + '/clients/management-id/roles/realm-admin/composites':
                    return self.respond(200, state['compositeRoles'])
                if '/clients/management-id/roles/' in path:
                    return self.respond(200, roles[path.rsplit('/', 1)[1]])
                if path == api + '/groups/parent-id/role-mappings':
                    return self.respond(200, state['parentMappings'])
                if path == api + '/groups/admin-id/role-mappings':
                    clients = copy.deepcopy(state['otherClients'])
                    if state['mapped']:
                        clients['realm-management'] = {'id': 'management-id', 'client': 'realm-management',
                                                      'mappings': state['mapped']}
                    return self.respond(200, {'realmMappings': state['realmMappings'], 'clientMappings': clients})
                if path.startswith(api + '/groups/admin-id/role-mappings/clients/management-id'):
                    effective = state['mapped'] + (state['compositeRoles'] if any(r['name'] == 'realm-admin' for r in state['mapped']) else [])
                    return self.respond(200, effective if path.endswith('/composite') else state['mapped'])
                return self.respond(404, {})
            def do_POST(self):
                path = urlsplit(self.path).path
                body = self.rfile.read(int(self.headers.get('Content-Length', 0)))
                state['calls'].append(('POST', path))
                if path == '/auth/realms/master/protocol/openid-connect/token':
                    return self.respond(401, {}) if state['tokenDeny'] else self.respond(200, {'access_token': 'synthetic-admin-session'})
                expected = '/auth/admin/realms/perkforge/groups/admin-id/role-mappings/clients/management-id'
                if path != expected:
                    return self.respond(403, {})
                values = json.loads(body)
                state['writes'].append((path, copy.deepcopy(values)))
                state['mapped'].extend(copy.deepcopy(values))
                return self.respond(500 if state['failAfterWrite'] else 204)
            def do_PUT(self):
                raise AssertionError('No replacement writes permitted')
            def do_DELETE(self):
                raise AssertionError('No deletion permitted')
        self.server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(str(self.d / 'ca'), str(self.d / 'key'))
        self.server.socket = context.wrap_socket(self.server.socket, server_side=True)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)
        for name in ('username', 'password'):
            (self.d / name).write_text('synthetic-private-' + name)
            (self.d / name).chmod(0o600)
        binary = self.d / 'bin'
        binary.mkdir()
        kubectl = binary / 'kubectl'
        kubectl.write_text('#!/bin/sh\nprintf synthetic-cluster-uid\n')
        kubectl.chmod(0o700)
        self.vars = {'perkforge_admin_apply': True, 'perkforge_admin_scope': 'perkforge-full-realm-admin-v1',
                     'perkforge_admin_recovery_preserved': True, 'perkforge_admin_group_id': 'admin-id',
                     'perkforge_admin_parent_id': 'parent-id',
                     'perkforge_admin_url': f'https://localhost:{self.server.server_port}/auth',
                     'perkforge_admin_ca': str(self.d / 'ca'),
                     'perkforge_admin_username_file': str(self.d / 'username'),
                     'perkforge_admin_password_file': str(self.d / 'password'),
                     'expected_cluster_uid': 'synthetic-cluster-uid', 'target_context': 'fixture',
                     'target_kubeconfig': str(self.d / 'not-a-kubeconfig')}

    def run_play(self, **extra):
        result = subprocess.run(['ansible-playbook', '-i', str(INV), str(PLAY), '-e',
                                 json.dumps({**self.vars, **extra})], capture_output=True, text=True,
                                env={**os.environ, 'PATH': str(self.d / 'bin') + ':' + os.environ['PATH'],
                                     'ANSIBLE_LOCAL_TEMP': str(self.d / 'local'), 'ANSIBLE_NOCOLOR': '1'}, timeout=150)
        for marker in ('synthetic-private-username', 'synthetic-private-password', 'synthetic-admin-session'):
            self.assertNotIn(marker, result.stdout + result.stderr)
        return result

    def test_exact_grant_second_run_and_read_only_inspection(self):
        result = self.run_play()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(len(self.s['writes']), 1)
        self.assertEqual({r['name'] for r in self.s['mapped']}, set(NAMES))
        self.assertTrue(self.s['mapped'][0]['composite'])
        self.assertEqual({r['name'] for r in self.s['compositeRoles']}, set(CHILDREN))
        self.assertIn('impersonation', CHILDREN)
        self.assertIn('manage-realm', CHILDREN)
        before = copy.deepcopy(self.s['writes'])
        for extra in ({}, {'perkforge_admin_apply': False, 'perkforge_admin_inspect': True}):
            result = self.run_play(**extra)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn('changed=0', result.stdout)
            self.assertEqual(self.s['writes'], before)
        self.assertFalse(any('/users' in path or '/authentication' in path for _, path in self.s['calls']))
        self.assertFalse(any('/admin/realms/master' in path for _, path in self.s['calls']))

    def test_uncertain_composite_grant_is_not_duplicated_on_resume(self):
        self.s['failAfterWrite'] = True
        self.assertNotEqual(self.run_play().returncode, 0)
        self.assertEqual(len(self.s['writes'][0][1]), 1)
        self.s['failAfterWrite'] = False
        result = self.run_play()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(len(self.s['writes']), 1)

    def test_refuse_unowned_replaced_defaults_and_parent_privilege(self):
        baseline = copy.deepcopy(self.s)
        for field, value in [('realm', {**baseline['realm'], 'attributes': {}}),
                             ('leaf', {**baseline['leaf'], 'id': 'replacement'}),
                             ('defaults', [baseline['leaf']]),
                             ('children', [{'id': 'nested'}]),
                             ('parentMappings', {'realmMappings': [{'name': 'unexpected'}]})]:
            with self.subTest(field=field):
                self.s.update(copy.deepcopy(baseline))
                self.s[field] = value
                self.assertNotEqual(self.run_play().returncode, 0)
                self.assertEqual(self.s['writes'], [])

    def test_refuse_direct_child_roles_other_clients_and_wrong_composite_id(self):
        for name in ('realm-admin', 'impersonation', 'manage-realm'):
            self.s['mapped'] = [{'name': name, 'id': 'unexpected', 'clientRole': True,
                                 'containerId': 'management-id', 'composite': name == 'realm-admin'}]
            self.assertNotEqual(self.run_play().returncode, 0)
            self.assertEqual(self.s['writes'], [])
        self.s['mapped'] = []
        self.s['otherClients'] = {'other-app': {'mappings': []}}
        self.assertNotEqual(self.run_play().returncode, 0)
        self.s['otherClients'] = {}
        self.roles['realm-admin']['composite'] = False
        self.assertNotEqual(self.run_play().returncode, 0)
        self.assertEqual(self.s['writes'], [])

    def test_refuse_cross_realm_cross_client_or_drifted_composite_expansion(self):
        baseline = copy.deepcopy(self.s['compositeRoles'])
        for change in ('cross-client', 'realm-role', 'nested-composite', 'extra-role', 'missing-role'):
            with self.subTest(change=change):
                self.s['compositeRoles'] = copy.deepcopy(baseline)
                if change == 'cross-client':
                    self.s['compositeRoles'][0]['containerId'] = 'master-other-realm'
                elif change == 'realm-role':
                    self.s['compositeRoles'][0]['clientRole'] = False
                elif change == 'nested-composite':
                    self.s['compositeRoles'][0]['composite'] = True
                elif change == 'extra-role':
                    self.s['compositeRoles'].append({**baseline[0], 'name': 'unexpected'})
                else:
                    self.s['compositeRoles'].pop()
                self.assertNotEqual(self.run_play().returncode, 0)
                self.assertEqual(self.s['writes'], [])

    def test_target_scope_auth_and_file_permissions_refuse_before_writes(self):
        for extra in ({'expected_cluster_uid': 'wrong'}, {'perkforge_admin_scope': 'realm-admin'},
                      {'perkforge_admin_recovery_preserved': False}):
            self.assertNotEqual(self.run_play(**extra).returncode, 0)
            self.assertEqual(self.s['writes'], [])
        self.s['tokenDeny'] = True
        self.assertNotEqual(self.run_play().returncode, 0)
        self.s['tokenDeny'] = False
        self.s['deny'] = True
        self.assertNotEqual(self.run_play().returncode, 0)
        self.s['deny'] = False
        (self.d / 'password').chmod(0o644)
        self.assertNotEqual(self.run_play().returncode, 0)
        self.assertEqual(self.s['writes'], [])

    def test_untrusted_tls_refuses_without_role_writes(self):
        subprocess.run(['openssl', 'req', '-x509', '-newkey', 'rsa:2048', '-nodes', '-days', '1',
                        '-subj', '/CN=wrong', '-keyout', str(self.d / 'wrong-key'),
                        '-out', str(self.d / 'wrong-ca')], check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self.assertNotEqual(self.run_play(perkforge_admin_ca=str(self.d / 'wrong-ca')).returncode, 0)
        self.assertEqual(self.s['writes'], [])


if __name__ == '__main__':
    unittest.main()

