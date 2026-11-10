"""Actual Ansible against synthetic HTTPS, never real credentials or cluster APIs.
Release publication is mocked in the copied fixture tree; source assertions retain
that gate. This is not live release, Kubernetes JWT login or ESO sync acceptance.
"""
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
import yaml

ROOT = Path(__file__).resolve().parents[2]
PLAY = ROOT/'configuration/ansible/openbao-eso.yaml'
SOURCE = ROOT/'configuration/external-secrets/openbao'
NAMES = ['eso-platform', 'eso-tenant-portal']


class SourceGuards(unittest.TestCase):
    def test_release_and_clean_checkout_before_private_block(self):
        play = yaml.safe_load(PLAY.read_text())[0]
        block = play['tasks'][1]['block']
        self.assertEqual(block[1]['ansible.builtin.include_tasks'], 'verify-release.yaml')
        self.assertEqual(block[2]['ansible.builtin.command']['argv'][-2:], ['rev-parse', 'HEAD'])
        self.assertEqual(block[3]['ansible.builtin.command']['argv'][-2:], ['status', '--porcelain'])
        self.assertIn('eso_checkout.stdout == config_release.resolvedCommit', block[4]['ansible.builtin.assert']['that'])
        self.assertIn('eso_changes.stdout | length == 0', block[4]['ansible.builtin.assert']['that'])
        self.assertTrue(block[5]['no_log'])
        self.assertEqual(play['module_defaults']['ansible.builtin.uri']['follow_redirects'], 'none')
        self.assertFalse(play['module_defaults']['ansible.builtin.uri']['use_proxy'])
        self.assertFalse(play['module_defaults']['ansible.builtin.uri']['use_netrc'])


@unittest.skipUnless(os.environ.get('RUN_PLATFORM_CONFIG_TESTS') == '1' and shutil.which('ansible-playbook'),
                     'explicit opt-in to isolated actual Ansible HTTPS fixture')
