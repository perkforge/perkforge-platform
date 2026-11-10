"""Paused physical Portal wiring and its actual published dependency chain."""
import copy
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

import yaml
from fixtures.render_helpers import build, helm, ordered_values
from fixtures.selection import context, release_for

ROOT = Path(__file__).resolve().parents[2]
CONTEXT = {'cluster': 'local', 'environment': 'local', 'profile': 'il2'}


def evidence():
    return json.loads((ROOT.parent / 'release-evidence.json').read_text())['dependencies']


def pair():
    objects = build(ROOT / 'enrollments/local-portal')
    return (next(o for o in objects if o['kind'] == 'GitRepository'),
            next(o for o in objects if o['kind'] == 'Kustomization'))


def canonical(objects):
    return sorted(json.dumps(o, sort_keys=True) for o in objects)


class PhysicalPortalSourceTests(unittest.TestCase):
    def test_independent_source_is_published_public_and_paused(self):
        objects = build(ROOT / 'enrollments/local-portal')
        self.assertEqual(len(objects), 2)
        self.assertEqual({o['kind'] for o in objects}, {'GitRepository', 'Kustomization'})
        for obj in objects:
            self.assertEqual(obj['metadata']['name'], 'portal-enrollments')
            self.assertEqual(obj['metadata']['namespace'], 'flux-system')
            self.assertTrue(obj['spec']['suspend'])
            self.assertEqual(context(obj), CONTEXT)
        source, _ = pair()
        release_for(source, evidence()['physical-portal-enrollment'])
        self.assertNotIn('secretRef', source['spec'])
        self.assertNotIn('serviceAccountName', source['spec'])

    def test_parent_uses_its_own_source_without_pruning_or_force(self):
        _, parent = pair()
        spec = parent['spec']
        self.assertEqual(spec['sourceRef'], {'kind': 'GitRepository', 'name': 'portal-enrollments'})
        self.assertEqual(spec['path'], './clusters/local')
        self.assertEqual(spec['serviceAccountName'], 'tenant-enrollment-admin')
        self.assertFalse(spec['prune'])
        self.assertFalse(spec['force'])
        self.assertTrue(spec['wait'])
        self.assertNotIn('targetNamespace', spec)

    def test_nextcloud_and_historical_selections_are_not_retargeted(self):
        for directory, dependency, tag, selected_path, suspended in [
            ('local-nextcloud', 'nextcloud-enrollment', 'v1.5.4', './clusters/local-nextcloud', False),
            ('local', 'enrollment', 'v1.0.0', './clusters/local', True),
        ]:
            with self.subTest(directory=directory):
                objects = build(ROOT / 'enrollments' / directory)
                source = next(o for o in objects if o['kind'] == 'GitRepository')
                parent = next(o for o in objects if o['kind'] == 'Kustomization')
                release_for(source, evidence()[dependency])
                self.assertEqual(source['spec']['ref'], {'tag': tag})
                self.assertEqual(parent['spec']['path'], selected_path)
                self.assertEqual(parent['spec']['sourceRef']['name'], 'tenant-enrollments')
                self.assertEqual(parent['spec']['serviceAccountName'], 'tenant-enrollment-admin')
                self.assertFalse(parent['spec']['prune'])
                self.assertTrue(all(o['spec']['suspend'] == suspended for o in objects))

    def test_all_existing_cluster_roots_exclude_the_independent_pair(self):
        for recipe in sorted((ROOT / 'clusters').glob('*/kustomization.yaml')):
            with self.subTest(root=recipe.parent.name):
                self.assertFalse(any(o['metadata']['name'] == 'portal-enrollments'
                                     for o in build(recipe.parent)))

    def test_explicit_opt_in_preserves_existing_platform_and_nextcloud_objects(self):
        for stage in ['local-velero', 'local-external-secrets']:
            with self.subTest(stage=stage), tempfile.TemporaryDirectory() as directory:
                baseline = build(ROOT / 'clusters' / stage)
                copied = Path(directory) / 'bootstrap'
                shutil.copytree(ROOT, copied, ignore=shutil.ignore_patterns('tests', '__pycache__'))
                test_root = copied / 'clusters/portal-opt-in-test'
                test_root.mkdir()
                (test_root / 'kustomization.yaml').write_text(yaml.safe_dump({
                    'apiVersion': 'kustomize.config.k8s.io/v1beta1', 'kind': 'Kustomization',
                    'resources': ['../' + stage, '../../enrollments/local-portal']}))
                combined = build(test_root)
                added = [o for o in combined if o['metadata']['name'] == 'portal-enrollments']
                retained = [o for o in combined if o['metadata']['name'] != 'portal-enrollments']
                self.assertEqual(canonical(retained), canonical(baseline))
                self.assertEqual(canonical(added), canonical(build(ROOT / 'enrollments/local-portal')))
                identities = [(o['apiVersion'], o['kind'], o['metadata'].get('namespace'),
                               o['metadata']['name']) for o in combined]
                self.assertEqual(len(identities), len(set(identities)))

    def test_wrong_tag_and_repository_evidence_are_rejected(self):
        source, _ = pair()
        for field, value in [('tag', 'v1.0.0'), ('repository', 'perkforge/unrelated')]:
            bad = copy.deepcopy(evidence()['physical-portal-enrollment'])
            bad[field] = value
            with self.subTest(field=field), self.assertRaises(AssertionError):
                release_for(source, bad)


