"""Render staged roots and prove existing workload inputs remain identical."""
import os
from pathlib import Path
import unittest
import re

from fixtures.render_helpers import build, helm, ordered_values, child_values, release_name

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
        for stage in ('local', 'local-metrics-review', 'local-metrics-crds', 'local-metrics-pilot'):
            releases = {x['metadata']['name'] for x in self.render(stage) if x['kind'] == 'HelmRelease'}
            self.assertFalse({'loki', 'alloy'} & releases)
            if stage == 'local':
                self.assertFalse({'monitoring', 'grafana', 'prometheus-operator-crds'} & releases)

    def test_pilot_preserves_existing_child_workloads_without_new_installer_authority(self):
        before, after = self.render('local-gitlab-runner'), self.render('local-metrics-pilot')
        sources = Path(os.environ['PREFLIGHT_SOURCES_DIR'])
        for name in ('gitlab', 'gitlab-runner', 'headlamp', 'keycloak'):
            with self.subTest(package=name):
                children = []
                releases = []
                for outer in (before, after):
                    hr = next(x for x in outer if x['kind'] == 'HelmRelease' and x['metadata']['name'] == name)
                    releases.append(hr)
                    objects = helm(sources / name / 'chart', release_name(hr), hr['spec']['targetNamespace'], child_values(outer, name))
                    for obj in objects:
                        # Upstream hashes all coalesced values, including an inert redis:null.
                        # Permit only the two shared-secret hook names to differ; compare their
                        # complete PodSpecs, commands, references and hook policies unchanged.
                        if name == 'gitlab' and obj['kind'] == 'Job':
                            obj['metadata']['name'] = re.sub(r'^(gitlab-shared-secrets-)[0-9a-f]{7}(?=-selfsign$|$)', r'\1HASH', obj['metadata']['name'])
                    children.append(objects)
                self.assertEqual(children[0], children[1])
                self.assertEqual(releases[0]['spec'].get('dependsOn'), releases[1]['spec'].get('dependsOn'))
                self.assertEqual(releases[0]['spec']['serviceAccountName'], releases[1]['spec']['serviceAccountName'])
        selected = {x['metadata']['name']: x for x in after if x['kind'] == 'HelmRelease'}
        for name in ('monitoring', 'grafana', 'prometheus-operator-crds'):
            self.assertFalse(selected[name]['spec']['suspend'])
        parent = next(x for x in build(ROOT / 'clusters/local-metrics-pilot') if x['kind'] == 'HelmRelease' and x['metadata']['name'] == 'bigbang')
        patches = parent['spec']['postRenderers'][0]['kustomize']['patches']
        self.assertTrue(any(x['target'] == {'kind': 'Namespace', 'name': 'monitoring'} and '$patch: delete' in x['patch'] for x in patches))
