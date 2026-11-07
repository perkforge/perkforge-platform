"""Reproduce GitLab API-discovery integration and exercise its exact Flux post-renderer."""
from pathlib import Path
import copy
import os
import unittest
from fixtures.render_helpers import build, ordered_values, helm, child_values
from security import test_gitlab_namespace_ownership as namespace_fixture

ROOT = Path(__file__).resolve().parents[2]
APIS = ('--api-versions', 'monitoring.coreos.com/v1',
        '--api-versions', 'monitoring.coreos.com/v1alpha1')
NAMES = {'gitlab-gitaly', 'gitlab-webservice', 'gitlab-webservice-workhorse'}
render = namespace_fixture.GitLabNamespaceOwnership.render
indexed = namespace_fixture.GitLabNamespaceOwnership.indexed


def postrender(objects, renderers):
    # Canonicalize both sides equally; Kustomize omits null metadata fields.
    for renderer in renderers:
        objects = render(objects, renderer['kustomize'])
    return render(objects, {})


class GitLabMonitoringCapabilities(unittest.TestCase):
    def test_discovery_cannot_activate_unselected_monitors_or_change_other_objects(self):
        sources = Path(os.environ['PREFLIGHT_SOURCES_DIR'])
        for stage in ('local-gitlab-app', 'local-gitlab-runner', 'local-metrics-crds',
                      'local-metrics-limited-pilot', 'local-logging-backend',
                      'local-logging-limited-pilot'):
            with self.subTest(stage=stage):
                root = build(ROOT/'clusters'/stage)
                parent = next(x for x in root if x['kind'] == 'HelmRelease'
                              and x['metadata']['name'] == 'bigbang')
                outer = helm(sources/'bigbang/chart', 'bigbang', 'bigbang', ordered_values(root, parent))
                outer = render(outer, parent['spec']['postRenderers'][0]['kustomize'])
                child = next(x for x in outer if x['kind'] == 'HelmRelease'
                             and x['metadata']['name'] == 'gitlab')
                values = child_values(outer, 'gitlab')
                no_api = helm(sources/'gitlab/chart', 'gitlab', 'gitlab', values)
                # global=false does not override upstream's OR with API availability.
                discovered = helm(sources/'gitlab/chart', 'gitlab', 'gitlab', values,
                                  APIS + ('--set', 'global.monitoring.enabled=false'))
                self.assertEqual({x['metadata']['name'] for x in discovered if x['kind'] == 'ServiceMonitor'}, NAMES)
                self.assertFalse(any(x['kind'] == 'ServiceMonitor' for x in no_api))
                renderers = child['spec']['postRenderers']
                deletion = [r for r in renderers if {p['target'].get('name') for p in r['kustomize']['patches']} == NAMES]
                self.assertEqual(len(deletion), 1)
                for patch in deletion[0]['kustomize']['patches']:
                    self.assertEqual({k: v for k, v in patch['target'].items() if k != 'name'},
                                     {'group': 'monitoring.coreos.com', 'version': 'v1',
                                      'kind': 'ServiceMonitor', 'namespace': 'gitlab'})
                legacy = [r for r in renderers if r not in deletion]
                legacy_outer = helm(sources/'bigbang/chart', 'bigbang', 'bigbang',
                                    ordered_values(root, parent),
                                    ('--set-json', 'addons.gitlab.postRenderers=[]'))
                legacy_outer = render(legacy_outer, parent['spec']['postRenderers'][0]['kustomize'])
                expected_outer = copy.deepcopy(outer)
                expected_child = next(x for x in expected_outer if x['kind'] == 'HelmRelease'
                                      and x['metadata']['name'] == 'gitlab')
                if legacy:
                    expected_child['spec']['postRenderers'] = legacy
                else:
                    expected_child['spec'].pop('postRenderers')
                self.assertEqual(indexed(expected_outer), indexed(legacy_outer))
                old = postrender(discovered, legacy)
                current = postrender(discovered, renderers)
                self.assertFalse(any(x['apiVersion'].startswith('monitoring.coreos.com/') for x in current))
                # Exact object equality includes hooks, Pod annotations, claims and Secret references.
                self.assertEqual(indexed(current), indexed([x for x in old if x['kind'] != 'ServiceMonitor']))
                self.assertEqual(indexed(current), indexed(postrender(no_api, legacy)))
                self.assertEqual(indexed(current), indexed(postrender(current, deletion)))
                # Same-kind foreign objects and the same name in another namespace survive.
                sentinel = {'apiVersion': 'monitoring.coreos.com/v1', 'kind': 'ServiceMonitor',
                            'metadata': {'name': 'foreign-monitor', 'namespace': 'gitlab'},
                            'spec': {'selector': {'matchLabels': {'owner': 'foreign'}}, 'endpoints': [{'port': 'metrics'}]}}
                elsewhere = copy.deepcopy(sentinel)
                elsewhere['metadata'] = {'name': 'gitlab-gitaly', 'namespace': 'other'}
                retained = indexed(postrender(current + [sentinel, elsewhere], deletion))
                self.assertEqual(retained['ServiceMonitor', 'gitlab', 'foreign-monitor'], sentinel)
                self.assertEqual(retained['ServiceMonitor', 'other', 'gitlab-gitaly'], elsewhere)
                self.assertEqual(child['spec']['serviceAccountName'], 'gitlab-installer')
                self.assertEqual(child['spec']['upgrade']['remediation']['retries'], 0)
