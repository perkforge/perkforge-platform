"""Compare pinned native chart renders; never contact the cluster."""
import copy
import os
from pathlib import Path
import unittest
import yaml
from fixtures.render_helpers import build, helm, ordered_values, child_values, release_name
from security import test_gitlab_namespace_ownership as namespace_fixture

ROOT = Path(__file__).resolve().parents[2]
render = namespace_fixture.GitLabNamespaceOwnership.render
key = lambda o: (o['kind'], o['metadata'].get('namespace'), o['metadata']['name'])


class NodeExporterCPU(unittest.TestCase):
    def test_only_exporter_request_changes_in_limited_roots(self):
        sources = Path(os.environ['PREFLIGHT_SOURCES_DIR'])
        args = ('--api-versions', 'monitoring.coreos.com/v1', '--api-versions', 'monitoring.coreos.com/v1alpha1')
        for stage in ('local-metrics-limited-pilot', 'local-logging-limited-pilot'):
            with self.subTest(stage=stage):
                objects = build(ROOT / 'clusters' / stage)
                parent = next(o for o in objects if o['kind'] == 'HelmRelease' and o['metadata']['name'] == 'bigbang')
                values = ordered_values(objects, parent)
                baseline = []
                for text in values:
                    obj = yaml.safe_load(text)
                    upstream = obj.get('monitoring', {}).get('values', {}).get('upstream', {})
                    exporter = upstream.get('prometheus-node-exporter', {})
                    exporter.get('resources', {}).get('requests', {}).pop('cpu', None)
                    baseline.append(yaml.safe_dump(obj))
                versions = []
                for selected in (baseline, values):
                    outer = render(helm(sources/'bigbang/chart', 'bigbang', 'bigbang', selected, args),
                                   parent['spec']['postRenderers'][0]['kustomize'])
                    hr = next(o for o in outer if o['kind'] == 'HelmRelease' and o['metadata']['name'] == 'monitoring')
                    child = helm(sources/'monitoring/chart', release_name(hr), 'monitoring', child_values(outer, 'monitoring'), args)
                    for pr in hr['spec'].get('postRenderers', []):
                        child = render(child, pr['kustomize'])
                    versions.append({key(o): o for o in child})
                old, new = versions
                self.assertEqual(set(old), set(new))
                changed = [k for k in old if old[k] != new[k]]
                self.assertEqual(len(changed), 1)
                ds = new[changed[0]]
                self.assertEqual(ds['kind'], 'DaemonSet')
                self.assertIn('node-exporter', ds['metadata']['name'])
                before = old[changed[0]]['spec']['template']['spec']['containers'][0]
                after = ds['spec']['template']['spec']['containers'][0]
                self.assertEqual(before['resources']['requests']['cpu'], '200m')
                self.assertEqual(after['resources']['requests']['cpu'], '50m')
                normalized = copy.deepcopy(new)
                normalized[changed[0]]['spec']['template']['spec']['containers'][0]['resources']['requests']['cpu'] = '200m'
                self.assertEqual(old, normalized)
