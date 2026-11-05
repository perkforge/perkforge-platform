"""Pinned application hooks/workloads must reference the approved local pull Secret."""
import copy
import os
import re
import unittest
from pathlib import Path
import yaml
from fixtures.render_helpers import build, helm, ordered_values, child_values, release_name

ROOT = Path(__file__).resolve().parents[2]


class GitLabImagePullReferences(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        sources = Path(os.environ['PREFLIGHT_SOURCES_DIR'])
        root = build(ROOT/'clusters/local-gitlab-app')
        parent = next(x for x in root if x['kind'] == 'HelmRelease'
                      and x['metadata']['name'] == 'bigbang')
        outer = helm(sources/'bigbang/chart', 'bigbang', 'bigbang', ordered_values(root, parent))
        release = next(x for x in outer if x['kind'] == 'HelmRelease'
                       and x['metadata']['name'] == 'gitlab')
        values = child_values(outer, 'gitlab')
        cls.current = helm(sources/'gitlab/chart', release_name(release), 'gitlab', values)
        previous = []
        for value in values:
            d = yaml.safe_load(value)
            # Remove only authored overlay references. Leave Big Bang's empty
            # defaults in place to reproduce the actual anonymous pull failure.
            if d.get('global', {}).get('imagePullSecrets') == [{'name': 'private-registry'}]:
                d['global'].pop('imagePullSecrets')
                d['global'].get('image', {}).pop('pullSecrets', None)
                if d['global'].get('image') == {}:
                    d['global'].pop('image')
            previous.append(yaml.safe_dump(d))
        cls.previous = helm(sources/'gitlab/chart', release_name(release), 'gitlab', previous)

    @staticmethod
    def podspec(obj):
        if obj['kind'] == 'Pod':
            return obj['spec']
        if obj['kind'] in ['Deployment', 'StatefulSet', 'DaemonSet', 'Job']:
            return obj['spec']['template']['spec']
        if obj['kind'] == 'CronJob':
            return obj['spec']['jobTemplate']['spec']['template']['spec']
        return None

    def test_every_hook_init_container_and_workload_uses_only_local_secret(self):
        pods = [(o, self.podspec(o)) for o in self.current if self.podspec(o) is not None]
        self.assertEqual(len(pods), 9)  # five workloads, migrations, and three Helm hooks
        jobs = [o for o, _ in pods if o['kind'] == 'Job']
        self.assertEqual(len(jobs), 4)
        self.assertTrue(any(o['metadata']['name'].endswith('-selfsign') for o in jobs))
        for obj, spec in pods:
            self.assertEqual(obj['metadata']['namespace'], 'gitlab')
            self.assertEqual(spec['imagePullSecrets'], [{'name': 'private-registry'}],
                             obj['metadata']['name'])
            containers = spec['containers'] + spec.get('initContainers', [])
            self.assertTrue(containers)
            self.assertTrue(any(c['image'].startswith('registry1.dso.mil/') for c in containers))
        old = [self.podspec(o) for o in self.previous if self.podspec(o) is not None]
        self.assertEqual(len(old), 9)
        self.assertTrue(all(not s.get('imagePullSecrets') for s in old))

    def test_only_references_and_values_hashed_job_names_change(self):
        def normalized(objects, remove_refs):
            objects = copy.deepcopy(objects)
            for obj in objects:
                spec = self.podspec(obj)
                if spec is not None and remove_refs:
                    spec.pop('imagePullSecrets')
            def stable(value):
                if isinstance(value, str):
                    return re.sub(r'(gitlab-(?:shared-secrets|migrations))-[0-9a-f]{7}(?=-selfsign|$)',
                                  r'\1-VALUESHASH', value)
                if isinstance(value, list):
                    return [stable(x) for x in value]
                if isinstance(value, dict):
                    return {k: stable(v) for k, v in value.items()}
                return value
            return {(o['kind'], o['metadata'].get('namespace'), o['metadata']['name']): o
                    for o in stable(objects)}
        self.assertEqual(normalized(self.current, True), normalized(self.previous, False))
        self.assertFalse(any(o['kind'] == 'Secret' and o['metadata']['name'] == 'private-registry'
                             for o in self.current))
        # Namespace and RBAC authority are unchanged by an image reference fix.
        self.assertFalse(any(o['kind'] in ['Namespace', 'ClusterRole', 'ClusterRoleBinding']
                             for o in self.current))

    def test_hashed_preinstall_hooks_change_names_without_failed_hook_cleanup(self):
        def hooks(objects):
            return [o for o in objects if o['kind'] == 'Job'
                    and 'pre-install' in (o['metadata'].get('annotations') or {}).get('helm.sh/hook', '')]
        old, new = hooks(self.previous), hooks(self.current)
        self.assertEqual(len(old), 2)
        self.assertEqual(len(new), 2)
        self.assertTrue({x['metadata']['name'] for x in old}.isdisjoint(
                        {x['metadata']['name'] for x in new}))
        for job in old + new:
            policies = set(job['metadata']['annotations']['helm.sh/hook-delete-policy'].split(','))
            self.assertEqual(policies, {'hook-succeeded', 'before-hook-creation'})
            self.assertNotIn('hook-failed', policies)
