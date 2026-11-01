"""Pinned Rancher bootstrap lookups and rendered delegation, synthetic APIs only."""
import base64
from copy import deepcopy
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

import yaml
from fixtures.lookup_server import lookup_server
from fixtures.render_helpers import build, helm, ordered_values, release_name

ROOT = Path(__file__).resolve().parents[2]
DUMMY = 'synthetic-offline-bootstrap-only'


class RancherInstallerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.chart = Path(os.environ['PREFLIGHT_SOURCES_DIR']) / 'rancher'
        root = build(ROOT / 'clusters/local')
        parent = next(o for o in root if o['kind'] == 'HelmRelease')
        outer = helm(cls.chart.parent / 'bigbang/chart', 'bigbang', 'bigbang', ordered_values(root, parent))
        cls.hr = next(o for o in outer if o['kind'] == 'HelmRelease' and o['metadata']['name'] == 'rancher')
        cls.values = next(o for o in outer if o['kind'] == 'Secret' and o['metadata']['name'] == 'rancher-values')['stringData']['values.yaml']
        cls.objects = helm(cls.chart, release_name(cls.hr), 'cattle-system', [cls.values, 'bootstrapPassword: ' + DUMMY])
        cls.foundation = build(ROOT / 'configuration/packages/bigbang/prerequisites') + build(ROOT / 'configuration/packages/rancher/prerequisites')
        roles = {(o['kind'], o['metadata'].get('namespace'), o['metadata']['name']): o for o in cls.foundation if o['kind'] in ['Role', 'ClusterRole']}
        cls.policies = []
        for binding in cls.foundation:
            if binding['kind'] not in ['RoleBinding', 'ClusterRoleBinding'] or {'kind': 'ServiceAccount', 'name': 'rancher-installer', 'namespace': 'bigbang'} not in binding['subjects']:
                continue
            ref = binding['roleRef']; namespace = binding['metadata'].get('namespace') if ref['kind'] == 'Role' else None
            cls.policies.append(roles[ref['kind'], namespace, ref['name']])
        cls.target_role = next(o for o in cls.policies if o['kind'] == 'Role' and o['metadata']['namespace'] == 'cattle-system')

    def allowed(self, namespace, resource, name, verb, group='rbac.authorization.k8s.io'):
        return any(group in rule['apiGroups'] and resource in rule['resources'] and verb in rule['verbs']
                   and (not rule.get('resourceNames') or name in rule['resourceNames'])
                   for policy in self.policies if policy['kind'] == 'ClusterRole' or policy['metadata']['namespace'] == namespace
                   for rule in policy['rules'])

    def test_all_objects_roles_binding_targets_and_hook_scopes(self):
        self.assertEqual(len(self.objects), 14)
        resources = {'PriorityClass': 'priorityclasses', 'ServiceAccount': 'serviceaccounts', 'ConfigMap': 'configmaps',
                     'ClusterRoleBinding': 'clusterrolebindings', 'Service': 'services', 'Deployment': 'deployments',
                     'Ingress': 'ingresses', 'Secret': 'secrets', 'ClusterRole': 'clusterroles', 'Job': 'jobs'}
        for obj in self.objects:
            kind = obj['kind']; namespace = None if kind in ['PriorityClass', 'ClusterRole', 'ClusterRoleBinding'] else 'cattle-system'
            group = obj['apiVersion'].split('/')[0] if '/' in obj['apiVersion'] else ''
            for verb in ['get', 'create', 'update', 'patch', 'delete']:
                with self.subTest(kind=kind, name=obj['metadata']['name'], verb=verb):
                    self.assertTrue(self.allowed(namespace, resources[kind], obj['metadata']['name'], verb, group))
            if kind == 'ClusterRole':
                self.assertTrue(self.allowed(None, 'clusterroles', obj['metadata']['name'], 'escalate'))
            if kind == 'ClusterRoleBinding':
                self.assertTrue(self.allowed(None, 'clusterroles', obj['roleRef']['name'], 'bind'))
        bindings = [o for o in self.objects if o['kind'] == 'ClusterRoleBinding']
        self.assertEqual({o['roleRef']['name'] for o in bindings}, {'cluster-admin', 'rancher-pre-upgrade'})
        runtime = next(o for o in bindings if o['metadata']['name'] == 'rancher')
        self.assertEqual(runtime['subjects'], [{'kind': 'ServiceAccount', 'name': 'rancher', 'namespace': 'cattle-system'}])
        self.assertFalse(any('post-delete' in o['metadata']['name'] for o in self.objects))
        self.assertFalse(self.allowed(None, 'clusterroles', 'cluster-admin', 'escalate'))
        self.assertFalse(self.allowed(None, 'clusterroles', 'unrelated-role', 'bind'))
        self.assertFalse(any(o['kind'] == 'ClusterRoleBinding' and o['roleRef']['name'] == 'cluster-admin' for o in self.foundation))

    def test_selected_runtime_is_local_admin_tls_only(self):
        values = yaml.safe_load(self.values)
        self.assertEqual(values['replicas'], 1)
        self.assertEqual(values['features'], 'continuous-delivery=false')
        self.assertEqual(values['agentTLSMode'], 'strict')
        self.assertTrue(values['privateCA'])
        self.assertEqual(values['ingress']['tls']['source'], 'secret')
        self.assertEqual(values['resources'], {'requests': {'cpu': '500m', 'memory': '1Gi'}, 'limits': {'memory': '4Gi'}})
        self.assertFalse(any(o['kind'] in ['Certificate', 'Issuer', 'ClusterIssuer', 'PersistentVolumeClaim', 'AuthConfig', 'GlobalRoleBinding'] for o in self.objects))
        self.assertFalse(self.hr['spec']['suspend'])
        self.assertEqual(self.hr['spec']['serviceAccountName'], 'rancher-installer')

    def test_real_chart_secret_lookup_denial_creation_and_preservation(self):
        # Chart source has a second CRD lookup, but only for Rancher/LE TLS.
        sources = [p.read_text() for p in (self.chart / 'templates').rglob('*') if p.is_file()]
        self.assertEqual(sum(line.count('lookup ') for text in sources for line in text.splitlines()), 2)
        denied = deepcopy(self.target_role)
        for rule in denied['rules']:
            if 'secrets' in rule['resources']:
                rule['resources'].remove('secrets')
        existing = base64.b64encode(b'synthetic-existing-bootstrap').decode()
        for policy, secrets, success, expected in [
            (denied, {}, False, None),
            (self.target_role, {}, True, base64.b64encode(DUMMY.encode()).decode()),
            (self.target_role, {('cattle-system', 'bootstrap-secret'): {'bootstrapPassword': existing}}, True, existing),
        ]:
            with self.subTest(allowed=success, existing=bool(secrets)), tempfile.TemporaryDirectory() as directory, lookup_server(policy, secrets=secrets) as (url, requests):
                path = Path(directory)
                (path / 'kubeconfig').write_text(yaml.safe_dump({'apiVersion': 'v1', 'kind': 'Config',
                    'clusters': [{'name': 'synthetic', 'cluster': {'server': url}}], 'users': [{'name': 'synthetic', 'user': {}}],
                    'contexts': [{'name': 'synthetic', 'context': {'cluster': 'synthetic', 'user': 'synthetic'}}], 'current-context': 'synthetic'}))
                (path / 'values.yaml').write_text(self.values)
                (path / 'dummy.yaml').write_text(yaml.safe_dump({'bootstrapPassword': DUMMY}))
                result = subprocess.run(['helm', 'template', release_name(self.hr), str(self.chart), '--namespace', 'cattle-system',
                    '--kube-version', '1.36.5', '--kubeconfig', str(path / 'kubeconfig'), '--dry-run=server',
                    '-f', str(path / 'values.yaml'), '-f', str(path / 'dummy.yaml')], text=True, capture_output=True, timeout=30,
                    env={**os.environ, 'KUBECONFIG': str(path / 'kubeconfig')})
                self.assertEqual(result.returncode == 0, success, result.stderr)
                self.assertIn('/api/v1/namespaces/cattle-system/secrets/bootstrap-secret', requests)
                self.assertFalse(any('customresourcedefinitions' in request for request in requests))
                if success:
                    objects = [o for o in yaml.safe_load_all(result.stdout) if o]
                    secret = next(o for o in objects if o['kind'] == 'Secret' and o['metadata']['name'] == 'bootstrap-secret')
                    self.assertEqual(secret['data']['bootstrapPassword'], expected)
                else:
                    self.assertIn('forbidden', result.stderr.lower())
