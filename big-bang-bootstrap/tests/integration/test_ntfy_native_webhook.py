"""Optional native ntfy TLS/ACL/formatting test; synthetic data and loopback only.

Set NTFY_VALIDATE_BIN to the separately checksum-verified official v2.37.2 binary.
No download, live Grafana, production credentials or cluster access is performed.
"""
import base64
import json
import os
from pathlib import Path
import shutil
import socket
import ssl
import subprocess
import tempfile
import time
import unittest
import urllib.error
import urllib.request
import yaml

ROOT = Path(__file__).resolve().parents[2]
SENTINEL = 'SYNTHETIC-SENSITIVE-DETAIL-MUST-NOT-BE-FORWARDED'
PASSWORD = 'synthetic-fixture-only-credential-123456789'


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        raise AssertionError('Loopback fixture must never follow a redirect')


class NtfyNativeWebhook(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        binary = os.environ.get('NTFY_VALIDATE_BIN')
        if not binary:
            raise unittest.SkipTest('Set NTFY_VALIDATE_BIN to checksum-verified official ntfy v2.37.2; no binary is downloaded')
        cls.env = {k: v for k, v in os.environ.items() if not k.startswith('NTFY_')}
        version = subprocess.run([binary, '--version'], capture_output=True, text=True, check=True, env=cls.env)
        if version.stdout.strip() != 'ntfy version 2.37.2':
            raise AssertionError('Only the reviewed ntfy v2.37.2 fixture is accepted')
        cls.temp = tempfile.TemporaryDirectory(); cls.addClassCleanup(cls.temp.cleanup)
        cls.folder = Path(cls.temp.name)
        cls.cert = cls.folder / 'tls.crt'; key = cls.folder / 'tls.key'
        subprocess.run(['openssl', 'req', '-x509', '-newkey', 'rsa:2048', '-nodes', '-keyout', str(key), '-out', str(cls.cert), '-days', '1', '-subj', '/CN=localhost', '-addext', 'subjectAltName=DNS:localhost'], check=True, capture_output=True)
        key.chmod(0o600)
        templates = cls.folder / 'templates'; templates.mkdir()
        shutil.copyfile(ROOT / 'configuration/observability/ntfy-templates/platform-grafana.yml', templates / 'platform-grafana.yml')
        with socket.socket() as listener:
            listener.bind(('127.0.0.1', 0)); cls.port = listener.getsockname()[1]
        cls.url = 'https://localhost:' + str(cls.port)
        config = cls.folder / 'server.yml'
        config.write_text(yaml.safe_dump({
            'base-url': cls.url, 'listen-http': '-', 'listen-https': '127.0.0.1:' + str(cls.port),
            'key-file': str(key), 'cert-file': str(cls.cert),
            'auth-file': str(cls.folder / 'auth.db'), 'auth-default-access': 'deny-all',
            'cache-file': str(cls.folder / 'cache.db'), 'cache-duration': '10m',
            'attachment-cache-dir': '', 'template-dir': str(templates),
            'upstream-base-url': '', 'web-root': 'disable', 'log-level': 'WARN',
        }))
        config.chmod(0o600)
        cls.log = (cls.folder / 'server.log').open('w'); cls.addClassCleanup(cls.log.close)
        cls.server = subprocess.Popen([binary, 'serve', '--config', str(config)], env=cls.env, stdout=cls.log, stderr=subprocess.STDOUT)
        def stop():
            cls.server.terminate()
            try: cls.server.wait(timeout=5)
            except subprocess.TimeoutExpired: cls.server.kill(); cls.server.wait(timeout=5)
        cls.addClassCleanup(stop)
        cls.context = ssl.create_default_context(cafile=str(cls.cert))
        for _ in range(100):
            if cls.server.poll() is not None:
                raise AssertionError('Synthetic ntfy failed to start: ' + (cls.folder / 'server.log').read_text())
            try:
                with socket.create_connection(('127.0.0.1', cls.port), timeout=.1): break
            except OSError: time.sleep(.05)
        else: raise AssertionError('Synthetic ntfy did not bind loopback')
        for user, permission in [('fixture-publisher', 'write-only'), ('fixture-subscriber', 'read-only')]:
            result = subprocess.run([binary, 'user', '--config', str(config), 'add', user], env={**cls.env, 'NTFY_PASSWORD': PASSWORD}, capture_output=True, text=True)
            if result.returncode: raise AssertionError(result.stdout + result.stderr)
            subprocess.run([binary, 'access', '--config', str(config), user, 'platform-alerts', permission], env=cls.env, check=True, capture_output=True)

    def request(self, method, path, user=None, payload=None, context=None, host=None, password=PASSWORD):
        headers = {'Content-Type': 'application/json'}
        if user:
            headers['Authorization'] = 'Basic ' + base64.b64encode((user + ':' + password).encode()).decode()
        body = json.dumps(payload).encode() if payload is not None else None
        request = urllib.request.Request((host or self.url) + path, data=body, method=method, headers=headers)
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), urllib.request.HTTPSHandler(context=context or self.context), NoRedirect())
        try:
            with opener.open(request, timeout=5) as response: return response.status, response.read().decode()
        except urllib.error.HTTPError as error: return error.code, error.read().decode()

    def test_native_firing_resolved_formatter_omits_sensitive_fields(self):
        for status, priority in [('firing', 4), ('resolved', 3)]:
            payload = {'receiver': 'fixture', 'status': status, 'alerts': [
                {'status': status, 'labels': {'alertname': SENTINEL}, 'annotations': {'summary': SENTINEL}, 'values': {'A': 42}}
            ], 'groupLabels': {'private': SENTINEL}, 'commonLabels': {'private': SENTINEL}, 'commonAnnotations': {'private': SENTINEL},
                'version': '1', 'groupKey': '{}', 'truncatedAlerts': 0, 'orgId': 1,
                'title': SENTINEL, 'message': SENTINEL, 'externalURL': 'https://synthetic.invalid/' + SENTINEL}
            code, body = self.request('POST', '/platform-alerts?template=platform-grafana', 'fixture-publisher', payload)
            self.assertEqual(code, 200, body)
            message = json.loads(body)
            self.assertEqual(message['title'], 'Platform alerts ' + status)
            self.assertEqual(message['priority'], priority)
            self.assertEqual(message['message'], '1 grouped alert(s). Open Grafana with your approved account for details.')
            self.assertNotIn(SENTINEL, body)
        code, body = self.request('GET', '/platform-alerts/json?poll=1&since=all', 'fixture-subscriber')
        self.assertEqual(code, 200, body)
        messages = [json.loads(line) for line in body.splitlines() if line]
        self.assertTrue(any(x.get('title') == 'Platform alerts firing' for x in messages))
        self.assertTrue(any(x.get('title') == 'Platform alerts resolved' for x in messages))
        self.assertNotIn(SENTINEL, body)

    def test_anonymous_and_wrong_role_or_topic_access_is_denied(self):
        for method, path, user, payload in [
            ('POST', '/platform-alerts', None, {'message': 'fixture'}),
            ('GET', '/platform-alerts/json?poll=1', None, None),
            ('GET', '/platform-alerts/json?poll=1', 'fixture-publisher', None),
            ('POST', '/platform-alerts', 'fixture-subscriber', {'message': 'fixture'}),
            ('POST', '/another-topic', 'fixture-publisher', {'message': 'fixture'}),
            ('GET', '/another-topic/json?poll=1', 'fixture-subscriber', None),
        ]:
            with self.subTest(method=method, path=path, user=user):
                code, _ = self.request(method, path, user, payload)
                self.assertIn(code, (401, 403))

    def test_wrong_ca_and_wrong_hostname_are_denied_before_auth(self):
        for context, host in [(ssl.create_default_context(), self.url), (self.context, 'https://127.0.0.1:' + str(self.port))]:
            with self.subTest(host=host):
                with self.assertRaises(urllib.error.URLError) as error:
                    self.request('GET', '/platform-alerts/json?poll=1', context=context, host=host)
                self.assertIsInstance(error.exception.reason, ssl.SSLCertVerificationError)

    def test_wrong_password_is_denied(self):
        code, _ = self.request('POST', '/platform-alerts', 'fixture-publisher', {'message': 'fixture'}, password='incorrect-synthetic-credential')
        self.assertIn(code, (401, 403))

    def test_malformed_webhook_is_rejected_without_raw_payload_fallback(self):
        code, _ = self.request('POST', '/platform-alerts?template=platform-grafana', 'fixture-publisher', {'status': 'firing', 'message': SENTINEL})
        self.assertEqual(code, 400)
        code, body = self.request('GET', '/platform-alerts/json?poll=1&since=all', 'fixture-subscriber')
        self.assertEqual(code, 200, body)
        self.assertNotIn(SENTINEL, body)
