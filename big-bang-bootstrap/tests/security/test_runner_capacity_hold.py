"""Offline proof that the capacity hold only scales the original manager to zero."""
import copy
import os
from pathlib import Path
import unittest
from fixtures.render_helpers import build, helm, ordered_values, child_values

ROOT = Path(__file__).resolve().parents[2]

class RunnerCapacityHold(unittest.TestCase):
    def test_only_manager_replica_count_changes(self):
        sources = Path(os.environ['PREFLIGHT_SOURCES_DIR'])
        selected = build(ROOT / 'clusters/local-identity-onboarding')
        selected_parent = next(o for o in selected if o['kind'] == 'HelmRelease' and o['metadata']['name'] == 'bigbang')
        self.assertEqual(selected_parent['spec']['valuesFrom'][-1]['name'], 'values-runner-capacity-hold')
        objects = build(ROOT / 'clusters/local-gitlab-runner')
        objects.append(next(o for o in selected if o['kind'] == 'ConfigMap' and o['metadata']['name'] == 'values-runner-capacity-hold'))
        parent = next(o for o in objects if o['kind'] == 'HelmRelease' and o['metadata']['name'] == 'bigbang')
        old = copy.deepcopy(parent)
        parent['spec']['valuesFrom'].append(selected_parent['spec']['valuesFrom'][-1])
        old['spec']['valuesFrom'] = [r for r in old['spec']['valuesFrom'] if r['name'] != 'values-runner-capacity-hold']
        def rendered(release):
            outer = helm(sources / 'bigbang/chart', 'bigbang', 'bigbang', ordered_values(objects, release))
            child = helm(sources / 'gitlab-runner/chart', 'gitlab-runner', 'gitlab-runner', child_values(outer, 'gitlab-runner'))
            return {(o['kind'], o['metadata'].get('namespace'), o['metadata']['name']): o for o in child}
        before, after = rendered(old), rendered(parent)
        self.assertEqual(set(before), set(after))
        deployments = [o for o in before.values() if o['kind'] == 'Deployment']
        self.assertEqual(len(deployments), 1)
        self.assertEqual(deployments[0]['spec']['replicas'], 1)
        deployments[0]['spec']['replicas'] = 0
        self.assertEqual(before, after)
