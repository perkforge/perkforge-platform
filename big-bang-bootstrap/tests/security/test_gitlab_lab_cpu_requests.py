"""CPU-only lab sizing against the actual pinned umbrella and GitLab chart."""
import copy
import os
from pathlib import Path
import re
import unittest
import yaml

from fixtures.render_helpers import build, child_values, helm, ordered_values
from fixtures.resource_inventory import quantity

ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / 'configuration/packages/gitlab'


class GitLabLabCPURequests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        src = Path(os.environ['PREFLIGHT_SOURCES_DIR'])
        cls.root = build(ROOT / 'clusters/local-gitlab-app')
        parent = next(x for x in cls.root if x['kind'] == 'HelmRelease'
                      and x['metadata']['name'] == 'bigbang')
        outer = helm(src / 'bigbang/chart', 'bigbang', 'bigbang',
                     ordered_values(cls.root, parent))
        values = child_values(outer, 'gitlab')
        cls.actual = helm(src / 'gitlab/chart', 'gitlab', 'gitlab', values)
        cls.before = helm(src / 'gitlab/chart', 'gitlab', 'gitlab', values, (
            '--set', 'upstream.gitlab.toolbox.resources.requests.cpu=1',
            '--set', 'upstream.gitlab.webservice.workhorse.resources.requests.cpu=600m'))

    def test_full_child_render_changes_only_two_cpu_requests_and_values_hashes(self):
        def stable(objects):
            objects = copy.deepcopy(objects)
            for obj in objects:
                if obj['kind'] == 'Deployment':
                    for container in obj['spec']['template']['spec']['containers']:
                        name = container['name']
                        if name in ('toolbox', 'gitlab-workhorse'):
                            container['resources']['requests']['cpu'] = 'BASELINE'
            # The pinned chart deliberately includes a values digest in these
            # hook names. Do not normalize unrelated checksums, fields or names.
            return re.sub(r'(gitlab-(?:shared-secrets|migrations))-[0-9a-f]{7}',
                          r'\1-VALUESHASH', yaml.safe_dump(objects))
        self.assertEqual(stable(self.before), stable(self.actual))
        found = {}
        for obj in self.actual:
            if obj['kind'] == 'Deployment':
                for c in obj['spec']['template']['spec']['containers']:
                    if c['name'] in ('toolbox', 'gitlab-workhorse'):
                        found[c['name']] = c['resources']
        self.assertEqual(set(found), {'toolbox', 'gitlab-workhorse'})
        self.assertEqual(found['toolbox']['requests']['cpu'], '250m')
        self.assertEqual(found['gitlab-workhorse']['requests']['cpu'], '100m')
        self.assertEqual(quantity(found['toolbox']['limits']['cpu']), 2)
        self.assertEqual(quantity(found['gitlab-workhorse']['limits']['cpu']), .6)

    def test_postgres_runtime_and_review_contract_preserve_memory_limits_and_placement(self):
        pg = next(x for x in self.root if x['kind'] == 'Cluster'
                  and x['metadata']['name'] == 'gitlab-postgres')
        self.assertEqual(pg['spec']['resources'], {
            'requests': {'cpu': '250m', 'memory': '2Gi'},
            'limits': {'cpu': '2', 'memory': '4Gi'}})
        self.assertEqual(pg['spec']['instances'], 1)
        self.assertEqual(pg['spec']['storage'], {'storageClass': 'longhorn', 'size': '16Gi'})
        review = yaml.safe_load((PACKAGE / 'data-services-review.yaml').read_text())
        expected = review['recommended_lab']['postgres']
        self.assertEqual(pg['spec']['resources'],
                         {k: expected[k] for k in ('requests', 'limits')})
        baseline = build(ROOT / 'clusters/local-gitlab-data')
        old_pg = next(x for x in baseline if x['kind'] == 'Cluster'
                      and x['metadata']['name'] == 'gitlab-postgres')
        self.assertEqual(pg, old_pg)

    def test_effective_request_savings_include_init_containers(self):
        def effective(pod):
            # These pinned workloads have ordinary (not restartable) init
            # containers. Fail rather than silently miscount future sidecars.
            self.assertFalse(any(c.get('restartPolicy') == 'Always'
                                 for c in pod.get('initContainers', [])))
            def cpu(c):
                return quantity(c.get('resources', {}).get('requests', {}).get('cpu', 0))
            total = sum(cpu(c) for c in pod['containers'])
            init = max((cpu(c) for c in pod.get('initContainers', [])), default=0)
            return max(total, init) + quantity(pod.get('overhead', {}).get('cpu', 0))
        def workloads(objects):
            return {o['metadata']['name']: o for o in objects
                    if o['kind'] in ('Deployment', 'StatefulSet')}
        before, after = workloads(self.before), workloads(self.actual)
        self.assertEqual(before.keys(), after.keys())
        savings = 0
        for name, obj in after.items():
            replicas = obj['spec'].get('replicas', 1)
            self.assertEqual(replicas, before[name]['spec'].get('replicas', 1))
            savings += replicas * (effective(before[name]['spec']['template']['spec'])
                                   - effective(obj['spec']['template']['spec']))
        # 750m Toolbox + 500m Workhorse; PostgreSQL adds another 750m.
        self.assertAlmostEqual(savings, 1.25)
        self.assertAlmostEqual(savings + 1 - .25, 2)


if __name__ == '__main__':
    unittest.main()