@unittest.skipUnless(os.environ.get('PHYSICAL_PORTAL_ENROLLMENT_CHECKOUT') and
                     os.environ.get('PHYSICAL_PORTAL_APP_CHECKOUT'),
                     'exact published physical Portal enrollment/app checkouts required')
class PublishedPhysicalPortalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.enrollment = Path(os.environ['PHYSICAL_PORTAL_ENROLLMENT_CHECKOUT']).resolve()
        cls.app = Path(os.environ['PHYSICAL_PORTAL_APP_CHECKOUT']).resolve()

    def assert_checkout(self, checkout, recorded):
        for ref in ['HEAD', recorded['tag'] + '^{commit}']:
            actual = subprocess.check_output(['git', '-C', str(checkout), 'rev-parse', ref], text=True).strip()
            self.assertEqual(actual, recorded['resolvedCommit'])
        self.assertEqual(subprocess.check_output(['git', '-C', str(checkout), 'status',
                         '--porcelain', '--untracked-files=no'], text=True), '')
        origin = subprocess.check_output(['git', '-C', str(checkout), 'remote', 'get-url', 'origin'], text=True).strip()
        self.assertEqual(origin.removesuffix('.git'), 'https://github.com/' + recorded['repository'])

    def enrollment_objects(self):
        source, parent = pair()
        self.assert_checkout(self.enrollment, evidence()['physical-portal-enrollment'])
        target = (self.enrollment / parent['spec']['path']).resolve()
        self.assertTrue(target.is_relative_to(self.enrollment))
        return build(target)

    def test_published_enrollment_is_exact_and_keeps_all_child_reconcilers_paused(self):
        objects = self.enrollment_objects()
        self.assertEqual(len(objects), 2)
        self.assertEqual({o['kind'] for o in objects}, {'GitRepository', 'Kustomization'})
        for obj in objects:
            self.assertEqual(obj['metadata']['namespace'], 'tenant-portal-config')
            self.assertTrue(obj['spec']['suspend'])
            self.assertEqual(context(obj), CONTEXT)
        parent = next(o for o in objects if o['kind'] == 'Kustomization')
        self.assertEqual(parent['spec']['serviceAccountName'], 'portal-reconciler')
        self.assertEqual(parent['spec']['targetNamespace'], 'tenant-portal-config')
        self.assertFalse(parent['spec']['prune'])
        self.assertEqual(parent['spec']['path'], './gitops/clusters/local')

    def test_actual_app_is_exact_disabled_and_uses_physical_identity(self):
        enrolled = self.enrollment_objects()
        source = next(o for o in enrolled if o['kind'] == 'GitRepository')
        parent = next(o for o in enrolled if o['kind'] == 'Kustomization')
        recorded = json.loads((self.enrollment / 'release-evidence.json').read_text())['dependencies']['portal']
        release_for(source, recorded)
        self.assert_checkout(self.app, recorded)
        objects = build(self.app / parent['spec']['path'])
        release = next(o for o in objects if o['kind'] == 'HelmRelease')
        self.assertTrue(release['spec']['suspend'])
        self.assertEqual(release['spec']['serviceAccountName'], 'portal-deployer')
        self.assertEqual(release['spec']['targetNamespace'], 'tenant-portal')
        self.assertEqual(release['spec']['storageNamespace'], 'tenant-portal-release')
        self.assertTrue(all(context(o) == CONTEXT for o in objects))
        values = ordered_values(objects, release)
        local = yaml.safe_load(values[-1])
        self.assertFalse(local['enabled'])
        self.assertEqual(local['portalOrigin'], 'https://portal.perkforge.home.arpa')
        self.assertEqual(local['identity']['issuer'], 'https://keycloak.perkforge.home.arpa/auth/realms/perkforge')
        self.assertEqual(local['accessPolicy'], 'platform-admins')
        self.assertEqual(helm(self.app / release['spec']['chart']['spec']['chart'],
                              'portal', 'tenant-portal', values), [])

    def test_runtime_permissions_and_eso_stores_are_not_implicitly_enrolled(self):
        objects = self.enrollment_objects()
        self.assertFalse(any(o['kind'] in {'Role', 'RoleBinding', 'Secret', 'SecretStore',
                                         'ClusterSecretStore', 'ExternalSecret'} for o in objects))
        foundation = build(self.enrollment / 'tenants/portal/foundation')
        binding = next(o for o in foundation if o['kind'] == 'RoleBinding' and
                       o['metadata']['name'] == 'portal-enrollment')
        self.assertEqual(binding['metadata']['namespace'], 'tenant-portal-config')
        self.assertEqual(binding['subjects'], [{'kind': 'ServiceAccount',
                         'name': 'tenant-enrollment-admin', 'namespace': 'flux-system'}])
        self.assertFalse(any(o['kind'] in {'SecretStore', 'ClusterSecretStore', 'ExternalSecret'}
                             for o in foundation))
