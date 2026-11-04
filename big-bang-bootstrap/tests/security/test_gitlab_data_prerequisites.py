"""Offline selected data-stage placement, persistence and public-trust contract."""
from pathlib import Path
import json
import unittest
import yaml
from fixtures.render_helpers import build

ROOT = Path(__file__).resolve().parents[2]


class DataPrerequisites(unittest.TestCase):
    def test_garage_effective_argv_uses_the_pinned_image_executable(self):
        image = json.loads((ROOT/'tests/fixtures/garage-image-runtime-evidence.json').read_text())
        objects = build(ROOT/'clusters/local-gitlab-data')
        garage = next(x for x in objects if x['kind'] == 'StatefulSet'
                      and x['metadata']['name'] == 'gitlab-garage')
        container = next(x for x in garage['spec']['template']['spec']['containers']
                         if x['name'] == 'garage')
        self.assertEqual(container['image'], image['image'])
        self.assertIsNone(image['imageConfig']['Entrypoint'])
        self.assertEqual(image['imageConfig']['Cmd'], ['/garage', 'server'])
        # Kube command replaces ENTRYPOINT; args replace CMD. The old args-only
        # manifest attempted to exec '-c', despite the image CMD.
        def argv(pod_container):
            return ((pod_container.get('command') or image['imageConfig']['Entrypoint'] or [])
                    + (pod_container.get('args') or image['imageConfig']['Cmd'] or []))
        self.assertEqual(argv(container), ['/garage', '-c', '/etc/garage/garage.toml', 'server'])
        old = {k: v for k, v in container.items() if k != 'command'}
        self.assertEqual(argv(old)[0], '-c')
        self.assertNotEqual(argv(old)[0], image['imageConfig']['Cmd'][0])

    def test_both_new_pvc_consumers_require_prepared_workers(self):
        objects = build(ROOT / 'clusters/local-gitlab-data')
        pg = next(x for x in objects if x['kind'] == 'Cluster')
        garage = next(x for x in objects if x['kind'] == 'StatefulSet'
                      and x['metadata']['name'] == 'gitlab-garage')
        selector = {'storage.perkforge.io/worker': 'true'}
        self.assertEqual(pg['spec']['affinity']['nodeSelector'], selector)
        self.assertEqual(garage['spec']['template']['spec']['nodeSelector'], selector)
        self.assertEqual(pg['spec']['instances'], 1)
        self.assertEqual(pg['spec']['storage'], {'storageClass': 'longhorn', 'size': '16Gi'})
        self.assertEqual(garage['spec']['replicas'], 1)
        self.assertEqual(garage['spec']['persistentVolumeClaimRetentionPolicy'],
                         {'whenDeleted': 'Retain', 'whenScaled': 'Retain'})
        claims = {x['metadata']['name']: x['spec'] for x in garage['spec']['volumeClaimTemplates']}
        self.assertEqual({n: x['resources']['requests']['storage'] for n, x in claims.items()},
                         {'meta': '1Gi', 'objects': '32Gi'})
        self.assertTrue(all(x['storageClassName'] == 'longhorn' for x in claims.values()))
        self.assertFalse(garage['spec']['template']['spec']['automountServiceAccountToken'])

    def test_existing_provider_objects_preserved_and_app_still_disabled(self):
        def indexed(path):
            return {(x['kind'], x['metadata'].get('namespace'), x['metadata']['name']): x
                    for x in build(ROOT / path)}
        providers = indexed('clusters/local-gitlab-providers')
        data = indexed('clusters/local-gitlab-data')
        for k, value in providers.items():
            self.assertEqual(data[k], value)
        self.assertFalse(any(k[0] == 'HelmRelease' and k[2] in ('gitlab', 'gitlab-runner')
                             for k in data))
        candidate = yaml.safe_load((ROOT/'configuration/packages/gitlab/candidate-values.yaml').read_text())
        self.assertFalse(candidate['addons']['gitlab']['enabled'])
        self.assertTrue(candidate['addons']['gitlab']['flux']['suspend'])

    def test_operator_ca_and_explicit_client_rotation_are_documented(self):
        pg = yaml.safe_load((ROOT/'configuration/packages/gitlab/data-services/runtime/postgres.yaml').read_text())
        self.assertNotIn('certificates', pg['spec'])  # operator-managed, not an unreviewed external CA
        self.assertFalse(pg['spec']['enableSuperuserAccess'])
        self.assertIn('hostnossl all all all reject', pg['spec']['postgresql']['pg_hba'])
        doc = (ROOT/'configuration/packages/gitlab/postgres-ca-lifecycle.md').read_text()
        for text in ('status.certificates.serverCASecret', 'exact Cluster UID', 'only `ca.crt`',
                     'verify-full', '90-day', '7 days', 'immutable', 'separately approved',
                     'UID/resourceVersion', 'consumer Pods', 'ca.key'):
            self.assertIn(text, doc)


if __name__ == '__main__':
    unittest.main()
