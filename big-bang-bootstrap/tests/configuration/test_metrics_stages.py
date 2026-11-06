"""Render staged roots and prove existing workload inputs remain identical."""
import os
from pathlib import Path
import unittest

from fixtures.render_helpers import build, helm, ordered_values

ROOT = Path(__file__).resolve().parents[2]


class MetricsStages(unittest.TestCase):
    def render(self, stage):
        objects = build(ROOT / 'clusters' / stage)
        parent = next(x for x in objects if x['kind'] == 'HelmRelease')
        return helm(Path(os.environ['PREFLIGHT_SOURCES_DIR']) / 'bigbang/chart',
                    'bigbang', 'bigbang', ordered_values(objects, parent))

    def test_stages_preserve_existing_resources_and_select_only_intended_packages(self):
        def identity(x):
            return (x['apiVersion'], x['kind'], x['metadata'].get('namespace'), x['metadata']['name'])
        baseline = {identity(x): x for x in self.render('local-gitlab-runner')}
        expected = {'local-metrics-review': set(),
                    'local-metrics-crds': {'prometheus-operator-crds'}}
        for stage, added in expected.items():
            with self.subTest(stage=stage):
                rendered = {identity(x): x for x in self.render(stage)}
                for key, value in baseline.items():
                    if key == ('v1', 'Secret', 'bigbang', 'bigbang-prometheus-operator-crds-values'):
                        # The umbrella emits this disabled package's values Secret already.
                        # Only its keep annotation input changes before CRD activation.
                        import yaml
                        self.assertEqual(yaml.safe_load(rendered[key]['stringData']['overlays']),
                                         {'upstream': {'crds': {'annotations': {'helm.sh/resource-policy': 'keep'}}}})
                        for field in ('common', 'defaults'):
                            self.assertEqual(rendered[key]['stringData'][field], value['stringData'][field])
                        continue
                    self.assertEqual(rendered[key], value, key)
                releases = [x for k, x in rendered.items() if k not in baseline and x['kind'] == 'HelmRelease']
                self.assertEqual({x['metadata']['name'] for x in releases}, added)
                self.assertTrue(all(not x['spec']['suspend'] for x in releases))

    def test_default_root_remains_unmodified_and_logs_stay_off(self):
        for stage in ('local', 'local-metrics-review', 'local-metrics-crds'):
            releases = {x['metadata']['name'] for x in self.render(stage) if x['kind'] == 'HelmRelease'}
            self.assertFalse({'loki', 'alloy'} & releases)
            if stage == 'local':
                self.assertFalse({'monitoring', 'grafana', 'prometheus-operator-crds'} & releases)
