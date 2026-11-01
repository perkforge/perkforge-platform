"""Render the actual ordered stage roots; never contact a cluster or apply objects."""
import os
from pathlib import Path
import unittest
import yaml
from fixtures.render_helpers import build, helm, ordered_values, child_values, release_name

ROOT = Path(__file__).resolve().parents[2]

class AppStages(unittest.TestCase):
    def test_same_artifact_forward_selection_and_database_boundary(self):
        sources = Path(os.environ['PREFLIGHT_SOURCES_DIR'])
        previous = set()
        stable = None
        for path, expected in [
            ('local', {'longhorn', 'rancher', 'openbao'}),
            ('local-headlamp', {'longhorn', 'rancher', 'openbao', 'headlamp'}),
            ('local-keycloak', {'longhorn', 'rancher', 'openbao', 'headlamp', 'keycloak'}),
        ]:
            with self.subTest(stage=path):
                objects = build(ROOT / 'clusters' / path)
                parent = next(o for o in objects if o['kind'] == 'HelmRelease')
                refs = parent['spec']['valuesFrom']
                self.assertEqual(refs[-1], {'kind': 'ConfigMap', 'name': 'values-app-stage', 'valuesKey': 'values.yaml'})
                self.assertNotIn('values', parent['spec'])
                outer = helm(sources / 'bigbang/chart', 'bigbang', 'bigbang', ordered_values(objects, parent))
                children = {o['metadata']['name']: o for o in outer if o['kind'] == 'HelmRelease'}
                self.assertEqual(set(children), expected)
                self.assertTrue(previous <= set(children))
                previous = set(children)
                # Changing stage adds packages; it does not mutate running storage/management contracts.
                retained = {n: children[n] for n in ['longhorn', 'rancher', 'openbao']}
                if stable is None: stable = retained
                self.assertEqual(retained, stable)
                self.assertFalse(any(o['kind'] in ['Role', 'RoleBinding', 'ClusterRole', 'ClusterRoleBinding'] for o in objects))
                self.assertFalse(any('oidc.yaml' in o.get('data', {}) for o in objects))
                if 'keycloak' in children:
                    hr = children['keycloak']
                    rendered = helm(sources / 'keycloak/chart', release_name(hr), 'keycloak', child_values(outer, 'keycloak'))
                    self.assertEqual({o['metadata']['name'] for o in rendered if o['kind'] == 'StatefulSet'}, {'keycloak-keycloak', 'keycloak-postgresql'})
                else:
                    self.assertFalse(any(o['kind'] in ['StatefulSet', 'PersistentVolumeClaim'] for o in outer))

    def test_missing_final_selection_is_not_an_optional_fallback(self):
        objects = build(ROOT / 'clusters/local')
        parent = next(o for o in objects if o['kind'] == 'HelmRelease')
        without_gate = [o for o in objects if o['metadata']['name'] != 'values-app-stage']
        with self.assertRaises(KeyError):
            ordered_values(without_gate, parent)
