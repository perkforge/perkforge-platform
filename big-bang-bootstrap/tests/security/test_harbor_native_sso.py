"""Real Ansible against disposable loopback TLS; no cluster or real credentials."""
import base64
import http.server
import json
import os
from pathlib import Path
import ssl
import subprocess
import tempfile
import threading
import unittest
import yaml

ROOT = Path(__file__).resolve().parents[3]
DIR = ROOT / 'big-bang-bootstrap/configuration/authorization/sso/harbor'


class NativeSSO(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.path = Path(cls.tmp.name)
        cls.cert, cls.key = cls.path / 'ca.pem', cls.path / 'key.pem'
        subprocess.run(['openssl', 'req', '-x509', '-newkey', 'rsa:2048', '-nodes',
                        '-keyout', str(cls.key), '-out', str(cls.cert), '-days', '1',
                        '-subj', '/CN=localhost', '-addext', 'subjectAltName=DNS:localhost'],
                       check=True, capture_output=True)
        cls.password = cls.path / 'password'
        cls.secret = cls.path / 'secret'
        for path, text in [(cls.password, 'SYNTHETIC_ADMIN_PASSWORD'), (cls.secret, 'SYNTHETIC_CLIENT_SECRET')]:
            path.write_text(text)
            path.chmod(0o600)
        cls.env = dict(os.environ, ANSIBLE_LOCAL_TEMP=str(cls.path / 'ansible'),
                       ANSIBLE_REMOTE_TEMP=str(cls.path / 'remote'))

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def setUp(self):
        self.calls, self.writes = [], []
        self.version = 'v2.15.2'
        self.users = []
        self.corrupt = False
        self.bad_recovery = False
        self.redirect = False
        self.desired = next(task['ansible.builtin.set_fact']['harbor_native_desired']
                            for task in yaml.safe_load((DIR / 'native-tasks.yaml').read_text())[-1]['block']
                            if 'harbor_native_desired' in task.get('ansible.builtin.set_fact', {}))
        self.desired['oidc_endpoint'] = 'https://identity.example.test/auth/realms/perkforge'
        self.config = {k: {'value': v, 'editable': True} for k, v in self.desired.items()}
        self.config['auth_mode']['value'] = 'db_auth'
        self.config['unrelated'] = {'value': 'preserve-me', 'editable': True}
        owner = self

        class Handler(http.server.BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def answer(self, obj, code=200, headers=None):
                self.send_response(code)
                for key, val in (headers or {}).items():
                    self.send_header(key, str(val))
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(obj).encode())

            def do_GET(self):
                owner.calls.append((self.path, self.headers.get('Authorization')))
                if self.path.endswith('/systeminfo'):
                    if owner.redirect:
                        return self.answer({}, 302, {'Location': 'https://identity.example.test/'})
                    return self.answer({'external_url': owner.origin, 'harbor_version': owner.version})
                expected = 'Basic ' + base64.b64encode(b'admin:SYNTHETIC_ADMIN_PASSWORD').decode()
                if self.headers.get('Authorization') != expected:
                    return self.answer({}, 401)
                if self.path.endswith('/users/current'):
                    return self.answer({'username': 'admin', 'user_id': 1,
                                        'sysadmin_flag': not owner.bad_recovery})
                if self.path.endswith('/configurations'):
                    return self.answer(owner.config)
                if self.path.startswith('/api/v2.0/users?'):
                    return self.answer(owner.users, headers={'X-Total-Count': len(owner.users)})
                self.answer({}, 404)

            def do_PUT(self):
                data = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                owner.writes.append(data)
                for key, value in data.items():
                    if key != 'oidc_client_secret':
                        owner.config[key]['value'] = value
                if owner.corrupt:
                    owner.config['unrelated']['value'] = 'corrupted'
                self.answer({})

        self.server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(str(self.cert), str(self.key))
        self.server.socket = context.wrap_socket(self.server.socket, server_side=True)
        self.origin = f'https://localhost:{self.server.server_port}'
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self.close)

    def close(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()

    def run_play(self, changes=None, success=True, check=False, defaults=False):
        values = {} if defaults else {
            'harbor_native_operation': 'apply',
            'harbor_native_apply_approved': True,
            'harbor_native_secret_write_approved': True,
            'harbor_native_origin': self.origin,
            'harbor_native_approved_origin': self.origin,
            'harbor_native_issuer': self.desired['oidc_endpoint'],
            'harbor_native_approved_issuer': self.desired['oidc_endpoint'],
            'harbor_native_admin_password_file': str(self.password),
            'harbor_native_client_secret_file': str(self.secret),
            'harbor_native_ca_file': str(self.cert),
        }
        values.update(changes or {})
        args = ['ansible-playbook', str(DIR / 'native.yaml'), '-e', json.dumps(values)]
        if check:
            args.append('--check')
        result = subprocess.run(args, env=self.env, capture_output=True, text=True)
        output = result.stdout + result.stderr
        self.assertEqual(result.returncode == 0, success, output)
        self.assertNotIn('SYNTHETIC_ADMIN_PASSWORD', output)
        self.assertNotIn('SYNTHETIC_CLIENT_SECRET', output)
        if not defaults and not check:
            self.assertIn('Clear transient native credentials even after failure', output)
        return output

    def test_default_and_check_are_offline(self):
        self.run_play(defaults=True)
        self.run_play({'harbor_native_admin_password_file': '/missing'}, check=True)
        self.assertEqual(self.calls, [])

    def test_apply_preserve_readback_and_repeat_without_secret_read(self):
        self.run_play()
        self.assertEqual(len(self.writes), 1)
        self.assertEqual(self.writes[0], {'auth_mode': 'oidc_auth', 'oidc_client_secret': 'SYNTHETIC_CLIENT_SECRET'})
        self.assertEqual(self.config['unrelated']['value'], 'preserve-me')
        self.run_play({'harbor_native_secret_write_approved': False,
                       'harbor_native_client_secret_file': '/missing'})
        self.assertEqual(len(self.writes), 1)
        self.assertEqual(sum(path.endswith('/users/current') for path, _ in self.calls), 4)
        self.assertTrue(all(auth is None for path, auth in self.calls if path.endswith('/systeminfo')))

    def test_owned_drift_is_repaired_with_minimal_delta(self):
        self.config['auth_mode']['value'] = 'oidc_auth'
        self.config['oidc_verify_cert']['value'] = False
        self.config['oidc_scope']['value'] = 'openid offline_access'
        self.run_play({'harbor_native_secret_write_approved': False})
        self.assertEqual(self.writes, [{'oidc_verify_cert': True, 'oidc_scope': 'openid profile email'}])
        self.assertEqual(self.config['unrelated']['value'], 'preserve-me')

    def test_inspect_reports_drift_without_writes(self):
        self.run_play({'harbor_native_operation': 'inspect', 'harbor_native_secret_write_approved': False})
        self.assertEqual(self.writes, [])

    def test_migration_refuses_existing_user_or_missing_secret_approval(self):
        self.users = [{'user_id': 2, 'username': 'existing', 'sysadmin_flag': True}]
        self.run_play(success=False)
        self.users = []
        self.run_play({'harbor_native_secret_write_approved': False}, success=False)
        self.assertEqual(self.writes, [])

    def test_wrong_version_redirect_and_wrong_recovery_refused(self):
        self.version = 'v2.15.1'
        self.run_play(success=False)
        self.assertEqual(len(self.calls), 1)
        self.version = 'v2.15.2'
        self.redirect = True
        self.run_play(success=False)
        self.redirect = False
        self.bad_recovery = True
        self.run_play(success=False)
        self.assertEqual(self.writes, [])

    def test_readonly_drift_and_unexpected_secret_schema_refused(self):
        self.config['auth_mode']['editable'] = False
        self.run_play(success=False)
        self.config['auth_mode']['editable'] = True
        self.config['oidc_client_secret'] = {'value': '********', 'editable': True}
        self.run_play(success=False)
        self.assertEqual(self.writes, [])

    def test_unrelated_drift_after_write_fails_without_retry(self):
        self.corrupt = True
        self.run_play(success=False)
        self.assertEqual(len(self.writes), 1)

    def test_foreign_oidc_provider_is_not_adopted(self):
        self.config['auth_mode']['value'] = 'oidc_auth'
        for key, value in [('oidc_client_id', 'foreign'), ('oidc_endpoint', 'https://foreign.example.test/realms/perkforge')]:
            original = self.config[key]['value']
            self.config[key]['value'] = value
            self.run_play(success=False)
            self.config[key]['value'] = original
        self.assertEqual(self.writes, [])

    def test_control_whitespace_and_equivalent_hosts_refused(self):
        for suffix in ['\n', '\t', ' ', '\x7f']:
            origin = self.origin + suffix
            self.run_play({'harbor_native_origin': origin, 'harbor_native_approved_origin': origin}, success=False)
        issuer = self.origin.replace('localhost', 'LOCALHOST.') + '/auth/realms/perkforge'
        self.run_play({'harbor_native_issuer': issuer, 'harbor_native_approved_issuer': issuer}, success=False)
        self.assertEqual(self.calls, [])

    def test_unsafe_parent_and_noncanonical_private_paths_refused(self):
        parent = self.path / 'unsafe-parent'
        parent.mkdir(mode=0o755)
        password = parent / 'password'
        password.write_text('SYNTHETIC_ADMIN_PASSWORD')
        password.chmod(0o600)
        self.run_play({'harbor_native_admin_password_file': str(password)}, success=False)
        parent.chmod(0o700)
        alias = self.path / 'parent-alias'
        alias.symlink_to(parent, target_is_directory=True)
        self.run_play({'harbor_native_admin_password_file': str(alias / 'password')}, success=False)
        self.run_play({'harbor_native_admin_password_file': 'relative/password'}, success=False)
        self.assertEqual(self.calls, [])

    def test_cleanup_is_unconditional_and_noncacheable(self):
        play = yaml.safe_load((DIR / 'native.yaml').read_text())[0]
        cleanup = play['tasks'][-1]['always'][0]
        self.assertTrue(cleanup['no_log'])
        self.assertEqual(cleanup['ansible.builtin.set_fact'], {
            'harbor_native_password': None, 'harbor_native_secret': None,
            'harbor_native_delta': {}, 'cacheable': False})

    def test_tls_hostname_mismatch_refused_before_credentials(self):
        origin = self.origin.replace('localhost', '127.0.0.1')
        self.run_play({'harbor_native_origin': origin, 'harbor_native_approved_origin': origin}, success=False)
        self.assertEqual(self.calls, [])

    def test_wrong_target_and_unsafe_file_fail_before_network(self):
        self.run_play({'harbor_native_approved_origin': 'https://different.example.test'}, success=False)
        self.password.chmod(0o644)
        try:
            self.run_play(success=False)
        finally:
            self.password.chmod(0o600)
        self.assertEqual(self.calls, [])


if __name__ == '__main__':
    unittest.main()
