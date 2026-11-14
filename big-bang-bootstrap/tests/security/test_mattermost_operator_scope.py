"""Actual pinned chart + Flux-compatible post-render; no live authorization proof."""
from pathlib import Path
import hashlib
import json
import tempfile
import unittest
import yaml
from fixtures.collaboration import package_render
from fixtures.render_helpers import build

ROOT = Path(__file__).resolve().parents[2]
READ = {'get', 'list', 'watch'}


class MattermostOperatorScope(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.render = package_render(ROOT, 'mattermost', ('mattermost-operator',))
        cls.hr, cls.raw = cls.render['mattermost-operator']
        renderer, = cls.hr['spec']['postRenderers']
        cls.renderer = renderer['kustomize']
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            (directory / 'objects.yaml').write_text(yaml.safe_dump_all(cls.raw))
            (directory / 'kustomization.yaml').write_text(yaml.safe_dump({
                'apiVersion': 'kustomize.config.k8s.io/v1beta1',
                'kind': 'Kustomization', 'resources': ['objects.yaml'], **cls.renderer}))
            cls.effective = build(directory)
        cls.foundation = build(ROOT / 'configuration/packages/mattermost/prerequisites')

    def test_exact_native_versions_and_images_unchanged(self):
        source = yaml.safe_load((ROOT / 'configuration/packages/mattermost/candidate-values.yaml').read_text())
        for package in source['addons'].values():
            self.assertNotIn('git', package)
            self.assertNotIn('helmRepo', package)
            self.assertNotIn('image', package['values'])
        raw = {(o['kind'], o['metadata']['name']): o for o in self.raw}
        actual = {(o['kind'], o['metadata']['name']): o for o in self.effective}
        self.assertEqual(set(raw), set(actual))
        for key in raw:
            if key != ('ClusterRole', 'mattermost-operator'):
                self.assertEqual(actual[key], raw[key], key)
        app = next(o for o in self.render['mattermost'][1] if o['kind'] == 'Mattermost')
        self.assertEqual(app['metadata']['name'], 'mattermost')
        self.assertEqual(app['metadata']['namespace'], 'mattermost')
        self.assertEqual(app['spec']['version'], '11.11.0')
        deployment = actual[('Deployment', 'mattermost-operator')]
        self.assertEqual(deployment['spec']['template']['spec']['containers'][0]['image'],
                         'registry1.dso.mil/ironbank/opensource/mattermost/mattermost-operator:v1.25.9')

    def test_global_reads_and_only_named_ingressclass_delete(self):
        role = next(o for o in self.effective if o['kind'] == 'ClusterRole')
        mutations = [r for r in role['rules'] if set(r['verbs']) - READ]
        self.assertEqual(mutations, [{'apiGroups': ['networking.k8s.io'],
                         'resources': ['ingressclasses'], 'resourceNames': ['mattermost'], 'verbs': ['delete']}])
        self.assertTrue(any('secrets' in r['resources'] and set(r['verbs']) == READ
                            and 'resourceNames' not in r for r in role['rules']))
        for rule in role['rules']:
            self.assertNotIn('*', rule['apiGroups'] + rule['resources'] + rule['verbs'])
        binding = next(o for o in self.effective if o['kind'] == 'ClusterRoleBinding')
        self.assertEqual(binding['roleRef']['name'], 'mattermost-operator')
        self.assertEqual(binding['subjects'], [{'kind': 'ServiceAccount', 'name': 'mattermost-operator',
                                               'namespace': 'mattermost-operator'}])

    def test_runtime_mutations_have_only_two_namespace_bindings(self):
        bindings = [o for o in self.foundation if o['kind'] == 'RoleBinding'
                    and any(s['name'] == 'mattermost-operator' for s in o['subjects'])]
        self.assertEqual({o['metadata']['namespace'] for o in bindings}, {'mattermost', 'mattermost-operator'})
        self.assertEqual(len(bindings), 2)
        for binding in bindings:
            self.assertEqual(binding['roleRef']['kind'], 'Role')
            role = next(o for o in self.foundation if o['kind'] == 'Role'
                        and o['metadata']['name'] == binding['roleRef']['name'])
            self.assertEqual(role['metadata']['namespace'], binding['metadata']['namespace'])
            for r in role['rules']:
                self.assertFalse({'*', 'bind', 'escalate', 'impersonate'} & set(r['verbs']))
                self.assertFalse({'clusterroles', 'clusterrolebindings', 'namespaces', 'ingressclasses',
                                  'statefulsets', 'clusters'} & set(r['resources']))
            if role['metadata']['namespace'] == 'mattermost-operator':
                self.assertEqual({x for r in role['rules'] for x in r['resources']}, {'leases', 'events'})
                lease = [r for r in role['rules'] if 'leases' in r['resources']]
                self.assertEqual(lease, [
                    {'apiGroups': ['coordination.k8s.io'], 'resources': ['leases'], 'verbs': ['create']},
                    {'apiGroups': ['coordination.k8s.io'], 'resources': ['leases'],
                     'resourceNames': ['b78a986e.mattermost.com'], 'verbs': ['get', 'update']}])

    def test_upstream_authority_drift_requires_review(self):
        # Review on every Big Bang operator update, including changes hidden by /rules replacement.
        role = next(o for o in self.raw if o['kind'] == 'ClusterRole')
        self.assertEqual(hashlib.sha256(json.dumps(role['rules'], sort_keys=True,
                         separators=(',', ':')).encode()).hexdigest(),
                         'eaaec4fca71a82797f99ec820e94244b86bd91e6d990664ba0f018b1a3b7f723')
        expected = {('', 'pods'), ('', 'services'), ('', 'configmaps'), ('', 'secrets'),
                    ('', 'serviceaccounts'), ('', 'persistentvolumeclaims'), ('', 'namespaces'),
                    ('coordination.k8s.io', 'leases'), ('apps', 'deployments'),
                    ('apps', 'deployments/finalizers'), ('apps', 'replicasets'), ('batch', 'jobs'),
                    ('networking.k8s.io', 'ingresses'), ('networking.k8s.io', 'ingressclasses'),
                    ('rbac.authorization.k8s.io', 'roles'), ('rbac.authorization.k8s.io', 'rolebindings'),
                    ('mattermost.com', '*'), ('installation.mattermost.com', '*'),
                    ('mysql.presslabs.org', 'mysqlbackups'), ('mysql.presslabs.org', 'mysqlclusters'),
                    ('mysql.presslabs.org', 'mysqlclusters/status'),
                    ('miniocontroller.min.io', 'minioinstances'), ('miniocontroller.min.io', 'minioinstances/status')}
        self.assertEqual({(g, r) for rule in role['rules'] for g in rule['apiGroups'] for r in rule['resources']}, expected)
        patch, = self.renderer['patches']
        self.assertEqual(patch['target'], {'group': 'rbac.authorization.k8s.io', 'version': 'v1',
                                          'kind': 'ClusterRole', 'name': 'mattermost-operator'})
        self.assertEqual(len(yaml.safe_load(patch['patch'])), 1)
        self.assertFalse(any(o['metadata']['name'].startswith('mattermost') for o in build(ROOT / 'clusters/local')))
