"""Offline selected data-stage placement, persistence and public-trust contract."""
from pathlib import Path
import unittest
import yaml
from fixtures.render_helpers import build

ROOT = Path(__file__).resolve().parents[2]


class DataPrerequisites(unittest.TestCase):
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
