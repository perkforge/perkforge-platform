"""Native ntfy fixture, synthetic events/credentials on loopback, never live Flux."""
import json
import os
from pathlib import Path
import re
import shutil
import socket
import subprocess
import tempfile
import time
import unittest
import urllib.error
import urllib.request
import yaml
from jinja2 import Environment, StrictUndefined
from fixtures.render_helpers import build

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / 'configuration/observability/deployment-notifications'
SENTINEL = 'SYNTHETIC-PRIVATE-ERROR-DO-NOT-PUBLISH'


class FluxNotificationContract(unittest.TestCase):
    def test_eso_grant_is_named_merge_only_without_secret_creation(self):
        env = Environment(undefined=StrictUndefined)
        env.filters['to_json'] = json.dumps
        rendered = env.from_string((SOURCE / 'consumers.yaml.j2').read_text()).render(ntfy_bao_server='https://bao.example.invalid')
        objects = list(yaml.safe_load_all(rendered))
        role = next(x for x in objects if x['kind'] == 'Role')
        self.assertEqual(role['metadata']['namespace'], 'flux-system')
        rule = next(r for r in role['rules'] if 'secrets' in r['resources'])
        self.assertEqual(rule, {'apiGroups': [''], 'resources': ['secrets'],
                         'resourceNames': ['flux-deployment-publisher'], 'verbs': ['get', 'update', 'patch']})
        self.assertFalse(any(x['kind'] in {'ClusterRole', 'ClusterRoleBinding', 'NetworkPolicy'} for x in objects))
        external = next(x for x in objects if x['kind'] == 'ExternalSecret')
        self.assertEqual(external['spec']['target']['creationPolicy'], 'Merge')
        self.assertEqual({x['secretKey'] for x in external['spec']['data']}, {'headers', 'ca.crt'})
        secret = next(x for x in objects if x['kind'] == 'Secret')
        self.assertNotIn('data', secret)
        self.assertNotIn('stringData', secret)

    def test_opt_in_root_only_adds_notifications_and_template_mount(self):
        identity = lambda x: (x['kind'], x['metadata'].get('namespace'), x['metadata']['name'])
        before = {identity(x): x for x in build(ROOT / 'clusters/local-platform-alerts')}
        after = {identity(x): x for x in build(ROOT / 'clusters/local-deployment-notifications')}
        self.assertTrue(set(before).issubset(after))
        self.assertEqual({x[0] for x in set(after) - set(before)}, {'ConfigMap', 'Provider', 'Alert'})
        for key in before:
            if key == ('StatefulSet', 'ntfy', 'ntfy'):
                pod = after[key]['spec']['template']['spec']
                # Strategic merge order is not significant; remove only the new named entries.
                pod['volumes'] = [x for x in pod['volumes'] if x['name'] != 'deployment-template']
                container = next(x for x in pod['containers'] if x['name'] == 'ntfy')
                self.assertTrue(any(x['name'] == 'deployment-template' and x['readOnly'] for x in container['volumeMounts']))
                container['volumeMounts'] = [x for x in container['volumeMounts'] if x['name'] != 'deployment-template']
            self.assertEqual(after[key], before[key], key)

    def test_default_off_exact_sources_and_credential_contract(self):
        objects = build(SOURCE)
        provider = next(x for x in objects if x['kind'] == 'Provider')
        alert = next(x for x in objects if x['kind'] == 'Alert')
        for obj in (provider, alert):
            self.assertTrue(obj['spec']['suspend'])
            self.assertEqual(obj['metadata']['namespace'], 'flux-system')
        self.assertEqual(provider['spec']['type'], 'generic')
        self.assertEqual(provider['spec']['secretRef'], {'name': 'flux-deployment-publisher'})
        self.assertEqual(provider['spec']['certSecretRef'], provider['spec']['secretRef'])
        self.assertEqual(provider['spec']['address'], 'https://ntfy.UNCONFIGURED.invalid/platform-deployments?template=flux-deployment')
        self.assertEqual(alert['spec']['eventMetadata'], {'environment': 'UNCONFIGURED'})
        sources = alert['spec']['eventSources']
        self.assertEqual(sources, [{'kind': 'HelmRelease', 'name': '*', 'namespace': 'bigbang'}])
        self.assertFalse(any(x['kind'] in {'Secret', 'Deployment', 'Role', 'ClusterRole', 'NetworkPolicy'} for x in objects))
        self.assertFalse(any(x['metadata']['name'] == 'platform-deployments' for x in build(ROOT / 'clusters/local')))

    def test_exact_message_filter_excludes_reconcile_and_source_spam(self):
        alert = next(x for x in build(SOURCE) if x['kind'] == 'Alert')
        patterns = [re.compile(x) for x in alert['spec']['inclusionList']]
        for action in ('install', 'upgrade'):
            for result in ('succeeded', 'failed'):
                self.assertTrue(any(p.search(f'Helm {action} {result} for release mattermost/mattermost with chart mattermost@11.11.0-bb.0') for p in patterns))
        for message in ('Reconciliation finished in 2s', 'stored artifact for revision main@sha1:123',
                        'Release is in sync', 'HelmChart created', 'prefix Helm install succeeded for release foo'):
            self.assertFalse(any(p.search(message) for p in patterns), message)


