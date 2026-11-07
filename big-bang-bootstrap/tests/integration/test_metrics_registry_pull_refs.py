"""Actual pinned consumers must reference the existing namespace registry Secret."""
import copy
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
import yaml
from fixtures.render_helpers import build, helm, ordered_values, child_values, release_name
from security import test_gitlab_namespace_ownership as namespace_fixture

ROOT = Path(__file__).resolve().parents[2]
PULL_REFS = [{'name': 'private-registry'}]
render = namespace_fixture.GitLabNamespaceOwnership.render
key = lambda o: (o['kind'], o['metadata'].get('namespace'), o['metadata']['name'])


def legacy_values(values):
    result = []
    for text in values:
        value = yaml.safe_load(text)
        for name in ('monitoring', 'grafana'):
            package = value.get(name, {}).get('values', {})
            if 'global' in package:
                package['global'].pop('imagePullSecrets', None)
                if not package['global']:
                    del package['global']
        result.append(yaml.safe_dump(value))
    return result


def consumer_spec(obj):
    if obj['kind'] == 'Prometheus':
        return obj['spec']
    if obj['kind'] in ('Deployment', 'DaemonSet', 'Job'):
        return obj['spec']['template']['spec']
    return None


class MetricsRegistryPullReferences(unittest.TestCase):
    def test_exact_roots_reproduce_missing_refs_and_preserve_all_other_objects(self):
        sources = Path(os.environ['PREFLIGHT_SOURCES_DIR'])
        native = os.environ.get('PROMETHEUS_OPERATOR_SOURCE')
        args = ('--api-versions', 'monitoring.coreos.com/v1', '--api-versions', 'monitoring.coreos.com/v1alpha1')
        for stage in ('local', 'local-metrics-review', 'local-metrics-crds', 'local-metrics-pilot',
                      'local-metrics-limited-pilot', 'local-logging-pilot', 'local-logging-limited-pilot'):
            with self.subTest(stage=stage):
                objects = build(ROOT/'clusters'/stage)
                parent = next(o for o in objects if o['kind'] == 'HelmRelease' and o['metadata']['name'] == 'bigbang')
                values = ordered_values(objects, parent)
                old, current = [render(helm(sources/'bigbang/chart', 'bigbang', 'bigbang', v, args),
                                       parent['spec']['postRenderers'][0]['kustomize'])
                                for v in (legacy_values(values), values)]
                before, after = [{key(o): o for o in outer} for outer in (old, current)]
                self.assertEqual(set(before), set(after))
                if stage in ('local', 'local-metrics-review', 'local-metrics-crds'):
                    self.assertEqual(before, after)
                    continue
                for name in ('monitoring', 'grafana'):
                    hr_key = ('HelmRelease', 'bigbang', name)
                    a, b = [copy.deepcopy(index[hr_key]) for index in (before, after)]
                    for release in (a, b):
                        release['metadata']['annotations'].pop('checksum/bigbang-values')
                    self.assertEqual(a, b)
                changed = {k for k in before if before[k] != after[k]}
                self.assertEqual(changed, {(kind, 'bigbang', name if kind == 'HelmRelease' else 'bigbang-'+name+'-values')
                                           for kind in ('HelmRelease', 'Secret') for name in ('monitoring', 'grafana')})
                # Every unrelated package, direct app, claim, grant and logging input is equal above.
                for name in ('monitoring', 'grafana'):
                    children = []
                    for outer in (old, current):
                        hr = next(o for o in outer if o['kind'] == 'HelmRelease' and o['metadata']['name'] == name)
                        child = helm(sources/name/'chart', release_name(hr), 'monitoring', child_values(outer, name), args)
                        for renderer in hr['spec'].get('postRenderers', []):
                            child = render(child, renderer['kustomize'])
                        children.append({key(o): o for o in child})
                    legacy, fixed = children
                    self.assertEqual(set(legacy), set(fixed))
                    expected_count = 6 if name == 'monitoring' else 1
                    consumers = [o for o in fixed.values() if consumer_spec(o) is not None]
                    deferred = [o for o in consumers if o['metadata']['name'] == 'monitoring-monitoring-prometheus-blackbox-exporter']
                    self.assertEqual(len(deferred), int(name == 'monitoring' and 'limited' not in stage))
                    for obj in deferred:
                        self.assertEqual(legacy[key(obj)], obj)
                    consumers = [o for o in consumers if o not in deferred]
                    self.assertEqual(len(consumers), expected_count)
                    for obj in consumers:
                        old_spec = consumer_spec(legacy[key(obj)])
                        spec = consumer_spec(obj)
                        self.assertFalse(old_spec.get('imagePullSecrets'), key(obj))
                        self.assertEqual(spec['imagePullSecrets'], PULL_REFS, key(obj))
                        if obj['kind'] == 'Prometheus' and native and stage == 'local-metrics-limited-pilot':
                            with tempfile.TemporaryDirectory() as directory:
                                file = Path(directory)/'prometheus.json'; file.write_text(json.dumps(obj))
                                shutil.copyfile(ROOT/'tests/fixtures/operator_placement_test.go',
                                                Path(native)/'pkg/prometheus/server/perkforge_placement_test.go')
                                result = subprocess.run(['go', 'test', '-p=2', './pkg/prometheus/server',
                                                         '-run', '^TestPerkforgeRegistryPullReferences$', '-count=1'],
                                                        cwd=native, capture_output=True, text=True, timeout=900,
                                                        env={**os.environ, 'PLACEMENT_PROMETHEUS_JSON': str(file), 'GOTOOLCHAIN': 'local'})
                                self.assertEqual(result.returncode, 0, result.stdout+result.stderr)
                        spec.pop('imagePullSecrets')
                    # The native monitoring chart also binds the same reference on its five SAs.
                    for identity, obj in fixed.items():
                        if obj['kind'] == 'ServiceAccount' and obj.get('imagePullSecrets') != legacy[identity].get('imagePullSecrets'):
                            self.assertEqual(obj.pop('imagePullSecrets'), PULL_REFS)
                    # No credential creation/rotation, RBAC, image, resource, security, placement,
                    # claim, datasource, notification, hook-policy or scrape changes are allowed.
                    self.assertEqual(legacy, fixed)
