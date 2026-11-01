"""Pinned rendered installer contract; offline model, not a Kubernetes authorizer."""
from copy import deepcopy
import os
from pathlib import Path
import unittest

from fixtures.render_helpers import build, helm, ordered_values

ROOT = Path(__file__).resolve().parents[2]
ADMIN_BIND = {'apiGroups': ['rbac.authorization.k8s.io'],
              'resources': ['clusterroles'], 'resourceNames': ['cluster-admin'],
              'verbs': ['bind']}


class LonghornInstallerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        sources = Path(os.environ['PREFLIGHT_SOURCES_DIR'])
        root = build(ROOT / 'clusters/local')
        parent = next(o for o in root if o['kind'] == 'HelmRelease')
        outer = helm(sources / 'bigbang/chart', 'bigbang', 'bigbang', ordered_values(root, parent))
        child = next(o for o in outer if o['kind'] == 'HelmRelease' and o['metadata']['name'] == 'longhorn')
        assert child['spec']['serviceAccountName'] == 'longhorn-installer'
        assert not child['spec'].get('postRenderers')
        values = next(o for o in outer if o['kind'] == 'Secret' and o['metadata']['name'] == 'longhorn-values')['stringData']['values.yaml']
        cls.objects = helm(sources / 'longhorn', 'longhorn', 'longhorn-system', [values])
        foundation = build(ROOT / 'configuration/packages/longhorn/prerequisites')
        cls.foundation = foundation
        roles = {(o['kind'], o['metadata'].get('namespace'), o['metadata']['name']): o
                 for o in foundation if o['kind'] in ['Role', 'ClusterRole']}
        cls.policies = []
        for binding in foundation:
            if binding['kind'] not in ['RoleBinding', 'ClusterRoleBinding']:
                continue
            if {'kind': 'ServiceAccount', 'name': 'longhorn-installer', 'namespace': 'bigbang'} not in binding['subjects']:
                continue
            ref = binding['roleRef']
            namespace = binding['metadata'].get('namespace') if ref['kind'] == 'Role' else None
            # Release-storage Role lives in common prerequisites, outside chart RBAC.
            if (ref['kind'], namespace, ref['name']) in roles:
                cls.policies.append(roles[ref['kind'], namespace, ref['name']])

    @staticmethod
    def allowed(policies, namespace, resource, name, verb, group='rbac.authorization.k8s.io'):
        return any(group in rule['apiGroups'] and resource in rule['resources']
                   and verb in rule['verbs'] and (not rule.get('resourceNames') or name in rule['resourceNames'])
                   for role in policies if role['kind'] == 'ClusterRole' or role['metadata']['namespace'] == namespace
                   for rule in role['rules'])

    def test_all_rendered_roles_and_binding_targets_authorized(self):
        self.assertEqual(len(self.objects), 64)
        roles = [o for o in self.objects if o['kind'] in ['Role', 'ClusterRole']]
        bindings = [o for o in self.objects if o['kind'] in ['RoleBinding', 'ClusterRoleBinding']]
        self.assertEqual(len(roles), 5)
        self.assertEqual(len(bindings), 6)
        for obj in roles:
            resource = 'clusterroles' if obj['kind'] == 'ClusterRole' else 'roles'
            with self.subTest(role=obj['metadata']['name'], scope=obj['kind']):
                self.assertTrue(self.allowed(self.policies, 'longhorn-system', resource, obj['metadata']['name'], 'escalate'))
        old = deepcopy(self.policies)
        for role in old:
            role['rules'] = [rule for rule in role['rules'] if rule != ADMIN_BIND]
        denied_before = []
        for binding in bindings:
            ref = binding['roleRef']
            resource = 'clusterroles' if ref['kind'] == 'ClusterRole' else 'roles'
            name = binding['metadata']['name']
            with self.subTest(binding=name):
                self.assertTrue(self.allowed(self.policies, 'longhorn-system', resource, ref['name'], 'bind'))
            if not self.allowed(old, 'longhorn-system', resource, ref['name'], 'bind'):
                denied_before.append(name)
        self.assertEqual(denied_before, ['longhorn-support-bundle'])

    def test_rendered_resource_crud_stays_within_installer_policy(self):
        resources = {'ConfigMap': 'configmaps', 'ServiceAccount': 'serviceaccounts',
                     'Service': 'services', 'Job': 'jobs', 'Deployment': 'deployments',
                     'DaemonSet': 'daemonsets', 'NetworkPolicy': 'networkpolicies',
                     'PriorityClass': 'priorityclasses', 'CustomResourceDefinition': 'customresourcedefinitions',
                     'Role': 'roles', 'RoleBinding': 'rolebindings',
                     'ClusterRole': 'clusterroles', 'ClusterRoleBinding': 'clusterrolebindings'}
        cluster_kinds = {'PriorityClass', 'CustomResourceDefinition', 'ClusterRole', 'ClusterRoleBinding'}
        for obj in self.objects:
            kind, name = obj['kind'], obj['metadata']['name']
            group = obj['apiVersion'].split('/')[0] if '/' in obj['apiVersion'] else ''
            namespace = None if kind in cluster_kinds else 'longhorn-system'
            for verb in ['get', 'create', 'update', 'patch', 'delete']:
                with self.subTest(kind=kind, name=name, verb=verb):
                    self.assertTrue(self.allowed(self.policies, namespace, resources[kind], name, verb, group))

    def test_admin_delta_is_bind_only_not_installer_admin_binding(self):
        rules = [rule for role in self.policies for rule in role['rules']]
        self.assertEqual([rule for rule in rules if 'cluster-admin' in rule.get('resourceNames', [])], [ADMIN_BIND])
        for verb in ['get', 'patch', 'update', 'delete', 'escalate']:
            self.assertFalse(self.allowed(self.policies, None, 'clusterroles', 'cluster-admin', verb))
        self.assertFalse(self.allowed(self.policies, None, 'clusterroles', 'unrelated-role', 'bind'))
        self.assertFalse(any(o['kind'] in ['RoleBinding', 'ClusterRoleBinding']
                             and o['roleRef']['name'] == 'cluster-admin' for o in self.foundation))
        self.assertFalse(any(o['kind'] == 'Ingress' for o in self.objects))
        # Record the upstream trust actually accepted, not a least-privilege claim.
        manager = next(o for o in self.objects if o['kind'] == 'ClusterRole' and o['metadata']['name'] == 'longhorn-role')
        self.assertTrue(any(rule['verbs'] == ['*'] and 'clusterroles' in rule['resources']
                            for rule in manager['rules']))
