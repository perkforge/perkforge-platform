"""Pinned chart rendering and native operator generation; no Kubernetes API calls."""
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
SELECTOR = {'storage.perkforge.io/worker': 'true'}
render = namespace_fixture.GitLabNamespaceOwnership.render
key = lambda o: (o['kind'], o['metadata'].get('namespace'), o['metadata']['name'])


def without_placement(values):
    result = []
    for text in values:
        value = yaml.safe_load(text)
        for name in ('grafana', 'monitoring'):
            upstream = value.get(name, {}).get('values', {}).get('upstream', {})
            target = upstream if name == 'grafana' else upstream.get('prometheus', {}).get('prometheusSpec', {})
            target.pop('nodeSelector', None)
        result.append(yaml.safe_dump(value))
    return result


class MetricsWorkerPlacement(unittest.TestCase):
    def test_rendered_consumers_and_native_operator_preserve_everything_except_placement(self):
        sources = Path(os.environ['PREFLIGHT_SOURCES_DIR'])
        native = os.environ.get('PROMETHEUS_OPERATOR_SOURCE')
        args = ('--api-versions', 'monitoring.coreos.com/v1', '--api-versions', 'monitoring.coreos.com/v1alpha1')
        for stage in ('local', 'local-metrics-crds', 'local-metrics-limited-pilot', 'local-logging-limited-pilot'):
            with self.subTest(stage=stage):
                objects = build(ROOT/'clusters'/stage)
                parent = next(o for o in objects if o['kind'] == 'HelmRelease' and o['metadata']['name'] == 'bigbang')
                values = ordered_values(objects, parent)
                outer = [render(helm(sources/'bigbang/chart', 'bigbang', 'bigbang', v, args),
                                parent['spec']['postRenderers'][0]['kustomize'])
                         for v in (without_placement(values), values)]
                if stage in ('local', 'local-metrics-crds'):
                    self.assertEqual({key(o): o for o in outer[0]}, {key(o): o for o in outer[1]})
                    continue
                # Only the two monitoring values Secrets may change in the umbrella.
                indexed = [{key(o): o for o in selected} for selected in outer]
                self.assertEqual(set(indexed[0]), set(indexed[1]))
                for name in ('monitoring', 'grafana'):
                    release_key = ('HelmRelease', 'bigbang', name)
                    a, b = [copy.deepcopy(index[release_key]) for index in indexed]
                    for release in (a, b):
                        release['metadata']['annotations'].pop('checksum/bigbang-values')
                    self.assertEqual(a, b)
                    for index in indexed:
                        index[release_key]['metadata']['annotations'].pop('checksum/bigbang-values')
                self.assertEqual({k for k in indexed[0] if indexed[0][k] != indexed[1][k]},
                                 {('Secret', 'bigbang', 'bigbang-grafana-values'),
                                  ('Secret', 'bigbang', 'bigbang-monitoring-values')})
                for package, kind in (('grafana', 'Deployment'), ('monitoring', 'Prometheus')):
                    children = []
                    for selected in outer:
                        hr = next(o for o in selected if o['kind'] == 'HelmRelease' and o['metadata']['name'] == package)
                        children.append(helm(sources/package/'chart', release_name(hr), 'monitoring', child_values(selected, package), args))
                        for pr in hr['spec'].get('postRenderers', []):
                            children[-1] = render(children[-1], pr['kustomize'])
                    old, current = [{key(o): o for o in child} for child in children]
                    consumer = next(o for o in current.values() if o['kind'] == kind)
                    spec = consumer['spec']['template']['spec'] if kind == 'Deployment' else consumer['spec']
                    self.assertEqual(spec['nodeSelector'], SELECTOR)
                    # Actual observed label/CSI relationship: control lacks label, both workers match.
                    eligible = lambda labels: all(labels.get(k) == v for k, v in spec['nodeSelector'].items())
                    self.assertFalse(eligible({'node-role.kubernetes.io/control-plane': 'true'}))
                    self.assertTrue(eligible(SELECTOR))
                    self.assertTrue(eligible({**SELECTOR, 'kubernetes.io/hostname': 'second-worker'}))
                    self.assertFalse(eligible({'storage.perkforge.io/worker': 'false'}))
                    if kind == 'Prometheus':
                        operator = next(o for o in current.values() if o['kind'] == 'Deployment'
                                        and 'operator' in o['metadata']['name'])
                        self.assertTrue(any(c['image'].endswith('/prometheus-operator:v0.94.0')
                                            for c in operator['spec']['template']['spec']['containers']))
                    if kind == 'Prometheus' and native:
                        with tempfile.TemporaryDirectory() as directory:
                            file = Path(directory)/'prometheus.json'; file.write_text(json.dumps(consumer))
                            fixture = Path(native)/'pkg/prometheus/server/perkforge_placement_test.go'
                            shutil.copyfile(ROOT/'tests/fixtures/operator_placement_test.go', fixture)
                            result = subprocess.run(['go', 'test', '-p=2', './pkg/prometheus/server',
                                                     '-run', '^TestPerkforgeWorkerPlacement$', '-count=1'],
                                                    cwd=native, capture_output=True, text=True, timeout=900,
                                                    env={**os.environ, 'PLACEMENT_PROMETHEUS_JSON': str(file), 'GOTOOLCHAIN': 'local'})
                            self.assertEqual(result.returncode, 0, result.stdout+result.stderr)
                    # Full equality also covers claims, security, requests, hooks, monitors and rules.
                    old_consumer = old[key(consumer)]
                    old_spec = old_consumer['spec']['template']['spec'] if kind == 'Deployment' else old_consumer['spec']
                    self.assertFalse(old_spec.get('nodeSelector'))
                    if 'nodeSelector' in old_spec:
                        spec['nodeSelector'] = old_spec['nodeSelector']
                    else:
                        del spec['nodeSelector']
                    self.assertEqual(old, current)

    @unittest.skipUnless(os.environ.get('REQUIRE_NATIVE_OPERATOR_PLACEMENT'), 'native operator coverage is a separate pinned CI job')
    def test_native_operator_fixture_is_required_when_selected(self):
        self.assertTrue(os.environ.get('PROMETHEUS_OPERATOR_SOURCE'))
