"""Pinned offline render regression for CSI-capable placement and one PVC writer."""
import copy
import os
import tempfile
from pathlib import Path
import unittest
import yaml
from fixtures.render_helpers import build, helm

ROOT = Path(__file__).resolve().parents[2]


class ValkeyPlacement(unittest.TestCase):
    def render(self):
        objects = build(ROOT / 'clusters/local-gitlab-providers')
        release = next(x for x in objects if x['kind'] == 'HelmRelease'
                       and x['metadata']['name'] == 'gitlab-valkey')
        self.assertFalse(release['spec']['suspend'])
        ref = release['spec']['valuesFrom'][0]
        config = next(x for x in objects if x['kind'] == 'ConfigMap'
                      and x['metadata']['name'] == ref['name'])
        values = yaml.safe_load(config['data'][ref['valuesKey']])
        chart = Path(os.environ['PREFLIGHT_SOURCES_DIR']) / 'valkey'
        rendered = helm(chart, 'gitlab-valkey', 'gitlab', [yaml.safe_dump(values)])
        # Exercise Flux's actual Kustomize post-renderer, retaining the explicit
        # null that clears API-defaulted fields in Helm's three-way patch.
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            (path / 'objects.yaml').write_text(yaml.safe_dump_all(rendered))
            (path / 'kustomization.yaml').write_text(yaml.safe_dump({
                'resources': ['objects.yaml'],
                **release['spec']['postRenderers'][0]['kustomize']}))
            rendered = build(path)
        return values, chart, rendered

    def test_pvc_consumer_requires_storage_worker_and_cannot_surge(self):
        _, _, rendered = self.render()
        deployment = next(x for x in rendered if x['kind'] == 'Deployment')
        self.assertEqual(deployment['spec']['replicas'], 1)
        self.assertEqual(deployment['spec']['strategy'],
                         {'type': 'Recreate', 'rollingUpdate': None})
        pod = deployment['spec']['template']['spec']
        self.assertEqual(pod['nodeSelector'], {'storage.perkforge.io/worker': 'true'})
        claims = [v['persistentVolumeClaim']['claimName'] for v in pod['volumes']
                  if 'persistentVolumeClaim' in v]
        self.assertEqual(claims, ['gitlab-valkey'])
        # Model the observed topology: the schedulable control plane has no CSI;
        # both workers satisfy the explicit shared storage-capability contract.
        nodes = {'control-plane': {}, 'worker-a': {'storage.perkforge.io/worker': 'true'},
                 'worker-b': {'storage.perkforge.io/worker': 'true'},
                 'unprepared-worker': {'storage.perkforge.io/worker': 'false'}}
        eligible = {name for name, labels in nodes.items()
                    if all(labels.get(k) == v for k, v in pod['nodeSelector'].items())}
        self.assertEqual(eligible, {'worker-a', 'worker-b'})

    def test_only_placement_and_rollout_change_pvc_and_secrets_are_preserved(self):
        values, chart, actual = self.render()
        old = copy.deepcopy(values)
        old.pop('nodeSelector')
        old.pop('deploymentStrategy')
        baseline = helm(chart, 'gitlab-valkey', 'gitlab', [yaml.safe_dump(old)])
        def identity(x):
            return x['kind'], x['metadata'].get('namespace'), x['metadata']['name']
        before = {identity(x): x for x in baseline}
        after = {identity(x): copy.deepcopy(x) for x in actual}
        self.assertEqual(before.keys(), after.keys())
        for key, obj in after.items():
            if obj['kind'] == 'Deployment':
                obj['spec']['template']['spec'].pop('nodeSelector')
                obj['spec']['strategy'] = copy.deepcopy(before[key]['spec']['strategy'])
            self.assertEqual(obj, before[key], key)
        pvc = next(x for x in actual if x['kind'] == 'PersistentVolumeClaim')
        self.assertEqual(pvc['spec']['resources']['requests']['storage'], '2Gi')
        self.assertEqual(pvc['spec']['storageClassName'], 'longhorn')
        self.assertEqual(pvc['spec']['accessModes'], ['ReadWriteOnce'])


if __name__ == '__main__':
    unittest.main()
