"""Optional pilot render: protected inputs, verified TLS, and preserved services."""
from pathlib import Path
import os
import unittest
import yaml
from fixtures.render_helpers import build, helm, ordered_values, child_values, release_name

ROOT = Path(__file__).resolve().parents[2]


class LoggingPilot(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sources = Path(os.environ['PREFLIGHT_SOURCES_DIR'])
        cls.root = build(ROOT / 'clusters/local-logging-pilot')
        cls.parent = next(x for x in cls.root if x['kind'] == 'HelmRelease' and x['metadata']['name'] == 'bigbang')
        cls.outer = helm(cls.sources / 'bigbang/chart', 'bigbang', 'bigbang', ordered_values(cls.root, cls.parent))

    def test_preserves_nextcloud_and_existing_app_workloads(self):
        def key(x):
            return (x['kind'], x['metadata'].get('namespace'), x['metadata']['name'])
        current = {key(x): x for x in self.root}
        for obj in build(ROOT / 'clusters/local-nextcloud'):
            if key(obj) != ('HelmRelease', 'bigbang', 'bigbang'):
                self.assertEqual(current[key(obj)], obj)
        before = build(ROOT / 'clusters/local-metrics-pilot')
        parent = next(x for x in before if key(x) == ('HelmRelease', 'bigbang', 'bigbang'))
        baseline = helm(self.sources / 'bigbang/chart', 'bigbang', 'bigbang', ordered_values(before, parent))
        for name in ('gitlab', 'gitlab-runner', 'headlamp', 'keycloak'):
            rendered = []
            for outer in (baseline, self.outer):
                hr = next(x for x in outer if x['kind'] == 'HelmRelease' and x['metadata']['name'] == name)
                rendered.append(helm(self.sources / name / 'chart', release_name(hr), hr['spec']['targetNamespace'], child_values(outer, name)))
            self.assertEqual(rendered[0], rendered[1], name)

    def test_grafana_uses_only_authenticated_tls_gateway_with_protected_references(self):
        hr = next(x for x in self.outer if x['kind'] == 'HelmRelease' and x['metadata']['name'] == 'grafana')
        child = helm(self.sources / 'grafana/chart', release_name(hr), hr['spec']['targetNamespace'], child_values(self.outer, 'grafana'))
        config = next(x['data'] for x in child if x['kind'] == 'ConfigMap' and 'datasourcesbb.yaml' in x.get('data', {}))
        datasources = yaml.safe_load(config['datasourcesbb.yaml'])['datasources']
        self.assertEqual({x['uid'] for x in datasources}, {'prometheus', 'loki-pilot'})
        loki = next(x for x in datasources if x['uid'] == 'loki-pilot')
        self.assertEqual(loki['url'], 'https://logging-loki-gateway.logging.svc.cluster.local')
        self.assertTrue(loki['basicAuth']); self.assertFalse(loki['editable'])
        self.assertFalse(loki['jsonData']['tlsSkipVerify'])
        self.assertEqual(loki['secureJsonData'], {'basicAuthPassword': '$LOKI_PASSWORD', 'tlsCACert': '$LOKI_CA_CERT'})
        self.assertNotIn('X-Scope-OrgID', str(loki))
        pod = next(x['spec']['template']['spec'] for x in child if x['kind'] == 'Deployment')
        env = {x['name']: x for c in pod['containers'] for x in c.get('env', [])}
        for name, field in (('LOKI_USERNAME', 'username'), ('LOKI_PASSWORD', 'password')):
            self.assertEqual(env[name]['valueFrom']['secretKeyRef'], {'name': 'loki-query-auth', 'key': field})
        self.assertEqual(env['LOKI_CA_CERT']['valueFrom']['configMapKeyRef'], {'name': 'loki-ca', 'key': 'ca.crt'})
        self.assertIn('[auth.anonymous]\nenabled = false', config['grafana.ini'])
        self.assertFalse(any(x['kind'] in ('Secret', 'Ingress') for x in child))

    def test_stage_has_no_public_routes_and_keeps_failed_rollout_state(self):
        releases = {x['metadata']['name']: x for x in self.outer if x['kind'] == 'HelmRelease'}
        for name in ('alloy', 'loki'):
            spec = releases[name]['spec']
            self.assertFalse(spec['suspend'])
            self.assertFalse(spec['install']['remediation']['remediateLastFailure'])
            self.assertFalse(spec['upgrade']['cleanupOnFail'])
        self.assertFalse(any(x['kind'] in ('Ingress', 'HTTPRoute', 'Gateway') for x in self.outer))
