"""Prove the same native Fleet base works beyond Home and supports reviewed opt-outs."""
import copy
from pathlib import Path
import re
import unittest
import yaml
from portal_fleet_fixture import BUNDLE, provisioned, render, run_fleet
from test_portal_fleet import review_budget, review_transition


class SharedFoundationTests(unittest.TestCase):
    def setUp(self):
        self.tenant = yaml.safe_load((Path(__file__).parent / 'fixtures/tenant-demo.yaml').read_text())

    def test_generic_templates_have_no_application_knowledge(self):
        for path in (BUNDLE / 'templates').glob('*.yaml'):
            self.assertNotRegex(path.read_text().lower(), r'portal|oidc|imagerepository|tenant-reader', str(path))
        self.assertEqual(yaml.safe_load((BUNDLE / 'values.yaml').read_text())['applications'], {})

    def test_second_tenant_uses_same_base_without_portal_settings(self):
        review_budget(self.tenant)
        objects = render(self.tenant)
        self.assertEqual(len(objects), 14)
        self.assertNotIn('portal', yaml.safe_dump(objects))
        self.assertFalse(any(o['kind'].startswith('ValidatingAdmission') for o in objects))
        self.assertEqual(next(o for o in objects if o['kind'] == 'Project')['metadata']['name'], 'p-tenant-demo-local')
        namespace = next(o for o in objects if o['kind'] == 'Namespace')
        self.assertEqual(namespace['metadata']['annotations']['field.cattle.io/projectId'], 'local:p-tenant-demo-local')
        accounts = {(o['metadata']['namespace'], o['metadata']['name']) for o in objects if o['kind'] == 'ServiceAccount'}
        self.assertEqual(accounts, {('tenant-demo-web', 'demo-runtime'), ('cattle-fleet-local-system', 'demo-deployer')})
        mapping = next(o for o in objects if o['kind'] == 'BundleNamespaceMapping')
        self.assertEqual(mapping['bundleSelector'], {})
        self.assertEqual(mapping['metadata']['namespace'], 'fleet-tenant-demo')
        policy = next(o for o in objects if o['kind'] == 'Policy')
        allowed = policy['gitRepo']['allowedRepoPatterns'][0]
        self.assertIsNotNone(re.fullmatch(allowed, 'https://example.invalid/tenant-demo.git'))
        self.assertIsNone(re.fullmatch(allowed, 'https://example.invalid/tenant-demo.git/other'))
        self.assertEqual(policy['allowedServiceAccounts'], ['demo-deployer'])

    def test_each_component_can_be_omitted_by_platform_values(self):
        component_kinds = {'project': {'Project'}, 'namespaces': {'Namespace'}, 'quotas': {'ResourceQuota'},
            'limits': {'LimitRange'}, 'networkPolicies': {'NetworkPolicy'}, 'serviceAccounts': {'ServiceAccount'},
            'deploymentRbac': {'Role', 'RoleBinding'}, 'fleetAccess': {'FleetWorkspace', 'Policy', 'BundleNamespaceMapping'},
            'registration': {'GitRepo'}}
        full = render(self.tenant)
        identity = lambda o: (o['kind'], o['metadata'].get('namespace'), o['metadata']['name'])
        for component, kinds in component_kinds.items():
            with self.subTest(component=component):
                tenant = copy.deepcopy(self.tenant)
                tenant['foundation']['components'] = {component: False}
                self.assertNotEqual(run_fleet(tenant).returncode, 0, 'Opt-outs require a platform review reason')
                tenant['foundation']['optOutReasons'] = {component: 'Fixture: existing reviewed platform owner supplies this component'}
                actual = render(tenant)
                self.assertEqual({identity(o) for o in actual}, {identity(o) for o in full if o['kind'] not in kinds})

    def test_bad_component_or_cluster_is_rejected(self):
        for switches in ({'quotas': 'false'}, {'unknown': False}):
            tenant = copy.deepcopy(self.tenant)
            tenant['foundation']['components'] = switches
            self.assertNotEqual(run_fleet(tenant).returncode, 0)
        tenant = copy.deepcopy(self.tenant)
        tenant['cluster'] = 'missing'
        self.assertNotEqual(run_fleet(tenant).returncode, 0)

    def test_opt_out_does_not_silently_remove_previously_managed_resources(self):
        before = provisioned()
        after = copy.deepcopy(before)
        after['foundation']['components']['quotas'] = False
        after['foundation']['optOutReasons']['quotas'] = 'Reviewed elsewhere'
        with self.assertRaisesRegex(ValueError, 'separate review'):
            review_transition(before, after)
        after = copy.deepcopy(before)
        after['foundation']['namespaces'] = {}
        with self.assertRaisesRegex(ValueError, 'separate review'):
            review_transition(before, after)
