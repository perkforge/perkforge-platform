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
from fixtures.package_context import IdentityFixture

class IdentityPermissionTests(IdentityFixture):
    def test_oidc_issuer_audience_pkce_ca_and_no_fallback(self):
        contract = yaml.safe_load((EX / 'configuration/identity/context.yaml').read_text())
        dep = next(o for o in self.children['headlamp'] if o['kind'] == 'Deployment')
        pod = dep['spec']['template']['spec']; c = pod['containers'][0]
        env = {e['name']: e.get('value') for e in c['env']}
        self.assertEqual(env['OIDC_ISSUER_URL'], contract['identity_issuer'])
        self.assertEqual(env['OIDC_VALIDATOR_ISSUER_URL'], contract['identity_issuer'])
        self.assertEqual(env['OIDC_CLIENT_ID'], contract['identity_client_id'])
        self.assertEqual(env['OIDC_VALIDATOR_CLIENT_ID'], contract['identity_client_id'])
        self.assertEqual(env['OIDC_CALLBACK_URL'], contract['identity_redirect'])
        self.assertEqual(env['OIDC_USE_PKCE'], 'true')
        self.assertEqual(env['OIDC_SCOPES'].split(','), ['openid', 'profile', 'email'])
        self.assertNotIn('OIDC_CLIENT_SECRET', env)
        self.assertEqual(c['envFrom'], [{'secretRef': {'name': 'headlamp-oidc'}}])
        self.assertIn('-oidc-ca-file=/identity-ca/ca.crt', c['args'])
        self.assertEqual(env['SSL_CERT_FILE'], '/identity-ca/ca.crt')
        self.assertFalse(any('unsafe' in a or 'use-access-token' in a for a in c['args']))
        api = yaml.safe_load((EX / 'configuration/identity/rke2-oidc.yaml').read_text())
        flags = dict(v.split('=', 1) for v in api['kube-apiserver-arg+'])
        self.assertEqual(flags['oidc-issuer-url'], contract['identity_issuer'])
        self.assertEqual(flags['oidc-client-id'], contract['identity_client_id'])
        self.assertEqual(flags['oidc-required-claim'], 'azp=' + contract['identity_client_id'])
        self.assertEqual(flags['oidc-groups-prefix'], 'oidc:')
        self.assertEqual(flags['oidc-username-claim'], 'sub')
        self.assertEqual(flags['oidc-signing-algs'], 'RS256')
        self.assertIn('/etc/hosts:/etc/hosts:ro', api['kube-apiserver-extra-mount+'])

    def test_rke2_automatic_ca_mount_cannot_overlap_explicit_mounts(self):
        # Source-grounded contract model, not execution of the RKE2 Pod renderer.
        # v1.36.5+rke2r1 / e1d699d2c3a3d3c1f3247c4f9eb140f20d369776:
        # pkg/executor/staticpod/staticpod.go writeTemplate calls ReadFiles(args);
        # pkg/podtemplate/podtemplate.go mounts existing argument files read-only,
        # then appends ExtraMounts without deduplicating destination paths.
        config = yaml.safe_load((EX / 'configuration/identity/rke2-oidc.yaml').read_text())
        flags = dict(a.split('=', 1) for a in config['kube-apiserver-arg+'])
        ca = '/etc/rancher/rke2/identity/ca.crt'
        self.assertEqual(flags['oidc-ca-file'], ca)
        extras = config['kube-apiserver-extra-mount+']
        self.assertEqual(extras, ['/etc/hosts:/etc/hosts:ro'])

        def modeled_targets(explicit):
            # Precondition: the reviewed CA file exists on the control node.
            targets = [ca] + [mount.split(':')[1] for mount in explicit]
            if len(targets) != len(set(targets)):
                raise ValueError('duplicate API-server mount destination')
            return targets

        self.assertEqual(modeled_targets(extras), [ca, '/etc/hosts'])
        with self.assertRaisesRegex(ValueError, 'duplicate'):
            modeled_targets([ca + ':' + ca + ':ro'] + extras)

    def test_only_exact_platform_admin_group_gets_builtin_cluster_admin(self):
        bindings = [o for o in self.access if o['kind'] == 'ClusterRoleBinding']
        self.assertEqual(len(bindings), 1)
        self.assertEqual(bindings[0]['roleRef'], {
            'apiGroup': 'rbac.authorization.k8s.io', 'kind': 'ClusterRole', 'name': 'cluster-admin'})
        self.assertEqual(bindings[0]['subjects'], [{
            'kind': 'Group', 'name': 'oidc:/platform/admins', 'apiGroup': 'rbac.authorization.k8s.io'}])
        self.assertEqual({o['metadata']['name'] for o in self.access if o['kind'] == 'ClusterRole'},
                         {'local-identity-observer'})
        self.assertEqual([o['metadata']['name'] for o in self.access if o['kind'] == 'RoleBinding'],
                         ['identity-developer-observer'])
        self.assertTrue(self.permitted('oidc:/platform/admins', '', 'nodes', 'list'))
        self.assertTrue(self.permitted('oidc:/platform/admins', '', 'pods', 'list'))
        for namespace in ['', 'headlamp', 'keycloak', 'kube-system', 'tenant-home']:
            self.assertTrue(self.permitted('oidc:/platform/admins', namespace, 'secrets', 'get'))
            self.assertTrue(self.permitted('oidc:/platform/admins', namespace, 'deployments', 'patch', 'apps'))
            self.assertTrue(self.permitted('oidc:/platform/admins', namespace, 'rolebindings', 'create', 'rbac.authorization.k8s.io'))
        self.assertTrue(self.permitted('oidc:/platform/admins', '', 'users', 'impersonate'))

    def test_developer_tenant_and_ungranted_boundaries_do_not_inherit_admin(self):
        self.assertTrue(self.permitted('oidc:/platform/developers', 'headlamp', 'pods', 'list'))
        for group in ['oidc:/platform/developers', 'oidc:/platform', 'oidc:/platform/admins-extra',
                      '/platform/admins', 'oidc:/tenants/home/admins', 'no-grants']:
            self.assertFalse(self.permitted(group, '', 'pods', 'list'))
            self.assertFalse(self.permitted(group, '', 'users', 'impersonate'))
            for ns in ['headlamp', 'keycloak', 'kube-system']:
                for resource in ['secrets', 'configmaps', 'pods/exec', 'pods/log', 'pods/portforward', 'serviceaccounts/token']:
                    for verb in ['get', 'list', 'create', 'patch']:
                        self.assertFalse(self.permitted(group, ns, resource, verb))
                self.assertFalse(self.permitted(group, ns, 'deployments', 'patch', 'apps'))
                self.assertFalse(self.permitted(group, ns, 'rolebindings', 'create', 'rbac.authorization.k8s.io'))
        self.assertFalse(self.permitted('oidc:/platform/developers', 'keycloak', 'pods', 'list'))
        self.assertFalse(self.permitted('oidc:/platform/developers', '', 'namespaces', 'list'))
        self.assertFalse(any(o['kind'].endswith('RoleBinding') for o in self.children['headlamp'] + self.children['keycloak']))
        for o in self.foundation:
            if o['kind'] == 'Role':
                for rule in o['rules']:
                    self.assertFalse(set(rule['resources']) & {'roles', 'rolebindings', 'namespaces', 'persistentvolumes'})
                    self.assertNotIn('*', rule['resources'] + rule['verbs'])

    def test_live_matrix_matches_full_admin_and_restricted_user_contracts(self):
        checks = yaml.safe_load((EX / 'configuration/identity/auth-checks.yaml').read_text())
        self.assertTrue(any(c['token'] == 'admin' and c['path'] == '/api/v1/pods' for c in checks['identity_checks']))
        for check in checks['identity_checks']:
            if check['token'] == 'admin':
                self.assertEqual(check['status'], 200)
        groups = {'admin': 'oidc:/platform/admins', 'developer': 'oidc:/platform/developers', 'no-grants': 'no-grants'}
        for check in checks['identity_access_checks']:
            resource = check['resource'] + ('/' + check['subresource'] if 'subresource' in check else '')
            self.assertEqual(self.permitted(groups[check['token']], check['namespace'], resource,
                                            check['verb'], check['group']), check['allowed'])
