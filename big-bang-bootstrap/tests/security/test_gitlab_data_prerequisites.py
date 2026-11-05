"""Offline selected data-stage placement, persistence and public-trust contract."""
from pathlib import Path
import json
import os
import copy
import re
import unittest
import yaml
from fixtures.render_helpers import build, helm, ordered_values, child_values, release_name

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

    def test_selected_gitaly_requires_longhorn_worker_without_other_runtime_changes(self):
        sources = Path(os.environ['PREFLIGHT_SOURCES_DIR'])
        objects = build(ROOT / 'clusters/local-gitlab-app')
        parent = next(x for x in objects if x['kind'] == 'HelmRelease'
                      and x['metadata']['name'] == 'bigbang')
        outer = helm(sources/'bigbang/chart', 'bigbang', 'bigbang', ordered_values(objects, parent))
        release = next(x for x in outer if x['kind'] == 'HelmRelease'
                       and x['metadata']['name'] == 'gitlab')
        values = child_values(outer, 'gitlab')
        actual = helm(sources/'gitlab/chart', release_name(release), 'gitlab', values)
        previous = []
        for value in values:
            document = yaml.safe_load(value)
            document.get('upstream', {}).get('gitlab', {}).get('gitaly', {}).pop('nodeSelector', None)
            previous.append(yaml.safe_dump(document))
        baseline = helm(sources/'gitlab/chart', release_name(release), 'gitlab', previous)
        def indexed(items):
            # The upstream chart embeds a full-values hash in the two shared-
            # secrets hook Job names; changing placement legitimately changes it.
            def stable(value):
                if isinstance(value, str):
                    return re.sub(r'gitlab-shared-secrets-[0-9a-f]{7}(?=-selfsign|$)',
                                  'gitlab-shared-secrets-VALUESHASH', value)
                if isinstance(value, list):
                    return [stable(x) for x in value]
                if isinstance(value, dict):
                    return {k: stable(v) for k, v in value.items()}
                return value
            items = stable(items)
            return {(x['kind'], x['metadata'].get('namespace'), x['metadata']['name']): x
                    for x in items}
        current, old = indexed(actual), indexed(baseline)
        self.assertEqual(set(current), set(old))
        key = next(k for k in current if k[0] == 'StatefulSet' and k[2] == 'gitlab-gitaly')
        gitaly = current[key]
        selector = gitaly['spec']['template']['spec']['nodeSelector']
        self.assertEqual(selector, {'storage.perkforge.io/worker': 'true'})
        # Negative eligibility case: a node without the storage-worker label
        # (including the observed control-plane node) cannot satisfy this selector.
        for labels, eligible in [({}, False), ({'storage.perkforge.io/worker': 'false'}, False),
                                 ({'storage.perkforge.io/worker': 'true'}, True)]:
            self.assertEqual(all(labels.get(k) == v for k, v in selector.items()), eligible)
        self.assertEqual(gitaly['spec']['replicas'], 1)
        claim = gitaly['spec']['volumeClaimTemplates'][0]['spec']
        self.assertEqual(claim['storageClassName'], 'longhorn')
        self.assertEqual(claim['resources']['requests']['storage'], '10Gi')
        restored = copy.deepcopy(current)
        restored[key]['spec']['template']['spec'].pop('nodeSelector')
        self.assertEqual(restored, old)  # no image, sizing, credential or other object changes
        review = yaml.safe_load((ROOT/'configuration/packages/gitlab/lab-values.yaml').read_text())
        self.assertFalse(review['addons']['gitlab']['enabled'])
        self.assertTrue(review['addons']['gitlab']['flux']['suspend'])

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