class HTTPSAdapter(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix='eso-auth-fixture-')
        self.addCleanup(temp.cleanup)
        self.d = Path(temp.name)
        self.play = self.d/'big-bang-bootstrap/configuration/ansible/openbao-eso.yaml'
        self.play.parent.mkdir(parents=True)
        shutil.copy(PLAY, self.play)
        shutil.copytree(SOURCE, self.play.parent.parent/'external-secrets/openbao')
        # Explicit test-only replacement, not a production bypass switch.
        (self.play.parent/'verify-release.yaml').write_text('- ansible.builtin.set_fact:\n    config_release: {resolvedCommit: "'+'a'*40+'"}\n')
        bins = self.d/'bin'; bins.mkdir()
        git = bins/'git'
        git.write_text('#!/bin/sh\ncase "$*" in *"rev-parse HEAD") echo "${FIXTURE_HEAD:-'+ 'a'*40+'}";; *"status --porcelain") printf \'%s\' "${FIXTURE_DIRTY:-}";; *) exit 91;; esac\n')
        git.chmod(0o700)
        self.env = {**os.environ, 'PATH': str(bins)+':'+os.environ['PATH'],
                    'ANSIBLE_LOCAL_TEMP': str(self.d/'local'), 'ANSIBLE_REMOTE_TEMP': str(self.d/'remote'),
                    'ANSIBLE_NOCOLOR': '1', 'KUBECONFIG': '/dev/null'}
        self.inventory = self.d/'inventory.yaml'
        self.inventory.write_text('all:\n  children:\n    bootstrap_clusters:\n      hosts:\n        local:\n          deployment_environment: local\n          impact_profile: il2\n')
        subprocess.run(['openssl', 'req', '-x509', '-newkey', 'rsa:2048', '-nodes', '-days', '1',
                        '-subj', '/CN=localhost', '-addext', 'subjectAltName=DNS:localhost',
                        '-keyout', str(self.d/'key'), '-out', str(self.d/'ca')],
                       check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self.s = {'cluster': 'fixture-cluster', 'version': '2.7.2', 'mount': None, 'config': None,
                  'policies': {}, 'roles': {}, 'writes': [], 'calls': [], 'deny': '',
                  'kv': {'platform/': {'type': 'kv', 'options': {'version': '2'}},
                         'tenants/': {'type': 'kv', 'options': {'version': '2'}}},
                  'aliases': {}, 'entities': {}, 'groups': {}, 'extra_roles': [],
                  'foreign': {'kubernetes/': {'type': 'kubernetes', 'accessor': 'legacy'},
                              'oidc/': {'type': 'oidc', 'accessor': 'human'}}}
        state = self.s
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args): pass
            def respond(self, code, data=None):
                self.send_response(code); self.send_header('Content-Type', 'application/json'); self.end_headers()
                if data is not None: self.wfile.write(json.dumps(data).encode())
            def do_GET(self):
                path = urlsplit(self.path).path
                bearer = self.headers.get('X-Vault-Token')
                state['calls'].append(('GET', path, bool(bearer)))
                if path == '/v1/sys/health':
                    return self.respond(200, {'cluster_id': state['cluster'], 'version': state['version'], 'initialized': True, 'sealed': False, 'standby': False})
                if bearer != 'synthetic-eso-operator-only': return self.respond(403)
                value = None
                if path == '/v1/sys/auth': value = {**state['foreign'], **({'kubernetes-eso/': state['mount']} if state['mount'] else {})}
                elif path == '/v1/sys/mounts': value = state['kv']
                elif path == '/v1/auth/kubernetes-eso/config': value = state['config']
                elif path == '/v1/auth/kubernetes-eso/role':
                    keys = list(state['roles']) + state['extra_roles']
                    value = {'keys': keys} if keys else None
                elif path.startswith('/v1/auth/kubernetes-eso/role/'): value = state['roles'].get(path.rsplit('/', 1)[1])
                elif path.startswith('/v1/sys/policies/acl/'): value = state['policies'].get(path.rsplit('/', 1)[1])
                elif path == '/v1/identity/entity-alias/id': value = {'keys': list(state['aliases'])} if state['aliases'] else None
                elif path.startswith('/v1/identity/entity-alias/id/'): value = state['aliases'].get(path.rsplit('/', 1)[1])
                elif path.startswith('/v1/identity/entity/id/'): value = state['entities'].get(path.rsplit('/', 1)[1])
                elif path == '/v1/identity/group-alias/id': value = {'keys': list(state['groups'])} if state['groups'] else None
                elif path.startswith('/v1/identity/group-alias/id/'): value = state['groups'].get(path.rsplit('/', 1)[1])
                else: return self.respond(400, {'errors': ['unexpected fixture read']})
                return self.respond(200, {'data': value}) if value is not None else self.respond(404, {'errors': []})
            def write(self):
                path = urlsplit(self.path).path
                if self.headers.get('X-Vault-Token') != 'synthetic-eso-operator-only': return self.respond(403)
                if state['deny'] == path: return self.respond(403)
                body = json.loads(self.rfile.read(int(self.headers.get('Content-Length', 0))))
                if path == '/v1/sys/auth/kubernetes-eso':
                    if state['mount'] is not None: return self.respond(409)
                    state['mount'] = {**body, 'accessor': 'fixture-eso-accessor'}
                elif path == '/v1/auth/kubernetes-eso/config':
                    if state['config'] is not None: return self.respond(409)
                    state['config'] = {**body, 'kubernetes_ca_cert': '', 'pem_keys': [], 'issuer': '', 'disable_iss_validation': True, 'token_reviewer_jwt_set': False}
                elif path.startswith('/v1/sys/policies/acl/'):
                    name = path.rsplit('/', 1)[1]
                    if name in state['policies']: return self.respond(409)
                    state['policies'][name] = body
                elif path.startswith('/v1/auth/kubernetes-eso/role/'):
                    name = path.rsplit('/', 1)[1]
                    if name in state['roles']: return self.respond(409)
                    state['roles'][name] = {**body, 'alias_name_source': 'serviceaccount_uid',
                                            'bound_service_account_namespace_selector': '', 'token_bound_cidrs': [],
                                            'token_num_uses': 0, 'token_period': 0, 'token_type': 'default', 'token_strictly_bind_ip': False}
                else: return self.respond(400, {'errors': ['unexpected fixture write']})
                state['calls'].append((self.command, path, True))
                state['writes'].append((self.command, path))
                self.respond(204)
            do_POST = write
            do_PUT = write
        server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ctx.load_cert_chain(str(self.d/'ca'), str(self.d/'key'))
        server.socket = ctx.wrap_socket(server.socket, server_side=True)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.server_close); self.addCleanup(server.shutdown)
        (self.d/'token').write_text('synthetic-eso-operator-only'); (self.d/'token').chmod(0o600)
        self.v = {'openbao_eso_run': True, 'openbao_eso_operation': 'apply',
                  'openbao_eso_reviewed_scope': 'openbao-eso-machine-v1', 'openbao_eso_recovery_verified': True,
                  'openbao_eso_cluster_id': 'fixture-cluster', 'openbao_eso_origin': 'https://localhost:'+str(server.server_port),
                  'openbao_eso_public_ca_file': str(self.d/'ca'), 'openbao_eso_token_file': str(self.d/'token')}
    def run_play(self, extra=None, check=False, defaults=False, verbose=False):
        cmd = ['ansible-playbook', '-i', str(self.inventory), str(self.play), '-e', json.dumps({**({} if defaults else self.v), **(extra or {})})]
        if check: cmd.append('--check')
        if verbose: cmd.extend(['-vvv', '--diff'])
        result = subprocess.run(cmd, env=self.env, capture_output=True, text=True, timeout=120)
        self.assertNotIn('synthetic-eso-operator-only', result.stdout+result.stderr)
        return result
    def success(self, result): self.assertEqual(result.returncode, 0, result.stdout+result.stderr)
    def failure(self, result): self.assertNotEqual(result.returncode, 0, result.stdout+result.stderr)
    def seed(self):
        self.s['mount'] = {'type': 'kubernetes', 'description': 'PerkForge eso-machine-v1',
                           'config': {'default_lease_ttl': 300, 'max_lease_ttl': 900}, 'accessor': 'fixture-eso-accessor'}
        self.s['config'] = json.loads((SOURCE/'kubernetes-auth.json').read_text())
        self.s['policies'] = {name: {'policy': (SOURCE/'policies'/f'{name}.hcl').read_text()} for name in NAMES}
        self.s['roles'] = {name: json.loads((SOURCE/'roles'/f'{name}.json').read_text()) for name in NAMES}
    def test_default_check_do_not_read_files_or_contact_server(self):
        (self.d/'token').unlink()
        self.success(self.run_play(defaults=True))
        self.success(self.run_play(check=True))
        self.assertEqual(self.s['calls'], []); self.assertEqual(self.s['writes'], [])
    def test_missing_create_repeat_inspect_preserves_other_auth(self):
        foreign = copy.deepcopy(self.s['foreign'])
        self.success(self.run_play(verbose=True)); self.assertEqual(len(self.s['writes']), 6)
        self.assertEqual(self.s['calls'][0], ('GET', '/v1/sys/health', False))
        first_write = next(i for i, (method, _, _) in enumerate(self.s['calls']) if method != 'GET')
        prereads = {path for _, path, _ in self.s['calls'][:first_write]}
        self.assertTrue({'/v1/auth/kubernetes-eso/config',
                         *('/v1/auth/kubernetes-eso/role/'+name for name in NAMES),
                         *('/v1/sys/policies/acl/'+name for name in NAMES)} <= prereads)
        for operation in ['apply', 'inspect']:
            result = self.run_play({'openbao_eso_operation': operation}); self.success(result)
            self.assertIn('changed=0', result.stdout); self.assertEqual(len(self.s['writes']), 6)
        self.assertEqual(self.s['foreign'], foreign)
    def test_wrong_target_and_wrong_ca_never_send_bearer(self):
        self.failure(self.run_play({'openbao_eso_cluster_id': 'wrong'}))
        self.assertEqual(self.s['calls'], [('GET', '/v1/sys/health', False)])
        subprocess.run(['openssl', 'req', '-x509', '-newkey', 'rsa:2048', '-nodes', '-days', '1', '-subj', '/CN=untrusted', '-keyout', str(self.d/'wrong-key'), '-out', str(self.d/'wrong-ca')], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self.s['calls'].clear(); self.failure(self.run_play({'openbao_eso_public_ca_file': str(self.d/'wrong-ca')}))
        self.assertEqual(self.s['calls'], []); self.assertEqual(self.s['writes'], [])
    def test_wrong_engine_version_never_reads_or_sends_bearer(self):
        self.s['version'] = '2.8.0'
        (self.d/'token').unlink()
        self.failure(self.run_play(verbose=True))
        self.assertEqual(self.s['calls'], [('GET', '/v1/sys/health', False)])
        self.assertEqual(self.s['writes'], [])
    def test_wrong_scope_and_target_selection_stop_before_api(self):
        for extra in [{'openbao_eso_run': 'true'}, {'openbao_eso_recovery_verified': 'true'}, {'openbao_eso_recovery_verified': 'false'}, {'openbao_eso_reviewed_scope': 'wrong'}, {'deployment_environment': 'wrong'}, {'openbao_eso_recovery_verified': False}, {'openbao_eso_operation': 'rollback'}, {'gitops_path': './big-bang-bootstrap/clusters/local'}]:
            with self.subTest(extra=extra): self.failure(self.run_play(extra))
        self.assertEqual(self.s['calls'], [])
    def test_checkout_mismatch_and_dirty_tree_stop_before_api(self):
        self.env['FIXTURE_HEAD'] = 'b'*40
        self.failure(self.run_play()); self.env.pop('FIXTURE_HEAD')
        self.env['FIXTURE_DIRTY'] = ' M changed.yaml'
        self.failure(self.run_play())
        self.assertEqual(self.s['calls'], []); self.assertEqual(self.s['writes'], [])
    def test_protected_token_refuses_links_and_permissions(self):
        token = self.d/'token'
        token.chmod(0o644); self.failure(self.run_play()); token.chmod(0o600)
        os.link(token, self.d/'hardlink'); self.failure(self.run_play()); (self.d/'hardlink').unlink()
        (self.d/'symlink').symlink_to(token)
        self.failure(self.run_play({'openbao_eso_token_file': str(self.d/'symlink')}))
        self.assertFalse(any(bearer for _, _, bearer in self.s['calls'])); self.assertEqual(self.s['writes'], [])
    def test_conflicts_before_any_write(self):
        changes = [('mount', {'type': 'kubernetes', 'description': 'foreign'}),
                   ('kv', {}), ('extra_roles', ['legacy-wide']),
                   ('config', {'kubernetes_host': 'https://wrong', 'disable_local_ca_jwt': False}),
                   ('policies', {'eso-tenant-portal': {'policy': 'path "*" {capabilities=["sudo"]}'}}),
                   ('roles', {'eso-tenant-portal': {'bound_service_account_names': ['*']}})]
        for key, value in changes:
            with self.subTest(key=key):
                original = copy.deepcopy(self.s[key]); self.s[key] = value
                self.failure(self.run_play()); self.assertEqual(self.s['writes'], []); self.s[key] = original
    def test_role_extra_privileges_and_identity_inheritance_refused(self):
        self.seed(); role = copy.deepcopy(self.s['roles']['eso-tenant-portal'])
        for extra in [{'bound_service_account_namespace_selector': 'all=true'}, {'token_period': 600}, {'token_policies': ['eso-tenant-portal', 'default']}, {'token_no_default_policy': False}, {'unknown_future_privilege': True}]:
            self.s['roles']['eso-tenant-portal'] = {**role, **extra}
            with self.subTest(extra=extra): self.failure(self.run_play()); self.assertEqual(self.s['writes'], [])
        self.s['roles']['eso-tenant-portal'] = role
        self.s['aliases'] = {'alias-id': {'mount_accessor': 'fixture-eso-accessor', 'canonical_id': 'entity-id'}}
        for extra in [{'policies': ['wide']}, {'inherited_group_ids': ['group']}]:
            self.s['entities'] = {'entity-id': extra}; self.failure(self.run_play()); self.assertEqual(self.s['writes'], [])
        self.s['entities'] = {'entity-id': {'policies': [], 'group_ids': []}}
        self.success(self.run_play({'openbao_eso_operation': 'inspect'}))
        self.s['groups'] = {'group-id': {'mount_accessor': 'fixture-eso-accessor'}}
        self.failure(self.run_play()); self.assertEqual(self.s['writes'], [])
    def test_partial_failure_inspect_and_retry_create_only_missing(self):
        self.s['deny'] = '/v1/auth/kubernetes-eso/role/eso-tenant-portal'
        self.failure(self.run_play()); self.assertEqual(len(self.s['writes']), 5)
        snapshot = copy.deepcopy(self.s['writes'])
        self.success(self.run_play({'openbao_eso_operation': 'inspect'})); self.assertEqual(self.s['writes'], snapshot)
        self.s['deny'] = ''; self.success(self.run_play()); self.assertEqual(len(self.s['writes']), 6)
    def test_missing_inspect_is_read_only(self):
        self.success(self.run_play({'openbao_eso_operation': 'inspect'})); self.assertEqual(self.s['writes'], [])


if __name__ == '__main__': unittest.main()
