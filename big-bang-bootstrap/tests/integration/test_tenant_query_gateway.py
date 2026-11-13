"""Native nginx + pinned prom-label-proxy, synthetic loopback upstream only.

Set PROM_LABEL_PROXY_BIN to the checksum-verified official Linux amd64 binary.
No downloads, production credentials, Grafana or Kubernetes calls occur here.
These are component tests, not proof of deployed tenant isolation.
"""
import base64
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import socket
import ssl
import subprocess
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.parse
import urllib.request

import yaml

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / 'configuration/observability/tenant-query'


def port():
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        return sock.getsockname()[1]


class Upstream(BaseHTTPRequestHandler):
    def do_GET(self):
        self.reply()

    def do_POST(self):
        self.reply()

    def reply(self):
        body = self.rfile.read(int(self.headers.get('Content-Length', 0))).decode()
        parameters = urllib.parse.parse_qs(urllib.parse.urlsplit(self.path).query)
        for key, values in urllib.parse.parse_qs(body).items():
            parameters.setdefault(key, []).extend(values)
        self.server.received.append((self.path, parameters, dict(self.headers)))
        payload = json.dumps({'status': 'success', 'data': {'resultType': 'vector', 'result': []}}).encode()
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, *args):
        pass


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        raise AssertionError('Synthetic test must never follow redirects')


