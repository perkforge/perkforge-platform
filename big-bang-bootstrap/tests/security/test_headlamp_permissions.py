"""Offline checks; synthetic API fixtures never target a live cluster."""
from collections import Counter
from copy import deepcopy
import os, subprocess, tempfile, unittest, base64, uuid
from pathlib import Path
import yaml
from fixtures.render_helpers import build, child_values, helm, ordered_values, release_name
from fixtures.resource_inventory import inventory
from fixtures.lookup_server import lookup_server, secret_allowed
ROOT = Path(__file__).resolve().parents[2]
EXAMPLES = ROOT
EX = ROOT
CLUSTER = ROOT / 'clusters/local'
STAGE = ROOT / 'configuration/identity'
from fixtures.package_context import HeadlampFixture

class HeadlampPermissionTests(HeadlampFixture):
    def test_namespaces_have_one_owner_and_no_installer_cluster_rights(self):
        self.assertEqual({o['metadata']['name'] for o in self.outer_raw if o['kind'] == 'Namespace'}, {'headlamp','keycloak'})
        self.assertFalse(any(o['kind'] == 'Namespace' for o in self.root + self.outer + self.child))
        for obj in self.foundation:
            self.assertNotIn(obj['kind'], ['ClusterRole', 'ClusterRoleBinding'])
            if obj['kind'] == 'Role':
                for rule in obj['rules']:
                    self.assertNotIn('*', rule['verbs'] + rule['apiGroups'] + rule['resources'])
                    self.assertFalse(set(rule['resources']) & {'roles', 'rolebindings', 'namespaces',
                                     'pods/exec', 'pods/portforward', 'serviceaccounts/token'})
            if obj['kind'] == 'RoleBinding':
                self.assertEqual(obj['roleRef']['kind'], 'Role')
        for identity in [('flux-system', 'platform-reconciler'), ('bigbang', 'platform-reconciler'),
                         ('bigbang', 'headlamp-installer')]:
            for verb in ['create', 'patch', 'delete']:
                self.assertFalse(self.allowed(identity, '', '', 'namespaces', verb))
                self.assertFalse(self.allowed(identity, 'kube-system', '', 'secrets', verb))

    def test_rbac_covers_actual_render_and_helm_readiness_without_ui_grants(self):
        kinds = {'ConfigMap': ('', 'configmaps'), 'Secret': ('', 'secrets'),
                 'GitRepository': ('source.toolkit.fluxcd.io', 'gitrepositories'),
                 'HelmRelease': ('helm.toolkit.fluxcd.io', 'helmreleases'),
                 'ServiceAccount': ('', 'serviceaccounts'), 'Service': ('', 'services'),
                 'Deployment': ('apps', 'deployments')}
        for objects, identity, verbs in [
            ([o for o in self.root if o['metadata']['namespace'] == 'bigbang'], ('flux-system', 'platform-reconciler'), ['get', 'list', 'watch', 'create', 'patch', 'update']),
            (self.outer, ('bigbang', 'platform-reconciler'), ['get', 'list', 'watch', 'create', 'patch', 'update', 'delete']),
            (self.child, ('bigbang', 'headlamp-installer'), ['get', 'list', 'watch', 'create', 'patch', 'update', 'delete']),
        ]:
            for obj in objects:
                group, resource = kinds[obj['kind']]
                for verb in verbs:
                    self.assertTrue(self.allowed(identity, obj['metadata']['namespace'], group, resource, verb),
                                    (identity, obj['kind'], verb))
        child = ('bigbang', 'headlamp-installer')
        for verb in ['get', 'list', 'watch']:
            self.assertTrue(self.allowed(child, 'headlamp', '', 'pods', verb))
            self.assertTrue(self.allowed(child, 'headlamp', 'apps', 'replicasets', verb))
        for verb in ['create', 'patch', 'delete']:
            self.assertFalse(self.allowed(child, 'headlamp', '', 'pods', verb))
            self.assertFalse(self.allowed(child, 'headlamp', 'apps', 'replicasets', verb))
        self.assertTrue(self.allowed(child, 'bigbang', '', 'secrets', 'create'))
        self.assertFalse(self.allowed(child, 'headlamp', '', 'secrets', 'get'))
        self.assertFalse(self.allowed(('flux-system', 'platform-reconciler'), 'bigbang', '', 'secrets', 'get'))
        app_sa = next(o['metadata']['name'] for o in self.child if o['kind'] == 'ServiceAccount')
        self.assertEqual(app_sa, 'headlamp-headlamp')
        for ns in ['headlamp', 'bigbang', 'kube-system']:
            self.assertFalse(self.allowed(('headlamp', app_sa), ns, '', 'secrets', 'get'))
        self.assertFalse(any(o['kind'].endswith('RoleBinding') for o in self.child))
