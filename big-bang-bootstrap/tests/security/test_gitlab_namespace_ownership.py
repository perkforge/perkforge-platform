"""Exercise Flux's actual Helm post-renderer with the pinned enabled app stage."""
from pathlib import Path
import copy
import os
import tempfile
import unittest
import yaml
from fixtures.render_helpers import build, helm, ordered_values

ROOT = Path(__file__).resolve().parents[2]


class GitLabNamespaceOwnership(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = build(ROOT/'clusters/local-gitlab-app')
        cls.parent = next(x for x in cls.root if x['kind'] == 'HelmRelease'
                          and x['metadata']['name'] == 'bigbang')
        cls.raw = helm(Path(os.environ['PREFLIGHT_SOURCES_DIR'])/'bigbang/chart',
                       'bigbang', 'bigbang', ordered_values(cls.root, cls.parent))
        cls.renderer = cls.parent['spec']['postRenderers'][0]['kustomize']
        cls.current = cls.render(cls.raw, cls.renderer)

    @staticmethod
    def render(objects, renderer):
        with tempfile.TemporaryDirectory(prefix='gitlab-namespace-owner-') as directory:
            p = Path(directory)
            (p/'objects.yaml').write_text(yaml.safe_dump_all(objects))
            (p/'kustomization.yaml').write_text(yaml.safe_dump({
                'apiVersion': 'kustomize.config.k8s.io/v1beta1', 'kind': 'Kustomization',
                'resources': ['objects.yaml'], **renderer}))
            return build(p)

    @staticmethod
    def indexed(objects):
        return {(x['kind'], x['metadata'].get('namespace'), x['metadata']['name']): x
                for x in objects}

    def test_regression_old_renderer_attempts_namespace_and_only_that_object_is_removed(self):
        legacy = copy.deepcopy(self.renderer)
        legacy['patches'] = [p for p in legacy['patches']
                             if p['target'] != {'kind': 'Namespace', 'name': 'gitlab'}]
        old = self.indexed(self.render(self.raw, legacy))
        key = ('Namespace', None, 'gitlab')
        self.assertIn(key, old)  # reproduces the real Helm ownership/RBAC failure
        old.pop(key)
        self.assertEqual(self.indexed(self.current), old)
        namespace_only = {'patches': [p for p in self.renderer['patches']
                                      if p['target'] == {'kind': 'Namespace', 'name': 'gitlab'}]}
        # The new deletion is idempotent. Existing unrelated append patches are
        # applied once to fresh Helm output by Flux, not to already patched output.
        self.assertEqual(self.indexed(self.render(self.current, namespace_only)), old)
        self.assertFalse(any(x['kind'] == 'Namespace' for x in self.current))

    def test_existing_foundation_and_unrelated_namespace_are_not_adopted_or_patched(self):
        foundation = build(ROOT/'configuration/packages/gitlab/prerequisites')
        ns = next(x for x in foundation if x['kind'] == 'Namespace')
        self.assertEqual(ns['metadata'], {'name': 'gitlab',
                         'labels': {'perkforge.io/owner': 'gitlab-foundation-v1'}})
        sentinel = {'apiVersion': 'v1', 'kind': 'Namespace',
                    'metadata': {'name': 'unrelated-fixture', 'labels': {'owner': 'foreign'}}}
        patched = self.indexed(self.render(self.raw + [sentinel], self.renderer))
        self.assertEqual(patched['Namespace', None, 'unrelated-fixture'], sentinel)
        self.assertFalse(any(x['kind'] in ['ClusterRole', 'ClusterRoleBinding']
                             for x in foundation))

    def test_existing_namespaced_umbrella_rbac_covers_every_remaining_rendered_object(self):
        foundation = build(ROOT/'configuration/packages/bigbang/prerequisites')
        role = next(x for x in foundation if x['kind'] == 'Role'
                    and x['metadata']['name'] == 'stage-umbrella-installer')
        kinds = {'Secret': ('', 'secrets'),
                 'GitRepository': ('source.toolkit.fluxcd.io', 'gitrepositories'),
                 'HelmRelease': ('helm.toolkit.fluxcd.io', 'helmreleases')}
        for obj in self.current:
            self.assertEqual(obj['metadata']['namespace'], 'bigbang')
            group, resource = kinds[obj['kind']]
            for verb in ['get', 'list', 'watch', 'create', 'update', 'patch', 'delete']:
                self.assertTrue(any(group in r['apiGroups'] and resource in r['resources']
                                    and verb in r['verbs'] for r in role['rules']),
                                (obj['kind'], obj['metadata']['name'], verb))
        self.assertFalse(any('namespaces' in r['resources'] for r in role['rules']))
        child = next(x for x in self.current if x['kind'] == 'HelmRelease'
                     and x['metadata']['name'] == 'gitlab')
        self.assertFalse(child['spec']['install']['createNamespace'])
        self.assertEqual(child['spec']['targetNamespace'], 'gitlab')
        self.assertFalse(any(x['kind'] == 'Secret' and x['metadata']['name'] == 'private-registry'
                             for x in self.current))
