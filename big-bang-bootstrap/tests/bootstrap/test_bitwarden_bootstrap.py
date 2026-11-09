"""Real Ansible, synthetic bw and HTTPS KV-v2 fixtures. No operator vault/cluster."""
import copy
import json
import importlib.util
import os
from pathlib import Path
import shutil
import ssl
import subprocess
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ROOT = Path(__file__).resolve().parents[2]
ACCOUNT = '11111111-1111-4111-8111-111111111111'
ITEM = '22222222-2222-4222-8222-222222222222'
SECRET = 'synthetic-password-with-{{not_a_template}}-and-newline\n'


class BitwardenBootstrap(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='bitwarden-offline-')
        self.addCleanup(self.temp.cleanup)
        self.d = Path(self.temp.name)
        self.repo = self.d / 'repo'
        self.playdir = self.repo / 'big-bang-bootstrap/configuration/ansible'
        self.playdir.mkdir(parents=True)
        for path in (ROOT / 'configuration/ansible').glob('bitwarden-*'):
            shutil.copy(path, self.playdir / path.name)
        (self.playdir / 'tasks').mkdir()
        for path in (ROOT / 'configuration/ansible/tasks').glob('bitwarden-*'):
            shutil.copy(path, self.playdir / 'tasks' / path.name)
        subprocess.run(['git', 'init', '-q', str(self.repo)], check=True)
        (self.repo / '.gitignore').write_text('.secrets/\n')
        self.inventory = self.d / 'inventory.json'
        self.inventory.write_text(json.dumps({'all': {'children': {'bootstrap_clusters': {
            'hosts': {'test': {'ansible_connection': 'local', 'deployment_environment': 'test'}}}}}}))
        self.statefile = self.d / 'state.json'
        self.calls = self.d / 'calls.jsonl'
        self.sensitive_markers = []
        self.state = {'status': {'status': 'unlocked', 'userId': ACCOUNT,
                                 'serverUrl': 'https://vault.bitwarden.com'},
                      'item': {'id': ITEM, 'name': 'Reviewed fixture item', 'type': 1,
                               'organizationId': None, 'collectionIds': [],
                               'login': {'username': 'synthetic-user', 'password': SECRET}}}
        self.cli = self.d / 'bw'
        self.cli.write_text('''#!/usr/bin/python3
import json,os,sys
from pathlib import Path
p=Path(os.environ['BW_FIXTURE_STATE']);s=json.loads(p.read_text());a=sys.argv[1:]
with open(os.environ['BW_FIXTURE_CALLS'],'a') as f:f.write(json.dumps(a)+'\\n')
assert os.environ.get('BW_SESSION')=='synthetic-session-only'
assert os.environ.get('BW_NOINTERACTION')=='true'
if a==['--version']:print('2026.10.1')
elif a==['status']:print(json.dumps(s['status']))
elif a==['get','item',s['item']['id']]:
 if s.get('fail'):print('synthetic-session-only '+s['item']['login']['password'],file=sys.stderr);sys.exit(1)
 print(json.dumps(s['item']))
else:raise SystemExit('Unsupported fixture command')
''')
        self.cli.chmod(0o700)
        self.manifest = {'schema_version': 1, 'environment': 'test', 'account_id': ACCOUNT,
                         'server_url': 'https://vault.bitwarden.com', 'organization_id': None,
                         'sources': {'registry-user': {'item_id': ITEM, 'item_name': 'Reviewed fixture item',
                             'field': 'username', 'purpose': 'initial', 'collection_ids': []},
                             'service-password': {'item_id': ITEM, 'item_name': 'Reviewed fixture item',
                             'field': 'password', 'purpose': 'downstream', 'collection_ids': []}},
                         'platform': [{'path': 'bootstrap/test/service', 'fields': {'password': 'service-password'}}]}
        self.vars = {'bitwarden_bootstrap_stage': True, 'bitwarden_bootstrap_cli': str(self.cli),
                     'bitwarden_bootstrap_manifest': self.manifest}
        self.output = self.repo / '.secrets/bitwarden-bootstrap-test'
        # Strip any real credential environment, use only isolated synthetic session/config.
        self.env = {k: v for k, v in os.environ.items() if not k.startswith(('BW_', 'BAO_', 'VAULT_', 'ANSIBLE_'))}
        self.env.update({'BW_SESSION': 'synthetic-session-only', 'BW_FIXTURE_STATE': str(self.statefile),
                         'BW_FIXTURE_CALLS': str(self.calls), 'BITWARDENCLI_APPDATA_DIR': str(self.d / 'vault'),
                         'KUBECONFIG': '/dev/null', 'ANSIBLE_LOCAL_TEMP': str(self.d / 'local'),
                         'ANSIBLE_REMOTE_TEMP': str(self.d / 'remote'), 'ANSIBLE_NOCOLOR': '1'})

    def run_play(self, extra=None, options=(), success=True):
        self.statefile.write_text(json.dumps(self.state))
        variables = self.d / 'vars.json'
        variables.write_text(json.dumps({**self.vars, **(extra or {})}))
        result = subprocess.run(['ansible-playbook', '-i', str(self.inventory),
                                 str(self.playdir / 'bitwarden-bootstrap.yaml'), '-e', '@' + str(variables),
                                 *options], env=self.env, capture_output=True, text=True, timeout=90)
        output = result.stdout + result.stderr
        for secret in [SECRET.strip(), 'synthetic-session-only', 'synthetic-bao-token', *self.sensitive_markers]:
            self.assertNotIn(secret, output)
        if success:
            self.assertEqual(result.returncode, 0, output)
        else:
            self.assertNotEqual(result.returncode, 0, output)
        return output

    def command_calls(self):
        return [json.loads(line) for line in self.calls.read_text().splitlines()] if self.calls.exists() else []

    def test_default_and_check_mode_never_contact_cli_or_create_files(self):
        self.run_play({'bitwarden_bootstrap_stage': False, 'bitwarden_bootstrap_seed': False,
                       'bitwarden_bootstrap_manifest': {}})
        self.run_play({'bitwarden_bootstrap_seed': True}, options=['--check', '--diff'])
        self.assertEqual(self.command_calls(), [])
        self.assertFalse((self.repo / '.secrets').exists())

    def test_stage_exact_fields_reuses_without_overwrite_and_redacts_verbose_diff(self):
        self.run_play(options=['--diff', '-vvv'])
        self.assertEqual((self.output / 'service-password').read_bytes(), SECRET.encode())
        self.assertEqual((self.output / 'registry-user').read_text(), 'synthetic-user')
        self.assertEqual(self.output.stat().st_mode & 0o777, 0o700)
        for path in self.output.iterdir():
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
        self.assertEqual(self.command_calls(), [['--version'], ['status'], ['get', 'item', ITEM]])
        before = (self.output / 'service-password').stat().st_mtime_ns
        self.assertIn('changed=0', self.run_play())
        self.assertEqual((self.output / 'service-password').stat().st_mtime_ns, before)
        self.state['item']['login']['password'] = 'synthetic-different'
        self.run_play(success=False)
        self.assertEqual((self.output / 'service-password').read_bytes(), SECRET.encode())

    def test_environment_paths_and_missing_mappings_fail_before_cli(self):
        for change in ('environment', 'path', 'field', 'initial-to-platform'):
            manifest = copy.deepcopy(self.manifest)
            if change == 'environment': manifest['environment'] = 'production'
            if change == 'path': manifest['platform'][0]['path'] = 'bootstrap/test/../production'
            if change == 'field': manifest['sources']['service-password']['field'] = 'notes'
            if change == 'initial-to-platform': manifest['platform'][0]['fields']['password'] = 'registry-user'
            with self.subTest(change=change):
                self.run_play({'bitwarden_bootstrap_manifest': manifest}, success=False)
                self.assertEqual(self.command_calls(), [])
                self.assertFalse(self.output.exists())

    def test_missing_session_and_multiple_targets_stop_before_cli(self):
        self.env.pop('BW_SESSION')
        self.run_play(success=False)
        self.assertEqual(self.command_calls(), [])
        inventory = json.loads(self.inventory.read_text())
        inventory['all']['children']['bootstrap_clusters']['hosts']['other'] = {
            'ansible_connection': 'local', 'deployment_environment': 'test'}
        self.inventory.write_text(json.dumps(inventory))
        self.run_play(success=False)
        self.assertEqual(self.command_calls(), [])

    def test_wrong_account_and_locked_vault_stop_before_item_access(self):
        for status in ({'status': 'locked'}, {'userId': ITEM}, {'serverUrl': 'https://wrong.invalid'}):
            previous = copy.deepcopy(self.state)
            self.state['status'].update(status)
            self.run_play(success=False)
            self.assertFalse(any(call[0] == 'get' for call in self.command_calls()))
            self.calls.unlink()
            self.state = previous

    def test_wrong_item_scope_empty_fields_and_cli_failure_never_write(self):
        for mode in ('name', 'organization', 'collection', 'deleted', 'missing', 'empty', 'failure'):
            previous = copy.deepcopy(self.state)
            if mode == 'name': self.state['item']['name'] = 'Different environment'
            if mode == 'organization': self.state['item']['organizationId'] = ACCOUNT
            if mode == 'collection': self.state['item']['collectionIds'] = [ACCOUNT]
            if mode == 'deleted': self.state['item']['deletedDate'] = '2026-01-01'
            if mode == 'missing': self.state['item']['login'].pop('password')
            if mode == 'empty': self.state['item']['login']['password'] = '  '
            if mode == 'failure': self.state['fail'] = True
            with self.subTest(mode=mode):
                self.run_play(success=False)
                self.assertFalse(self.output.exists())
            self.state = previous

    def test_unsafe_local_custody_fails_before_cli(self):
        root = self.repo / '.secrets'
        root.mkdir(mode=0o755)
        self.run_play(success=False)
        root.chmod(0o700)
        elsewhere = self.d / 'elsewhere'
        elsewhere.mkdir(mode=0o700)
        self.output.symlink_to(elsewhere, target_is_directory=True)
        self.run_play(success=False)
        self.output.unlink()
        self.output.mkdir(mode=0o700)
        protected = elsewhere / 'protected'; protected.write_text('do-not-touch')
        (self.output / 'service-password').symlink_to(protected)
        self.run_play(success=False)
        self.assertEqual(self.command_calls(), [])
        self.assertEqual(protected.read_text(), 'do-not-touch')

    def test_hardlinked_or_public_destination_refused_before_cli(self):
        root = self.repo / '.secrets'; root.mkdir(mode=0o700)
        self.output.mkdir(mode=0o700)
        protected = self.output / 'service-password'
        protected.write_text('preserve-existing'); protected.chmod(0o644)
        self.run_play(success=False)
        protected.chmod(0o600)
        (self.d / 'other-link').hardlink_to(protected)
        self.run_play(success=False)
        self.assertEqual(self.command_calls(), [])
        self.assertEqual(protected.read_text(), 'preserve-existing')

    def test_tracked_output_or_per_file_unignore_refused_before_cli(self):
        root = self.repo / '.secrets'; root.mkdir(mode=0o700)
        self.output.mkdir(mode=0o700)
        protected = self.output / 'service-password'
        protected.write_text('preserve-tracked-fixture'); protected.chmod(0o600)
        subprocess.run(['git', '-C', str(self.repo), 'add', '-f', str(protected)], check=True)
        self.run_play(success=False)
        self.assertEqual(self.command_calls(), [])
        self.assertEqual(protected.read_text(), 'preserve-tracked-fixture')
        subprocess.run(['git', '-C', str(self.repo), 'rm', '--cached', str(protected)], check=True,
                       stdout=subprocess.DEVNULL)
        (self.repo / '.gitignore').write_text('.secrets/*\n!.secrets/bitwarden-bootstrap-test/\n.secrets/bitwarden-bootstrap-test/*\n!.secrets/bitwarden-bootstrap-test/manifest.json\n')
        self.run_play(success=False)
        self.assertEqual(self.command_calls(), [])

    def start_bao(self, engine=None):
        subprocess.run(['openssl', 'req', '-x509', '-newkey', 'rsa:2048', '-nodes', '-days', '1',
                        '-subj', '/CN=localhost', '-addext', 'subjectAltName=DNS:localhost',
                        '-keyout', str(self.d / 'key'), '-out', str(self.d / 'ca')],
                       check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        state = {'calls': [], 'data': {}, 'mode': 'normal', 'writes': 0}
        self.bao = state
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args): pass
            def forward(self):
                state['calls'].append((self.command, self.path))
                body = self.rfile.read(int(self.headers.get('Content-Length', '0')))
                headers = {key: self.headers[key] for key in ('X-Vault-Token', 'Content-Type') if key in self.headers}
                response = engine.session.request(self.command, engine.base.removesuffix('/v1') + self.path,
                    headers=headers, data=body or None, timeout=5, allow_redirects=False)
                self.send_response(response.status_code); self.send_header('Content-Type', 'application/json'); self.end_headers()
                self.wfile.write(response.content)
            def do_GET(self):
                if engine: return self.forward()
                state['calls'].append(('GET', self.path))
                status = 200
                if self.path == '/v1/sys/health':
                    data = {'initialized': True, 'sealed': False, 'cluster_id': 'fixture-cluster'}
                    if state['mode'] == 'wrong-cluster': data['cluster_id'] = 'different-cluster'
                elif self.headers.get('X-Vault-Token') != 'synthetic-bao-token':
                    status, data = 403, {'errors': ['denied']}
                elif self.path == '/v1/auth/token/lookup-self':
                    data = {'data': {'policies': ['root'] if state['mode'] == 'root' else ['bitwarden-bootstrap-test'], 'ttl': 900}}
                    if state['mode'] == 'extra-policy': data['data']['policies'].append('default')
                    if state['mode'] == 'identity-policy': data['data']['identity_policies'] = ['human-admin']
                    if state['mode'] == 'long-ttl': data['data']['ttl'] = 7200
                    if state['mode'] == 'expired': data['data']['ttl'] = 0
                elif self.path.startswith('/v1/sys/internal/ui/mounts/platform/'):
                    data = {'data': {'path': 'platform/', 'type': 'kv', 'options': {'version': '1' if state['mode'] == 'kv1' else '2'}}}
                elif self.path in state['data']:
                    data = {'data': {'data': state['data'][self.path], 'metadata': {'version': 1, 'destroyed': False, 'deletion_time': ''}}}
                else: status, data = 404, {'errors': []}
                self.reply(status, data)
            def do_POST(self):
                if engine: return self.forward()
                state['calls'].append(('POST', self.path))
                body = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                assert self.headers.get('X-Vault-Token') == 'synthetic-bao-token'
                assert body['options'] == {'cas': 0}
                assert self.path.startswith('/v1/platform/data/bootstrap/test/')
                if self.path in state['data'] or state['mode'] in ('tombstone', 'race'):
                    self.reply(400, {'errors': ['CAS conflict']}); return
                state['data'][self.path] = body['data']; state['writes'] += 1
                if state['mode'] == 'lost-response':
                    self.reply(500, {'errors': ['response lost after commit']}); return
                self.reply(200, {'data': {'version': 1}})
            def reply(self, status, data):
                self.send_response(status); self.send_header('Content-Type', 'application/json'); self.end_headers()
                self.wfile.write(json.dumps(data).encode())
        server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ctx.load_cert_chain(str(self.d / 'ca'), str(self.d / 'key'))
        server.socket = ctx.wrap_socket(server.socket, server_side=True)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.server_close); self.addCleanup(server.shutdown)
        token = self.d / 'token'; token.write_text('synthetic-bao-token'); token.chmod(0o600)
        self.vars.update({'bitwarden_bootstrap_stage': False, 'bitwarden_bootstrap_seed': True,
                          'bitwarden_bootstrap_bao_url': 'https://localhost:' + str(server.server_port),
                          'bitwarden_bootstrap_bao_cluster_id': 'fixture-cluster',
                          'bitwarden_bootstrap_bao_policy': 'bitwarden-bootstrap-test',
                          'bitwarden_bootstrap_bao_ca_file': str(self.d / 'ca'),
                          'bitwarden_bootstrap_bao_token_file': str(token)})

    def test_seed_exact_downstream_only_idempotence_and_rotation_refusal(self):
        self.run_play()
        self.start_bao()
        self.calls.unlink()
        self.run_play(options=['--diff', '-vvv'])
        self.assertEqual(self.bao['data'], {'/v1/platform/data/bootstrap/test/service': {'password': SECRET}})
        self.assertEqual(self.command_calls(), [])
        self.assertIn('changed=0', self.run_play())
        self.assertEqual(self.bao['writes'], 1)
        self.bao['data']['/v1/platform/data/bootstrap/test/service']['other'] = 'preserve-existing-key'
        self.run_play(success=False)
        self.assertEqual(self.bao['writes'], 1)

    def test_seed_refuses_wrong_cluster_root_kv1_tombstones_and_concurrent_writer(self):
        self.run_play()
        self.start_bao()
        for mode in ('wrong-cluster', 'root', 'extra-policy', 'identity-policy', 'long-ttl', 'expired', 'kv1', 'tombstone', 'race'):
            self.bao['mode'] = mode
            with self.subTest(mode=mode):
                self.run_play(success=False)
                self.assertEqual(self.bao['writes'], 0)

    def test_seed_lost_response_can_resume_without_a_second_version(self):
        self.run_play(); self.start_bao()
        self.bao['mode'] = 'lost-response'
        self.run_play(success=False)
        self.assertEqual(self.bao['writes'], 1)
        self.bao['mode'] = 'normal'
        self.assertIn('changed=0', self.run_play())
        self.assertEqual(self.bao['writes'], 1)

    def test_seed_requires_manifest_receipt_and_tls_trust(self):
        self.run_play(); self.start_bao()
        (self.output / 'manifest.json').unlink()
        self.run_play(success=False)
        self.assertEqual(self.bao['calls'], [])
        (self.output / 'manifest.json').write_text(json.dumps(self.manifest))
        (self.output / 'manifest.json').chmod(0o600)
        self.run_play({'bitwarden_bootstrap_bao_ca_file': '/nonexistent-fixture-ca'}, success=False)
        self.assertEqual(self.bao['writes'], 0)


