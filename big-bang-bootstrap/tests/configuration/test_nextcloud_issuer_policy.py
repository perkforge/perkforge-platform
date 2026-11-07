"""Exact LOCAL policy selection; offline builds only, no Kubernetes API."""
import copy
from pathlib import Path
import subprocess
import tempfile
import unittest

import yaml

ROOT = Path(__file__).resolve().parents[2]
EXPECTED_SPEC = {
    'podSelector': {'matchLabels': {
        'app.kubernetes.io/name': 'nextcloud',
        'app.kubernetes.io/instance': 'nextcloud',
        'app.kubernetes.io/component': 'app',
    }},
    'policyTypes': ['Egress'],
    'egress': [{'to': [{'ipBlock': {'cidr': '192.168.1.102/32'}}],
                'ports': [{'protocol': 'TCP', 'port': 443}]}],
}


def build(path):
    return list(yaml.safe_load_all(subprocess.check_output(
        ['kubectl', 'kustomize', str(path)], text=True)))


class LocalIssuerSelection(unittest.TestCase):
    def assert_exact_policy(self, policy):
        self.assertEqual(policy['apiVersion'], 'networking.k8s.io/v1')
        self.assertEqual(policy['kind'], 'NetworkPolicy')
        self.assertEqual(policy['metadata']['name'], 'nextcloud-oidc-issuer')
        self.assertEqual(policy['metadata']['namespace'], 'tenant-home-nextcloud')
        self.assertEqual(policy['spec'], EXPECTED_SPEC)

    def test_unique_exact_local_policy_without_inputs_or_authority(self):
        objects = build(ROOT / 'clusters/local-nextcloud')
        policies = [o for o in objects if o['metadata']['name'] == 'nextcloud-oidc-issuer']
        self.assertEqual(len(policies), 1)
        self.assert_exact_policy(policies[0])
        self.assertEqual(policies[0]['metadata']['annotations'], {
            'kustomize.toolkit.fluxcd.io/prune': 'disabled',
            'kustomize.toolkit.fluxcd.io/force': 'disabled',
            'platform.perkforge.io/cluster': 'local',
            'platform.perkforge.io/environment': 'local',
            'platform.perkforge.io/profile': 'il2',
        })
        source = yaml.safe_load((ROOT / 'configuration/identity/nextcloud/local/network.yaml').read_text())
        self.assert_exact_policy(source)

    def test_baselines_and_explicit_opt_out_exclude_issuer(self):
        for path in ['clusters/local', 'clusters/local-gitlab-runner',
                     'enrollments/local', 'enrollments/local-nextcloud']:
            with self.subTest(path=path):
                self.assertFalse(any(o['metadata']['name'] == 'nextcloud-oidc-issuer'
                                     for o in build(ROOT / path)))
        with tempfile.TemporaryDirectory() as directory:
            Path(directory, 'kustomization.yaml').write_text(
                'apiVersion: kustomize.config.k8s.io/v1beta1\nkind: Kustomization\nresources: []\n')
            self.assertEqual(build(directory), [])

    def test_access_is_exact_and_never_selected(self):
        path = ROOT / 'configuration/identity/nextcloud/local'
        role, binding = list(yaml.safe_load_all((path / 'access.yaml').read_text()))
        self.assertEqual(role['rules'], [{
            'apiGroups': ['networking.k8s.io'], 'resources': ['networkpolicies'],
            'resourceNames': ['nextcloud-oidc-issuer'], 'verbs': ['get', 'patch', 'update'],
        }])
        self.assertEqual(binding['subjects'], [{'kind': 'ServiceAccount',
            'name': 'platform-reconciler', 'namespace': 'flux-system'}])
        self.assertEqual(binding['roleRef'], {'apiGroup': 'rbac.authorization.k8s.io',
            'kind': 'Role', 'name': 'nextcloud-issuer-writer'})
        for obj in (role, binding):
            self.assertEqual(obj['metadata'], {'name': 'nextcloud-issuer-writer',
                'namespace': 'tenant-home-nextcloud'})
        selected_roots = []
        for root in sorted((ROOT / 'clusters').iterdir()):
            if not (root / 'kustomization.yaml').exists():
                continue
            objects = build(root)
            self.assertFalse(any(o['metadata']['name'] == 'nextcloud-issuer-writer' for o in objects))
            policies = [o for o in objects if o['metadata']['name'] == 'nextcloud-oidc-issuer']
            if policies:
                selected_roots.append(root.name)
                self.assertEqual(len(policies), 1)
                self.assert_exact_policy(policies[0])
        self.assertEqual(selected_roots, [
            'local-logging-backend', 'local-logging-limited-pilot', 'local-logging-pilot',
            'local-metrics-crds', 'local-metrics-limited-pilot', 'local-metrics-limited-pilot-ui',
            'local-metrics-pilot', 'local-metrics-review', 'local-nextcloud'])
        self.assertEqual([o['kind'] for o in build(path)], ['NetworkPolicy'])
        seed = (ROOT / 'configuration/ansible/seed.yaml.j2').read_text()
        self.assertIn('serviceAccountName: platform-reconciler', seed)
        self.assertIn('prune: false', seed)
        self.assertEqual(yaml.safe_load((path / 'kustomization.yaml').read_text())['resources'], ['network.yaml'])

    def test_contract_rejects_widening_or_identity_drift(self):
        original = yaml.safe_load((ROOT / 'configuration/identity/nextcloud/local/network.yaml').read_text())
        mutations = [
            lambda p: p['metadata'].update(namespace='default'),
            lambda p: p['metadata'].update(name='another-policy'),
            lambda p: p['spec'].update(podSelector={}),
            lambda p: p['spec']['podSelector']['matchLabels'].pop('app.kubernetes.io/component'),
            lambda p: p['spec']['egress'][0]['to'][0]['ipBlock'].update(cidr='192.168.1.0/24'),
            lambda p: p['spec']['egress'][0]['ports'][0].update(port=8443),
            lambda p: p['spec']['egress'][0]['ports'][0].update(protocol='UDP'),
            lambda p: p['spec']['egress'].append({}),
            lambda p: p['spec']['egress'][0]['to'].append({'ipBlock': {'cidr': '0.0.0.0/0'}}),
            lambda p: p['spec'].update(ingress=[{}]),
        ]
        for index, mutate in enumerate(mutations):
            with self.subTest(case=index):
                policy = copy.deepcopy(original)
                mutate(policy)
                with self.assertRaises(AssertionError):
                    self.assert_exact_policy(policy)


if __name__ == '__main__':
    unittest.main()
