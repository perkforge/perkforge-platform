"""Native Grafana/Prometheus synthetic data test. No live cluster access."""
import base64
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import hashlib
import json
import os
from pathlib import Path
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
from integration.test_tenant_query_gateway import SOURCE, ROOT, port, NoRedirect


class Metrics(BaseHTTPRequestHandler):
    def do_GET(self):
        payload = {'/portal': 'fixture_value{namespace="tenant-other",source="portal"} 11\n',
                   '/other': 'fixture_value{source="other"} 22\n',
                   '/unknown': 'fixture_value{source="unmapped"} 33\n'}[self.path].encode()
        self.send_response(200)
        self.send_header('Content-Type', 'text/plain; version=0.0.4')
        self.end_headers(); self.wfile.write(payload)
    def log_message(self, *args):
        pass


class NativeTenantDataPlane(unittest.TestCase):
    backend_sidecar = False
    @classmethod
    def setUpClass(cls):
        names = {'prom_label_proxy': 'PROM_LABEL_PROXY_BIN', 'prometheus': 'PROMETHEUS_VALIDATE_BIN', 'grafana': 'GRAFANA_VALIDATE_BIN'}
        if any(not os.environ.get(value) for value in names.values()):
            raise unittest.SkipTest('Provide the three checksum-pinned native binaries; no downloads performed')
        pins = yaml.safe_load((SOURCE / 'sources.yaml').read_text())
        binaries = {name: os.environ[key] for name, key in names.items()}
        for name, binary in binaries.items():
            if hashlib.sha256(Path(binary).read_bytes()).hexdigest() != pins[name]['linux_amd64_binary_sha256']:
                raise AssertionError('Unexpected native binary: ' + name)
        cls.tmp = tempfile.TemporaryDirectory(); cls.addClassCleanup(cls.tmp.cleanup)
        cls.folder = Path(cls.tmp.name)
        cls.processes = []
        def stop():
            for p in reversed(cls.processes):
                p.terminate()
                try: p.wait(timeout=5)
                except subprocess.TimeoutExpired: p.kill(); p.wait(timeout=5)
        cls.addClassCleanup(stop)
        cert = cls.folder / 'cert.pem'; key = cls.folder / 'key.pem'
        subprocess.run(['openssl', 'req', '-x509', '-newkey', 'rsa:2048', '-nodes', '-keyout', str(key), '-out', str(cert), '-days', '1', '-subj', '/CN=localhost', '-addext', 'subjectAltName=DNS:localhost'], check=True, capture_output=True)
        key.chmod(0o600)
        cls.cert = cert
        cls.tls = ssl.create_default_context(cafile=str(cert))
        cls.exporter = ThreadingHTTPServer(('127.0.0.1', 0), Metrics)
        cls.addClassCleanup(cls.exporter.server_close); cls.addClassCleanup(cls.exporter.shutdown)
        threading.Thread(target=cls.exporter.serve_forever, daemon=True).start()
        cls.prom_port, cls.gateway_port, cls.grafana_port = port(), port(), port()
        jobs = []
        for name in ['portal', 'other', 'unknown']:
            labels = {} if name == 'unknown' else {'namespace': 'tenant-' + name}
            jobs.append({'job_name': name, 'honor_labels': False, 'metrics_path': '/' + name,
                         'static_configs': [{'targets': ['127.0.0.1:' + str(cls.exporter.server_port)], 'labels': labels}]})
        (cls.folder / 'prometheus.yaml').write_text(yaml.safe_dump({'global': {'scrape_interval': '1s'}, 'scrape_configs': jobs}))
        (cls.folder / 'web.yaml').write_text(yaml.safe_dump({'tls_server_config': {'cert_file': str(cert), 'key_file': str(key), 'client_auth_type': 'RequireAndVerifyClientCert', 'client_ca_file': str(cert)}}))
        cls.local_prom_port = port() if cls.backend_sidecar else cls.prom_port
        prom_args = [binaries['prometheus'], '--config.file=' + str(cls.folder / 'prometheus.yaml'), '--web.enable-lifecycle', '--storage.tsdb.path=' + str(cls.folder / 'tsdb'), '--web.listen-address=127.0.0.1:' + str(cls.local_prom_port)]
        if not cls.backend_sidecar:
            prom_args.append('--web.config.file=' + str(cls.folder / 'web.yaml'))
        cls.start(prom_args, 'prometheus')
        if cls.backend_sidecar:
            from jinja2 import Environment, StrictUndefined
            config = Environment(undefined=StrictUndefined).from_string((SOURCE / 'backend-nginx.conf.j2').read_text()).render(
                runtime_dir=str(cls.folder), backend_listen_address='127.0.0.1:' + str(cls.prom_port),
                certificate_path=str(cert), private_key_path=str(key), client_ca_path=str(cert),
                prometheus_loopback_port=cls.local_prom_port)
            backend_config = cls.folder / 'backend-nginx.conf'; backend_config.write_text(config)
            cls.start([os.environ.get('NGINX_VALIDATE_BIN', '/usr/sbin/nginx'), '-c', str(backend_config), '-p', str(cls.folder), '-g', 'daemon off;'], 'backend-nginx')
        contexts = []
        for name in ['portal', 'other', 'platform']:
            hashed = subprocess.run(['openssl', 'passwd', '-apr1', '-stdin'], input='synthetic-' + name, text=True, capture_output=True, check=True).stdout.strip()
            auth = cls.folder / (name + '.htpasswd'); auth.write_text(name + ':' + hashed + '\n'); auth.chmod(0o600)
            if name != 'platform':
                contexts.append({'id': name, 'proxy_port': port(), 'namespaces': ['tenant-' + name], 'htpasswd_path': str(auth)})
        values = dict(tenant_query_render_enabled=True, query_contexts=contexts, runtime_dir=str(cls.folder),
                      metrics_upstream='https://localhost:' + str(cls.prom_port), upstream_tls_name='localhost',
                      upstream_ca_path=str(cert), upstream_client_cert_path=str(cert), upstream_client_key_path=str(key),
                      platform_query={'htpasswd_path': str(cls.folder / 'platform.htpasswd')},
                      certificate_path=str(cert), private_key_path=str(key), server_name='localhost', listen_address='127.0.0.1:' + str(cls.gateway_port))
        variables = cls.folder / 'vars.yaml'; variables.write_text(yaml.safe_dump(values))
        result = subprocess.run(['ansible-playbook', '-i', 'localhost,', str(SOURCE / 'render.yaml'), '-e', '@' + str(variables)], capture_output=True, text=True)
        if result.returncode: raise AssertionError(result.stdout + result.stderr)
        for item in yaml.safe_load((cls.folder / 'proxy-arguments.yaml').read_text()):
            cls.start([binaries['prom_label_proxy']] + item['arguments'], item['context'])
        cls.start([os.environ.get('NGINX_VALIDATE_BIN', '/usr/sbin/nginx'), '-c', str(cls.folder / 'nginx.conf'), '-p', str(cls.folder), '-g', 'daemon off;'], 'nginx')
        cls.gateway = 'https://localhost:' + str(cls.gateway_port)
        cls.grafana = 'http://127.0.0.1:' + str(cls.grafana_port)
        config = cls.folder / 'grafana.ini'
        config.write_text('[server]\nhttp_addr=127.0.0.1\nhttp_port=' + str(cls.grafana_port) + '\n[paths]\ndata=' + str(cls.folder / 'grafana-data') + '\nlogs=' + str(cls.folder / 'grafana-logs') + '\nplugins=' + str(cls.folder / 'plugins') + '\nprovisioning=' + str(cls.folder / 'provisioning') + '\n[security]\nadmin_user=fixture-admin\nadmin_password=synthetic-admin\n' + (cls.folder / 'grafana-security.ini').read_text() + '\n[analytics]\nreporting_enabled=false\ncheck_for_updates=false\ncheck_for_plugin_updates=false\n[plugins]\npreinstall_disabled=true\n')
        home = str(Path(binaries['grafana']).resolve().parents[1])
        cls.start([binaries['grafana'], 'server', '--homepath', home, '--config', str(config)], 'grafana')
        for _ in range(150):
            try:
                status, _ = cls.http(cls.grafana + '/api/health')
                if status == 200: break
            except (OSError, urllib.error.URLError): pass
            if any(p.poll() is not None for p in cls.processes):
                raise AssertionError('Synthetic fixture process exited: ' + '\n'.join(p.name + ': ' + p.read_text()[-3000:] for p in cls.folder.glob('*.log')))
            time.sleep(.1)
        else: raise AssertionError('Grafana failed to become healthy')
        status, org = cls.api('/api/orgs', data={'name': 'synthetic-portal'})
        if status != 200: raise AssertionError(org)
        cls.org = org['orgId']
        for login, role in [('tenant-admin', 'Admin'), ('tenant-developer', 'Editor'), ('tenant-viewer', 'Viewer')]:
            status, user = cls.api('/api/admin/users', data={'name': login, 'login': login, 'password': 'synthetic-user'})
            if status != 200: raise AssertionError(user)
            added, detail = cls.api('/api/orgs/' + str(cls.org) + '/users', data={'loginOrEmail': login, 'role': role})
            if added != 200: raise AssertionError(detail)
            removed, detail = cls.api('/api/orgs/1/users/' + str(user['id']), method='DELETE')
            if removed != 200: raise AssertionError(detail)
        cls.create_source('portal', cls.gateway + '/portal', 'portal', org=cls.org)
        cls.create_source('platform', cls.gateway + '/platform', 'platform')
        for _ in range(100):
            status, result = cls.query('platform', user='fixture-admin')
            if status == 200 and len(result.get('data', {}).get('result', [])) == 3: break
            time.sleep(.1)
        else: raise AssertionError('Synthetic metrics not ready: ' + str(result))

    @classmethod
    def start(cls, args, name):
        output = (cls.folder / (name + '.log')).open('w'); cls.addClassCleanup(output.close)
        cls.processes.append(subprocess.Popen(args, stdout=output, stderr=subprocess.STDOUT))

    @classmethod
    def http(cls, url, user=None, password=None, data=None, method=None, headers=None, tls=None):
        headers = dict(headers or {})
        if user: headers['Authorization'] = 'Basic ' + base64.b64encode((user + ':' + password).encode()).decode()
        if data is not None: headers['Content-Type'] = 'application/json'; data = json.dumps(data).encode()
        request = urllib.request.Request(url, data=data, method=method, headers=headers)
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), urllib.request.HTTPSHandler(context=tls or cls.tls), NoRedirect())
        try:
            with opener.open(request, timeout=5) as response: code, body = response.status, response.read()
        except urllib.error.HTTPError as error: code, body = error.code, error.read()
        try: return code, json.loads(body)
        except ValueError: return code, body.decode()

    @classmethod
    def api(cls, path, user='fixture-admin', data=None, method=None, org=None):
        return cls.http(cls.grafana + path, user=user, password='synthetic-admin' if user == 'fixture-admin' else 'synthetic-user', data=data, method=method, headers={'X-Grafana-Org-Id': str(org)} if org else {})

    @classmethod
    def create_source(cls, uid, url, credential, user='fixture-admin', org=None):
        code, result = cls.api('/api/datasources', user=user, org=org, data={'uid': uid, 'name': uid, 'type': 'prometheus', 'access': 'proxy', 'url': url, 'basicAuth': True, 'basicAuthUser': credential, 'jsonData': {'tlsAuthWithCACert': True}, 'secureJsonData': {'basicAuthPassword': 'synthetic-' + credential, 'tlsCACert': cls.cert.read_text()}})
        if code != 200: raise AssertionError(result)

    @classmethod
    def query(cls, uid, user='tenant-viewer', expr='fixture_value'):
        return cls.api('/api/datasources/proxy/uid/' + uid + '/api/v1/query?' + urllib.parse.urlencode({'query': expr}), user=user)

    def test_roles_only_receive_runtime_namespace_data(self):
        for user in ['tenant-admin', 'tenant-developer', 'tenant-viewer']:
            code, result = self.query('portal', user=user)
            self.assertEqual(code, 200, result)
            series = result['data']['result']; self.assertEqual(len(series), 1)
            self.assertEqual(series[0]['metric']['namespace'], 'tenant-portal')
            self.assertEqual(series[0]['metric']['source'], 'portal')
            self.assertEqual(series[0]['metric']['exported_namespace'], 'tenant-other')

    def test_platform_sees_all_and_unmapped_data(self):
        code, result = self.query('platform', user='fixture-admin')
        self.assertEqual(code, 200)
        self.assertEqual({x['metric']['source'] for x in result['data']['result']}, {'portal', 'other', 'unmapped'})

    def test_cross_org_datasource_id_denied(self):
        self.assertEqual(self.query('platform', user='tenant-admin')[0], 404)

    def test_admin_custom_datasource_cannot_use_platform_route(self):
        self.create_source('attempt-platform', self.gateway + '/platform', 'portal', user='tenant-admin')
        code, result = self.query('attempt-platform', user='tenant-admin')
        self.assertEqual(code, 400, result)
        self.assertEqual(result, 'Authentication to data source failed')

    def test_admin_custom_datasource_cannot_use_other_tenant_route(self):
        self.create_source('attempt-other', self.gateway + '/other', 'portal', user='tenant-admin')
        code, result = self.query('attempt-other', user='tenant-admin')
        self.assertEqual(code, 400, result)
        self.assertEqual(result, 'Authentication to data source failed')

    def test_admin_custom_datasource_direct_backend_blocked(self):
        self.create_source('attempt-direct', 'https://localhost:' + str(self.prom_port), 'portal', user='tenant-admin')
        self.assertEqual(self.query('attempt-direct', user='tenant-admin')[0], 403)

    def test_raw_backend_requires_client_certificate(self):
        if self.backend_sidecar:
            # Nginx completes TLS then rejects absent client authentication with 400.
            self.assertEqual(self.http('https://localhost:' + str(self.prom_port) + '/api/v1/query?query=fixture_value')[0], 400)
        else:
            with self.assertRaises((urllib.error.URLError, ssl.SSLError, OSError)):
                self.http('https://localhost:' + str(self.prom_port) + '/api/v1/query?query=fixture_value')

    def test_tenant_cannot_select_platform_org_header(self):
        code, _ = self.api('/api/datasources', user='tenant-admin', org=1)
        self.assertEqual(code, 403)

    def test_query_model_direct_backend_still_cannot_return_data(self):
        self.create_source('model-direct', 'https://localhost:' + str(self.prom_port), 'portal', user='tenant-admin')
        code, result = self.api('/api/ds/query', user='tenant-admin', data={'from': 'now-5m', 'to': 'now', 'queries': [{'refId': 'A', 'datasource': {'type': 'prometheus', 'uid': 'model-direct'}, 'expr': 'fixture_value', 'instant': True, 'range': False, 'intervalMs': 1000, 'maxDataPoints': 1000}]})
        self.assertNotEqual(code, 200, result)
        # Grafana may attach an empty diagnostic frame on HTTP auth errors.
        for frame in result.get('results', {}).get('A', {}).get('frames', []):
            self.assertFalse(frame.get('schema', {}).get('fields'))
            self.assertFalse(frame.get('data', {}).get('values'))
        self.assertIn('error', result.get('results', {}).get('A', {}))

    def test_query_model_api_is_also_scoped(self):
        code, result = self.api('/api/ds/query', user='tenant-admin', data={'from': 'now-5m', 'to': 'now', 'queries': [{'refId': 'A', 'datasource': {'type': 'prometheus', 'uid': 'portal'}, 'expr': 'fixture_value', 'instant': True, 'range': False, 'intervalMs': 1000, 'maxDataPoints': 1000}]})
        self.assertEqual(code, 200, result)
        frames = result['results']['A']['frames']; self.assertTrue(frames)
        labels = [field['labels'] for frame in frames for field in frame['schema']['fields'] if field.get('labels')]
        self.assertTrue(labels)
        self.assertEqual({x['namespace'] for x in labels}, {'tenant-portal'})