class FluxNtfyNative(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        binary = os.environ.get('NTFY_VALIDATE_BIN')
        if not binary:
            raise unittest.SkipTest('NTFY_VALIDATE_BIN required; no binary download')
        cls.env = {k: v for k, v in os.environ.items() if not k.startswith('NTFY_')}
        cls.binary = binary
        version = subprocess.check_output([binary, '--version'], text=True, env=cls.env).strip()
        if version != 'ntfy version 2.37.2':
            raise AssertionError('Pinned native ntfy 2.37.2 required')
        cls.tmp = tempfile.TemporaryDirectory(); cls.addClassCleanup(cls.tmp.cleanup)
        cls.folder = Path(cls.tmp.name)
        templates = cls.folder / 'templates'; templates.mkdir()
        shutil.copyfile(SOURCE / 'flux-deployment.yml', templates / 'flux-deployment.yml')
        with socket.socket() as sock:
            sock.bind(('127.0.0.1', 0)); port = sock.getsockname()[1]
        cls.url = f'http://127.0.0.1:{port}'
        cls.config = cls.folder / 'server.yml'
        cls.config.write_text(yaml.safe_dump({'base-url': cls.url, 'listen-http': f'127.0.0.1:{port}',
            'auth-file': str(cls.folder / 'auth.db'), 'auth-default-access': 'deny-all',
            'cache-file': str(cls.folder / 'cache.db'), 'cache-duration': '10m',
            'attachment-cache-dir': '', 'upstream-base-url': '', 'web-root': 'disable',
            'template-dir': str(templates), 'log-level': 'WARN'}))
        cls.config.chmod(0o600)
        cls.log = (cls.folder / 'server.log').open('w'); cls.addClassCleanup(cls.log.close)
        cls.process = subprocess.Popen([binary, 'serve', '--config', str(cls.config)], env=cls.env,
                                       stdout=cls.log, stderr=subprocess.STDOUT)
        def stop():
            cls.process.terminate()
            try: cls.process.wait(timeout=5)
            except subprocess.TimeoutExpired: cls.process.kill(); cls.process.wait(timeout=5)
        cls.addClassCleanup(stop)
        for _ in range(100):
            if cls.process.poll() is not None:
                raise AssertionError('Synthetic native ntfy fixture failed to start')
            try:
                with socket.create_connection(('127.0.0.1', port), timeout=.1): break
            except OSError: time.sleep(.05)
        else: raise AssertionError('Native ntfy did not bind loopback')
        cls.tokens = {}
        for user, permission in [('fixture-publisher', 'write-only'), ('fixture-reader', 'read-only')]:
            created = subprocess.run([binary, 'user', '--config', str(cls.config), 'add', user],
                           env={**cls.env, 'NTFY_PASSWORD': 'synthetic-only-password-not-production'}, capture_output=True, text=True)
            if created.returncode:
                raise AssertionError('Synthetic fixture user setup: ' + created.stderr)
            subprocess.run([binary, 'access', '--config', str(cls.config), user, 'platform-deployments', permission],
                           check=True, env=cls.env, capture_output=True)
            result = subprocess.run([binary, 'token', '--config', str(cls.config), 'add', user],
                                    check=True, capture_output=True, text=True, env=cls.env)
            match = re.search(r'tk_[A-Za-z0-9]+', result.stdout + result.stderr)
            if not match:
                raise AssertionError('Native synthetic token creation did not return a token')
            cls.tokens[user] = match.group()

    def request(self, method, path, user=None, payload=None):
        headers = {'Content-Type': 'application/json'}
        if user: headers['Authorization'] = 'Bearer ' + self.tokens[user]
        request = urllib.request.Request(self.url + path, method=method, headers=headers,
                                         data=json.dumps(payload).encode() if payload is not None else None)
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        try:
            with opener.open(request, timeout=5) as response: return response.status, response.read().decode()
        except urllib.error.HTTPError as error: return error.code, error.read().decode()

    def event(self, reason='UpgradeSucceeded'):
        return {'involvedObject': {'kind': 'HelmRelease', 'apiVersion': 'helm.toolkit.fluxcd.io/v2',
                'name': 'mattermost', 'namespace': 'bigbang'}, 'reason': reason,
                'severity': 'error' if reason.endswith('Failed') else 'info',
                'timestamp': '2026-11-14T00:00:00Z', 'message': SENTINEL,
                'reportingController': 'helm-controller', 'reportingInstance': SENTINEL,
                'metadata': {'environment': 'local', 'revision': '11.11.0-bb.0',
                             'app-version': '11.11.0', 'token': SENTINEL, 'link': 'https://evil.invalid/' + SENTINEL}}

    def test_native_outcomes_are_bounded_and_cached_without_raw_errors(self):
        for reason in ('InstallSucceeded', 'UpgradeSucceeded', 'InstallFailed', 'UpgradeFailed'):
            code, body = self.request('POST', '/platform-deployments?template=flux-deployment', 'fixture-publisher', self.event(reason))
            self.assertEqual(code, 200, body)
            result = json.loads(body)
            self.assertEqual(result['title'], {'InstallSucceeded': 'Helm release installed',
                             'UpgradeSucceeded': 'Helm release upgraded', 'InstallFailed': 'Helm release failed',
                             'UpgradeFailed': 'Helm release failed'}[reason])
            self.assertIn('App: mattermost.', result['message'])
            self.assertIn('Environment: local.', result['message'])
            self.assertIn('Chart version: 11.11.0-bb.0.', result['message'])
            self.assertIn('App version (chart metadata): 11.11.0.', result['message'])
            self.assertIn('Source: https://github.com/perkforge/perkforge-platform', result['message'])
            self.assertNotIn(SENTINEL, body)
            self.assertLess(len(result['message']), 700)
        code, body = self.request('GET', '/platform-deployments/json?poll=1&since=all', 'fixture-reader')
        self.assertEqual(code, 200, body)
        self.assertNotIn(SENTINEL, body)
        self.assertNotIn(SENTINEL, (self.folder / 'server.log').read_text())

    def test_missing_and_oversized_versions_do_not_invent_or_overflow(self):
        payload = self.event(); payload['metadata'] = {'environment': 'local'}
        code, body = self.request('POST', '/platform-deployments?template=flux-deployment', 'fixture-publisher', payload)
        self.assertEqual(code, 200, body)
        self.assertIn('Chart version: unavailable.', json.loads(body)['message'])
        payload['metadata'].update({'revision': 'a' * 1000, 'app-version': 'b' * 1000})
        code, body = self.request('POST', '/platform-deployments?template=flux-deployment', 'fixture-publisher', payload)
        self.assertEqual(code, 200, body)
        self.assertLess(len(json.loads(body)['message']), 700)

    def test_exact_topic_publisher_and_reader_denials(self):
        for method, path, user, payload in [
            ('POST', '/platform-deployments?template=flux-deployment', None, self.event()),
            ('POST', '/platform-deployments?template=flux-deployment', 'fixture-reader', self.event()),
            ('GET', '/platform-deployments/json?poll=1', 'fixture-publisher', None),
            ('POST', '/platform-alerts?template=flux-deployment', 'fixture-publisher', self.event()),
            ('POST', '/tenant-portal-alerts?template=flux-deployment', 'fixture-publisher', self.event())]:
            code, _ = self.request(method, path, user, payload)
            self.assertIn(code, (401, 403), (method, path, code))