@unittest.skipUnless(os.environ.get('RUN_OPENBAO_POLICY_TESTS') == '1',
                     'opt in to existing pinned 2.7.2 native engine fixture')
class NativeOpenBaoBootstrap(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = ROOT / 'tests/integration/test_sso_openbao_self_session.py'
        spec = importlib.util.spec_from_file_location('bootstrap_native_engine', path)
        module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        cls.engine = module.PinnedEngine
        cls.engine.setUpClass()
        cls.addClassCleanup(cls.engine.doClassCleanups)

    def test_exact_create_read_policy_real_kv2_repeat_and_tombstone_refusal(self):
        fixture = BitwardenBootstrap()
        fixture.setUp(); self.addCleanup(fixture.doCleanups)
        fixture.run_play()
        path = '/platform/data/bootstrap/test/service'
        policy_name = 'bitwarden-bootstrap-test'
        policy = 'path "auth/token/lookup-self" { capabilities = ["read"] }\n' + \
                 'path "' + path[1:] + '" { capabilities = ["create", "read"] }'
        self.assertEqual(self.engine.call('PUT', '/sys/policies/acl/' + policy_name,
                                         {'policy': policy}).status_code, 204)
        result = self.engine.call('POST', '/auth/token/create', {'policies': [policy_name],
            'no_default_policy': True, 'ttl': '15m', 'explicit_max_ttl': '15m', 'renewable': False})
        self.assertEqual(result.status_code, 200)
        token = result.json()['auth']['client_token']
        fixture.sensitive_markers.append(token)
        fixture.start_bao(self.engine)
        (fixture.d / 'token').write_text(token)
        fixture.vars['bitwarden_bootstrap_bao_cluster_id'] = self.engine.call('GET', '/sys/health').json()['cluster_id']
        fixture.run_play(options=['--diff', '-vvv'])
        self.assertEqual(self.engine.call('GET', path).json()['data']['data'], {'password': SECRET})
        self.assertEqual(self.engine.call('GET', path).json()['data']['metadata']['version'], 1)
        self.assertIn('changed=0', fixture.run_play())
        self.assertEqual(self.engine.call('GET', path).json()['data']['metadata']['version'], 1)
        for method, target, body in [
            ('GET', '/tenants/data/synthetic-only', None),
            ('GET', '/platform/data/bootstrap/other/service', None),
            ('GET', '/sys/mounts', None),
            ('POST', path, {'data': {'password': 'forbidden-update'}}),
            ('DELETE', '/platform/metadata/bootstrap/test/service', None),
            ('POST', '/sys/policies/acl/unapproved', {'policy': policy}),
            ('POST', '/auth/token/create', {})]:
            with self.subTest(method=method, target=target):
                self.assertEqual(self.engine.call(method, target, body, token=token).status_code, 403)
        self.assertEqual(self.engine.call('DELETE', path).status_code, 204)
        fixture.run_play(success=False)
        self.assertEqual(self.engine.call('GET', '/platform/metadata/bootstrap/test/service').json()['data']['current_version'], 1)
        self.assertEqual(self.engine.call('GET', path).status_code, 404)
        self.assertEqual(self.engine.call('POST', '/platform/destroy/bootstrap/test/service', {'versions': [1]}).status_code, 204)
        fixture.run_play(success=False)
        self.assertEqual(self.engine.call('GET', '/platform/metadata/bootstrap/test/service').json()['data']['current_version'], 1)
