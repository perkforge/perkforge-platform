"""Offline guards for platform-owned, inactive household portal controls."""
from pathlib import Path
import unittest
import yaml
ROOT = Path(__file__).resolve().parents[2]
from portal_fleet_fixture import provisioned, render

class PortalBoundaryTests(unittest.TestCase):
    def test_portal_enrollment_prepares_controls_without_starting_workload(self):
        objects = render()
        self.assertIs(next(o for o in objects if o['kind']=='GitRepo')['spec']['paused'], True)
        self.assertFalse(any(o['kind']=='Deployment' for o in objects))

    def test_deployer_has_no_security_or_cluster_mutation(self):
        objects = render(provisioned())
        self.assertFalse(any(o['kind'] in ('ClusterRole', 'ClusterRoleBinding') for o in objects))
        for obj in objects:
            if obj['kind'] == 'ServiceAccount':
                self.assertIs(obj['automountServiceAccountToken'], False)
            if obj['kind'] == 'Role':
                for rule in obj['rules']:
                    self.assertFalse(set(rule['resources']) & {'roles', 'rolebindings', 'namespaces', 'networkpolicies', 'resourcequotas', '*'})
                    self.assertNotIn('*', rule['verbs'])
            if obj['kind'] == 'RoleBinding':
                self.assertEqual(obj['subjects'][0]['name'], 'home-portal-deployer')

    def test_network_defaults_deny_with_dns_and_exact_portal_https(self):
        objects = [o for o in render(provisioned()) if o['kind']=='NetworkPolicy']
        deny = next(o for o in objects if o['metadata']['name']=='default-deny')
        dns = next(o for o in objects if o['metadata']['name']=='allow-dns')
        self.assertEqual(set(deny['spec']['policyTypes']), {'Ingress', 'Egress'})
        self.assertNotIn('ingress', deny['spec'])
        self.assertNotIn('egress', deny['spec'])
        portal = next(o for o in objects if o['metadata']['name']=='portal-https')['spec']
        self.assertEqual(portal['podSelector']['matchLabels'], {'app.kubernetes.io/name': 'perkforge-portal'})
        self.assertEqual(portal['egress'][0]['ports'], [{'protocol':'TCP','port':8443}])
        self.assertEqual(portal['ingress'][0]['ports'], [{'protocol':'TCP','port':3000}])
        peer = {'namespaceSelector': {'matchLabels': {'kubernetes.io/metadata.name':'kube-system'}},
                'podSelector': {'matchLabels': {'app.kubernetes.io/name':'rke2-traefik'}}}
        self.assertEqual(portal['egress'][0]['to'], [peer])
        self.assertEqual(portal['ingress'][0]['from'], [peer])
        rules = dns['spec']['egress']
        self.assertEqual(len(rules), 1)
        self.assertEqual({p['port'] for p in rules[0]['ports']}, {53})
        self.assertEqual(set(rules[0]['to'][0]), {'namespaceSelector', 'podSelector'})

    def test_fleet_registration_targets_only_tenant_repo_and_is_paused(self):
        objects = render(provisioned())
        repo = next(o for o in objects if o['kind'] == 'GitRepo')['spec']
        self.assertEqual(repo['repo'], 'https://github.com/perkforge/perkforge-tenant-portal.git')
        self.assertIs(repo['paused'], True)
        self.assertEqual(repo['paths'], ['bundles/portal'])
        self.assertEqual(repo['serviceAccount'], 'home-portal-deployer')
        policy = next(o for o in objects if o['kind'] == 'Policy')
        self.assertNotIn('allowNamespaceCreation', policy)
        self.assertIs(policy['requireServiceAccount'], True)
        self.assertEqual(policy['allowedServiceAccounts'], ['home-portal-deployer'])
