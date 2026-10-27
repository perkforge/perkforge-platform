"""Offline contract checks against actual native Fleet output; no Python generator."""
import copy
import unittest
import yaml
from portal_fleet_fixture import BUNDLE, ROOT, home_values, portal_values, provisioned, render, run_fleet


class PortalIdentityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.home = provisioned()
        cls.contract = portal_values(cls.home)
        cls.objects = render(cls.home)

    def test_default_stays_empty_and_unregistered_with_published_image(self):
        self.assertEqual(render(), [])
        self.assertEqual(portal_values()['imageDigest'], 'sha256:2e07afbb31fd462911a365893d05796090883464560478bd70179466af5b17b7')
        for path in (ROOT / 'local-lab/fleet').rglob('*.yaml'):
            self.assertNotIn('home-portal', path.read_text())
            self.assertNotIn('local-lab/tenant-config', path.read_text())
        self.assertFalse(list(BUNDLE.rglob('Chart.yaml')))
        self.assertFalse(list(BUNDLE.rglob('*.py')))

    def test_paused_fleet_and_immutable_identity_values(self):
        repo = next(o for o in self.objects if o['kind'] == 'GitRepo')['spec']
        self.assertIs(repo['paused'], True)
        self.assertEqual(repo['revision'], self.home['foundation']['repositories']['portal']['revision'])
        self.assertEqual(set(repo['targets'][0]), {'name', 'clusterName'})
        self.assertFalse(any(o['kind'] in ('ConfigMap', 'Secret', 'Deployment', 'Job') for o in self.objects))

    def test_runtime_guards_reject_bad_scope_identity_and_unapproved_activation(self):
        changes = [('namespace', 'tenant-home-nextcloud'),
                   ('imageDigest', None), ('imageDigest', 'latest'), ('secret', 'never-allowed')]
        for key, value in changes:
            home = copy.deepcopy(self.home)
            home['applications']['portal'][key] = value
            with self.subTest(key=key, value=value):
                self.assertNotEqual(run_fleet(home).returncode, 0)
        for key, value in [('issuer', 'http://issuer.invalid/realms/perkforge'),
                           ('clientId', 'bad/client'), ('clientSecret', 'forbidden'),
                           ('groups', ['/admins']), ('secretKey', 'admin-password')]:
            home = copy.deepcopy(self.home)
            home['applications']['portal']['identity'][key] = value
            with self.subTest(key=key):
                self.assertNotEqual(run_fleet(home).returncode, 0)

    def test_rbac_workloads_and_write_only_release_storage(self):
        role = next(o for o in self.objects if o['kind'] == 'Role')
        self.assertEqual({r for rule in role['rules'] for r in rule['resources']}, {'deployments', 'services', 'secrets'})
        self.assertEqual(next(rule['verbs'] for rule in role['rules'] if rule['resources'] == ['secrets']), ['create', 'update', 'delete'])
        self.assertFalse(any(o['kind'] in ('ClusterRole', 'ClusterRoleBinding') for o in self.objects))
        for obj in self.objects:
            if obj['kind'] == 'ServiceAccount':
                self.assertIs(obj['automountServiceAccountToken'], False)

    def test_admission_targets_namespace_and_all_policies_deny_on_failure(self):
        policies = [o for o in self.objects if o['kind'] == 'ValidatingAdmissionPolicy']
        self.assertEqual(len(policies), 4)
        for policy in policies:
            self.assertEqual(policy['spec']['failurePolicy'], 'Fail')
            if policy['metadata']['name'] != 'portal-deployer-surface':
                self.assertEqual(policy['spec']['matchConditions'][0]['expression'], 'request.namespace == "tenant-home-portal"')
            self.assertNotIn('objectSelector', policy['spec']['matchConstraints'])
        bindings = [o for o in self.objects if o['kind'] == 'ValidatingAdmissionPolicyBinding']
        self.assertEqual({b['spec']['policyName'] for b in bindings}, {p['metadata']['name'] for p in policies})
        self.assertTrue(all(b['spec']['validationActions'] == ['Deny'] for b in bindings))

    def test_native_values_override_and_data_files_excluded(self):
        shared = yaml.safe_load((BUNDLE / 'values.yaml').read_text())
        shared['foundation']['workspace'] = 'wrong-default'
        result = run_fleet(self.home, shared, extra_files={
            'tenants/not-a-resource.yaml': 'this is intentionally not a Kubernetes object',
            'enrollments/never-apply.yaml': 'kind: Secret\nmetadata: {name: never-apply}\n',
            'generated/never-apply.yaml': 'kind: Secret\nmetadata: {name: never-apply}\n'})
        self.assertEqual(result.returncode, 0, result.stderr)
        objects = list(yaml.safe_load_all(result.stdout))
        workspace = next(o for o in objects if o['kind'] == 'FleetWorkspace')
        self.assertEqual(workspace['metadata']['name'], self.home['foundation']['workspace'])
        self.assertNotIn('never-apply', result.stdout)
        self.assertNotIn('TenantCatalog', result.stdout)
        self.assertEqual(len(objects), 21)
