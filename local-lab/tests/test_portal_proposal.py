"""Offline guards for the deliberately inactive household portal proposal."""
from pathlib import Path
import unittest
import yaml
ROOT = Path(__file__).resolve().parents[2]
PROPOSAL = ROOT / 'local-lab/templates/tenant-applications/portal'

class PortalProposalTests(unittest.TestCase):
    def test_not_in_active_fleet_or_catalog(self):
        for folder in ('local-lab/fleet',):
            for path in (ROOT / folder).rglob('*.yaml'):
                self.assertNotIn('home-portal', path.read_text(), str(path))
        self.assertFalse((PROPOSAL / 'fleet.yaml').exists())

    def test_deployer_has_no_security_or_cluster_mutation(self):
        objects = list(yaml.safe_load_all((PROPOSAL / 'rbac.yaml').read_text()))
        self.assertFalse(any(o['kind'] in ('ClusterRole', 'ClusterRoleBinding') for o in objects))
        for obj in objects:
            if obj['kind'] == 'ServiceAccount':
                self.assertIs(obj['automountServiceAccountToken'], False)
            if obj['kind'] == 'Role':
                for rule in obj['rules']:
                    self.assertFalse(set(rule['resources']) & {'secrets', 'roles', 'rolebindings', 'namespaces', 'networkpolicies', 'resourcequotas', '*'})
                    self.assertNotIn('*', rule['verbs'])
            if obj['kind'] == 'RoleBinding':
                self.assertEqual(obj['subjects'][0]['name'], 'home-portal-deployer')

    def test_network_defaults_deny_and_only_dns_allowed(self):
        objects = list(yaml.safe_load_all((PROPOSAL / 'networkpolicy.yaml').read_text()))
        deny, dns = objects
        self.assertEqual(set(deny['spec']['policyTypes']), {'Ingress', 'Egress'})
        self.assertNotIn('ingress', deny['spec'])
        self.assertNotIn('egress', deny['spec'])
        rules = dns['spec']['egress']
        self.assertEqual(len(rules), 1)
        self.assertEqual({p['port'] for p in rules[0]['ports']}, {53})
        self.assertEqual(set(rules[0]['to'][0]), {'namespaceSelector', 'podSelector'})

    def test_fleet_proposal_targets_only_tenant_repo_and_is_paused(self):
        objects = list(yaml.safe_load_all((ROOT / 'local-lab/tenant-config/generated/home/portal/resources.yaml').read_text()))
        repo = next(o for o in objects if o['kind'] == 'GitRepo')['spec']
        self.assertEqual(repo['repo'], 'https://github.com/perkforge/perkforge-tenant-portal.git')
        self.assertIs(repo['paused'], True)
        self.assertEqual(repo['paths'], ['bundles/portal'])
        self.assertEqual(repo['serviceAccount'], 'home-portal-deployer')
        policy = next(o for o in objects if o['kind'] == 'Policy')
        self.assertNotIn('allowNamespaceCreation', policy)
        self.assertIs(policy['requireServiceAccount'], True)
        self.assertEqual(policy['allowedServiceAccounts'], ['home-portal-deployer'])