class NativeLoopbackBackend(NativeTenantDataPlane):
    """Same Grafana bypass suite behind loopback HTTP + authenticated TLS sidecar.

    This is a localhost process proof, not an Operator reconciliation/CNI test.
    """
    backend_sidecar = True

    def test_local_operator_probe_and_reload_paths_work(self):
        for path in ['/-/ready', '/-/healthy']:
            self.assertEqual(self.http('http://127.0.0.1:' + str(self.local_prom_port) + path)[0], 200)
        self.assertEqual(self.http('http://127.0.0.1:' + str(self.local_prom_port) + '/-/reload', method='POST')[0], 200)

    def test_authenticated_self_scrape_and_lifecycle_denial(self):
        tls = ssl.create_default_context(cafile=str(self.cert))
        tls.load_cert_chain(str(self.cert), str(self.folder / 'key.pem'))
        url = 'https://localhost:' + str(self.prom_port)
        code, metrics = self.http(url + '/metrics', tls=tls)
        self.assertEqual(code, 200); self.assertIn('prometheus_build_info', metrics)
        for path in ['/-/reload', '/-/quit', '/api/v1/admin/tsdb/delete_series']:
            self.assertEqual(self.http(url + path, method='POST', tls=tls)[0], 404)


if __name__ == '__main__': unittest.main()