class NativeTenantQueryGateway(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        binary = os.environ.get('PROM_LABEL_PROXY_BIN')
        if not binary:
            raise unittest.SkipTest('Set PROM_LABEL_PROXY_BIN to the pinned official binary; no download performed')
        pin = yaml.safe_load((SOURCE / 'sources.yaml').read_text())['prom_label_proxy']
        if hashlib.sha256(Path(binary).read_bytes()).hexdigest() != pin['linux_amd64_binary_sha256']:
            raise AssertionError('Native binary does not match reviewed Linux amd64 pin')
        cls.temp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.temp.cleanup)
        cls.folder = Path(cls.temp.name)
        cls.cert = cls.folder / 'tls.crt'
        key = cls.folder / 'tls.key'
        subprocess.run(['openssl', 'req', '-x509', '-newkey', 'rsa:2048', '-nodes',
                        '-keyout', str(key), '-out', str(cls.cert), '-days', '1',
                        '-subj', '/CN=localhost', '-addext', 'subjectAltName=DNS:localhost'],
                       check=True, capture_output=True)
        key.chmod(0o600)
        cls.backend = ThreadingHTTPServer(('127.0.0.1', 0), Upstream)
        cls.backend.received = []
        cls.addClassCleanup(cls.backend.server_close)
        cls.addClassCleanup(cls.backend.shutdown)
        threading.Thread(target=cls.backend.serve_forever, daemon=True).start()
        context = yaml.safe_load((ROOT / 'configuration/authorization/contexts/portal.yaml').read_text())['paas_context']
        # Control namespaces do not silently become part of the runtime data view.
        cls.contexts = [dict(id=context['id'], namespaces=context['kubernetes']['runtime_namespaces']),
                        dict(id='other', namespaces=['tenant-other'])]
        cls.passwords = {'portal': 'synthetic-portal-only', 'other': 'synthetic-other-only'}
        for item in cls.contexts:
            item['proxy_port'] = port()
            item['htpasswd_path'] = str(cls.folder / (item['id'] + '.htpasswd'))
            hashed = subprocess.run(['openssl', 'passwd', '-apr1', '-stdin'],
                                    input=cls.passwords[item['id']], text=True, capture_output=True, check=True).stdout.strip()
            Path(item['htpasswd_path']).write_text(item['id'] + ':' + hashed + '\n')
            Path(item['htpasswd_path']).chmod(0o600)
        cls.port = port()
        cls.values = dict(query_contexts=cls.contexts, metrics_upstream='http://127.0.0.1:' + str(cls.backend.server_port),
                          runtime_dir=str(cls.folder), listen_address='127.0.0.1:' + str(cls.port),
                          server_name='localhost', certificate_path=str(cls.cert), private_key_path=str(key),
                          tenant_query_render_enabled=True)
        variables = cls.folder / 'variables.yaml'
        variables.write_text(yaml.safe_dump(cls.values))
        rendering = subprocess.run(['ansible-playbook', '-i', 'localhost,', str(SOURCE / 'render.yaml'),
                                    '-e', '@' + str(variables)], text=True, capture_output=True)
        if rendering.returncode:
            raise AssertionError(rendering.stdout + rendering.stderr)
        commands = yaml.safe_load((cls.folder / 'proxy-arguments.yaml').read_text())
        cls.processes = []
        def stop():
            for process in reversed(cls.processes):
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill(); process.wait(timeout=5)
        cls.addClassCleanup(stop)
        for command in commands:
            cls.processes.append(subprocess.Popen([binary] + command['arguments'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL))
        conf = cls.folder / 'nginx.conf'
        nginx = os.environ.get('NGINX_VALIDATE_BIN', '/usr/sbin/nginx')
        checked = subprocess.run([nginx, '-t', '-c', str(conf), '-p', str(cls.folder)], capture_output=True, text=True)
        if checked.returncode:
            raise AssertionError(checked.stderr)
        cls.processes.append(subprocess.Popen([nginx, '-c', str(conf), '-p', str(cls.folder), '-g', 'daemon off;'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL))
        for listening in [cls.port] + [item['proxy_port'] for item in cls.contexts]:
            for _ in range(100):
                if any(process.poll() is not None for process in cls.processes):
                    raise AssertionError('Native synthetic gateway process exited: ' + (cls.folder / 'error.log').read_text())
                try:
                    with socket.create_connection(('127.0.0.1', listening), timeout=.1):
                        break
                except OSError:
                    time.sleep(.05)
            else:
                raise AssertionError('Native fixture did not bind loopback')
        cls.tls = ssl.create_default_context(cafile=str(cls.cert))

    def request(self, path, user='portal', data=None, method=None, headers=None):
        headers = dict(headers or {})
        if user:
            headers['Authorization'] = 'Basic ' + base64.b64encode((user + ':' + self.passwords[user]).encode()).decode()
        if data is not None:
            data = urllib.parse.urlencode(data).encode()
            headers['Content-Type'] = 'application/x-www-form-urlencoded'
        request = urllib.request.Request('https://localhost:' + str(self.port) + path, data=data, headers=headers, method=method)
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), urllib.request.HTTPSHandler(context=self.tls), NoRedirect())
        try:
            with opener.open(request, timeout=5) as response:
                return response.status, response.read()
        except urllib.error.HTTPError as error:
            return error.code, error.read()

    def test_renderer_refuses_empty_scope_before_overwriting_files(self):
        import copy
        values = copy.deepcopy(self.values)
        values['query_contexts'][0]['namespaces'] = []
        before = (self.folder / 'proxy-arguments.yaml').read_bytes()
        path = self.folder / 'invalid.yaml'
        path.write_text(yaml.safe_dump(values))
        result = subprocess.run(['ansible-playbook', '-i', 'localhost,', str(SOURCE / 'render.yaml'),
                                 '-e', '@' + str(path)], capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Empty or request-supplied namespace scope is forbidden', result.stdout)
        self.assertEqual((self.folder / 'proxy-arguments.yaml').read_bytes(), before)

    def test_renderer_refuses_port_and_credential_aliases(self):
        import copy
        for defect in ['port-string', 'credential-alias', 'listener-conflict']:
            values = copy.deepcopy(self.values)
            if defect == 'port-string':
                values['query_contexts'][1]['proxy_port'] = '0' + str(values['query_contexts'][0]['proxy_port'])
            elif defect == 'credential-alias':
                values['query_contexts'][1]['htpasswd_path'] = str(self.folder / 'unused/../portal.htpasswd')
            else:
                values['query_contexts'][1]['proxy_port'] = self.port
            before = (self.folder / 'proxy-arguments.yaml').read_bytes()
            path = self.folder / 'invalid.yaml'
            path.write_text(yaml.safe_dump(values))
            result = subprocess.run(['ansible-playbook', '-i', 'localhost,', str(SOURCE / 'render.yaml'),
                                     '-e', '@' + str(path)], capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0, defect)
            self.assertEqual((self.folder / 'proxy-arguments.yaml').read_bytes(), before)

    def test_authentication_required_and_context_bound(self):
        for path, user in [('/portal/api/v1/query?query=up', None),
                           ('/portal/api/v1/query?query=up', 'other'),
                           ('/other/api/v1/query?query=up', 'portal')]:
            before = len(self.backend.received)
            self.assertEqual(self.request(path, user=user)[0], 401)
            self.assertEqual(len(self.backend.received), before)

    def test_each_context_injects_its_own_namespace(self):
        for user in self.passwords:
            code, _ = self.request('/' + user + '/api/v1/query?query=up', user=user)
            self.assertEqual(code, 200)
            query = self.backend.received[-1][1]['query'][0]
            self.assertEqual(query, 'up{namespace="tenant-' + user + '"}')

    def test_join_scopes_every_selector(self):
        query = 'sum(rate(a[5m])) / sum(rate(b[5m]))'
        self.assertEqual(self.request('/portal/api/v1/query', data={'query': query})[0], 200)
        rewritten = self.backend.received[-1][1]['query'][0]
        self.assertEqual(rewritten.count('namespace="tenant-portal"'), 2)

    def test_cross_namespace_selectors_rejected(self):
        for query in ['up{namespace="tenant-other"}',
                      'up{namespace="tenant-portal-config"}', 'up{namespace=""}']:
            before = len(self.backend.received)
            code, _ = self.request('/portal/api/v1/query', data={'query': query})
            self.assertEqual(code, 400, query)
            self.assertEqual(len(self.backend.received), before)

    def test_broad_namespace_matcher_is_narrowed(self):
        self.assertEqual(self.request('/portal/api/v1/query', data={'query': 'up{namespace=~".*"}'})[0], 200)
        self.assertEqual(self.backend.received[-1][1]['query'], ['up{namespace="tenant-portal"}'])

    def test_caller_cannot_override_namespace_with_headers_or_body(self):
        code, _ = self.request('/portal/api/v1/query?namespace=tenant-other',
                               data={'query': 'up', 'namespace': 'tenant-other'},
                               headers={'X-Scope-OrgID': 'other', 'X-Tenant': 'other', 'X-Namespace': 'tenant-other'})
        self.assertEqual(code, 200)
        _, values, headers = self.backend.received[-1]
        self.assertEqual(values['query'], ['up{namespace="tenant-portal"}'])
        for header in ['Authorization', 'X-Scope-OrgID', 'X-Tenant', 'X-Namespace']:
            self.assertNotIn(header, headers)

    def test_range_query_is_scoped(self):
        query = urllib.parse.urlencode({'query': 'up', 'start': '1', 'end': '2', 'step': '1'})
        self.assertEqual(self.request('/portal/api/v1/query_range?' + query)[0], 200)
        self.assertEqual(self.backend.received[-1][1]['query'], ['up{namespace="tenant-portal"}'])

    def test_unreviewed_routes_and_methods_never_reach_upstream(self):
        for route in ['labels', 'label/namespace/values', 'metadata', 'series', 'rules', 'alerts',
                      'status/config', 'read', 'admin/tsdb/delete_series']:
            before = len(self.backend.received)
            self.assertEqual(self.request('/portal/api/v1/' + route)[0], 404)
            self.assertEqual(len(self.backend.received), before)
        for path in ['/api/v1/query?query=up', '/platform/api/v1/query?query=up', '/metrics', '/-/reload']:
            self.assertEqual(self.request(path)[0], 404)
        self.assertEqual(self.request('/portal/api/v1/query?query=up', method='DELETE')[0], 403)

    def test_invalid_promql_does_not_reach_upstream(self):
        before = len(self.backend.received)
        self.assertEqual(self.request('/portal/api/v1/query', data={'query': 'bad('})[0], 400)
        self.assertEqual(len(self.backend.received), before)


if __name__ == '__main__':
    unittest.main()
