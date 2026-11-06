"""Optional backend-only root: no monitoring runtime or new access delegation."""
import os
from pathlib import Path
import unittest

from fixtures.render_helpers import build, child_values, helm, ordered_values, release_name

ROOT = Path(__file__).resolve().parents[2]


class LoggingBackend(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sources = Path(os.environ['PREFLIGHT_SOURCES_DIR'])
        cls.root = build(ROOT / 'clusters/local-logging-backend')
        cls.parent = next(x for x in cls.root if x['kind'] == 'HelmRelease' and x['metadata']['name'] == 'bigbang')
        cls.outer = cls.render(cls.root)

    @classmethod
    def render(cls, objects):
        parent = next(x for x in objects if x['kind'] == 'HelmRelease' and x['metadata']['name'] == 'bigbang')
        return helm(cls.sources / 'bigbang/chart', 'bigbang', 'bigbang', ordered_values(objects, parent))

    def test_every_existing_package_and_nextcloud_object_is_unchanged(self):
        def key(x):
            return (x['apiVersion'], x['kind'], x['metadata'].get('namespace'), x['metadata']['name'])
        current = {key(x): x for x in self.outer}
        for obj in self.render(build(ROOT / 'clusters/local-metrics-crds')):
            self.assertIn(key(obj), current)
            self.assertEqual(current[key(obj)], obj, key(obj))
        source = {key(x): x for x in self.root}
        for obj in build(ROOT / 'clusters/local-nextcloud'):
            if key(obj) != ('helm.toolkit.fluxcd.io/v2', 'HelmRelease', 'bigbang', 'bigbang'):
                self.assertEqual(source[key(obj)], obj)

    def test_only_logging_runtime_is_added_and_dependencies_resolve(self):
        names = {x['metadata']['name'] for x in self.outer if x['kind'] == 'HelmRelease'}
        original = {x['metadata']['name'] for x in self.render(build(ROOT / 'clusters/local-metrics-crds')) if x['kind'] == 'HelmRelease'}
        self.assertEqual(names - original, {'alloy', 'loki'})
        self.assertFalse({'monitoring', 'grafana'} & names)
        for release in [x for x in self.outer if x['kind'] == 'HelmRelease']:
            for dependency in release['spec'].get('dependsOn') or []:
                self.assertIn(dependency['name'], names)
        self.assertFalse(any(x['kind'] in ['Ingress', 'HTTPRoute', 'Gateway'] for x in self.outer))
        patches = self.parent['spec']['postRenderers'][0]['kustomize']['patches']
        for name in ['logging', 'alloy']:
            self.assertTrue(any(x.get('target', {}).get('kind') == 'Namespace' and x['target'].get('name') == name and '$patch: delete' in x['patch'] for x in patches))

    def test_backend_configurations_match_reviewed_logging_pilot(self):
        pilot = self.render(build(ROOT / 'clusters/local-logging-pilot'))
        for name in ['loki', 'alloy']:
            rendered = []
            for outer in [self.outer, pilot]:
                release = next(x for x in outer if x['kind'] == 'HelmRelease' and x['metadata']['name'] == name)
                self.assertFalse(release['spec']['suspend'])
                rendered.append(helm(self.sources / name / 'chart', release_name(release), release['spec']['targetNamespace'], child_values(outer, name), ('--include-crds',)))
            def key(x):
                return (x['kind'], x['metadata'].get('namespace'), x['metadata']['name'])
            backend = {key(x): x for x in rendered[0]}
            complete = {key(x): x for x in rendered[1]}
            omitted = ({('ConfigMap', 'monitoring', 'loki-grafana-dashboards'), ('ConfigMap', 'monitoring', 'logging-loki-dashboards-monolith')} if name == 'loki' else {('ServiceMonitor', 'alloy', 'alloy-alloy-logs'), ('ServiceMonitor', 'alloy', 'alloy-alloy-singleton')})
            self.assertEqual(set(complete) - set(backend), omitted)
            self.assertEqual(set(backend) - set(complete), set())
            for identity, obj in backend.items():
                self.assertEqual(complete[identity], obj, identity)

    def test_existing_bound_installer_roles_cover_actual_namespaces(self):
        foundation = build(ROOT / 'configuration/observability/logging-prerequisites')
        mapping = {'ServiceAccount': ('', 'serviceaccounts'), 'Service': ('', 'services'),
                   'ConfigMap': ('', 'configmaps'), 'Secret': ('', 'secrets'),
                   'Deployment': ('apps', 'deployments'), 'StatefulSet': ('apps', 'statefulsets'),
                   'Job': ('batch', 'jobs'), 'Role': ('rbac.authorization.k8s.io', 'roles'),
                   'RoleBinding': ('rbac.authorization.k8s.io', 'rolebindings'),
                   'CustomResourceDefinition': ('apiextensions.k8s.io', 'customresourcedefinitions'),
                   'Alloy': ('collectors.grafana.com', 'alloys')}
        for name in ['loki', 'alloy']:
            hr = next(x for x in self.outer if x['kind'] == 'HelmRelease' and x['metadata']['name'] == name)
            identity = hr['spec']['serviceAccountName']
            def allowed(group, resource, object_name, verb, namespace):
                rules = []
                for binding in foundation:
                    if binding['kind'] not in ['RoleBinding', 'ClusterRoleBinding']:
                        continue
                    if binding['kind'] == 'RoleBinding' and binding['metadata']['namespace'] != namespace:
                        continue
                    if not any(s.get('kind') == 'ServiceAccount' and s['name'] == identity and s.get('namespace') == hr['metadata']['namespace'] for s in binding['subjects']):
                        continue
                    ref = binding['roleRef']
                    for role in foundation:
                        if role['kind'] == ref['kind'] and role['metadata']['name'] == ref['name'] and (role['kind'] != 'Role' or role['metadata']['namespace'] == namespace):
                            rules.extend(role['rules'])
                return any(group in r['apiGroups'] and resource in r['resources'] and verb in r['verbs'] and ('resourceNames' not in r or object_name in r['resourceNames']) for r in rules)
            objects = helm(self.sources / name / 'chart', release_name(hr), hr['spec']['targetNamespace'], child_values(self.outer, name), ('--include-crds',))
            for obj in objects:
                group, resource = mapping[obj['kind']]
                namespace = None if obj['kind'] == 'CustomResourceDefinition' else obj['metadata'].get('namespace', hr['spec']['targetNamespace'])
                for verb in ['get', 'list', 'watch', 'create', 'update', 'patch', 'delete']:
                    self.assertTrue(allowed(group, resource, obj['metadata']['name'], verb, namespace), (name, obj['kind'], namespace, verb))
                if obj['kind'] == 'Role':
                    self.assertTrue(allowed(group, resource, obj['metadata']['name'], 'escalate', namespace))
                if obj['kind'] == 'RoleBinding':
                    self.assertTrue(allowed(group, 'roles', obj['roleRef']['name'], 'bind', namespace))
            self.assertFalse(allowed('', 'configmaps', 'unrelated', 'create', 'monitoring'))
            self.assertFalse(allowed('', 'secrets', 'unrelated', 'get', 'kube-system'))
