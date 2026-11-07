"""Exact LOCAL policy selection; offline builds only, no Kubernetes API."""
import copy
import json
import os
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

    def test_runtime_access_is_exact_and_not_selected(self):
        path = ROOT / 'configuration/identity/nextcloud/local'
        role, binding = list(yaml.safe_load_all((path / 'runtime-policy-access.yaml').read_text()))
        self.assertEqual(role, {
            'apiVersion': 'rbac.authorization.k8s.io/v1', 'kind': 'ClusterRole',
            'metadata': {'name': 'nextcloud-runtime-policy-writer'},
            'rules': [{'apiGroups': ['admissionregistration.k8s.io'],
                       'resources': ['validatingadmissionpolicies'],
                       'resourceNames': ['nextcloud-app-pod-templates'],
                       'verbs': ['get', 'patch', 'update']}]})
        self.assertEqual(binding, {
            'apiVersion': 'rbac.authorization.k8s.io/v1', 'kind': 'ClusterRoleBinding',
            'metadata': {'name': 'nextcloud-runtime-policy-writer'},
            'roleRef': {'apiGroup': 'rbac.authorization.k8s.io', 'kind': 'ClusterRole',
                        'name': 'nextcloud-runtime-policy-writer'},
            'subjects': [{'kind': 'ServiceAccount', 'name': 'platform-reconciler',
                          'namespace': 'flux-system'}]})
        for root in sorted((ROOT / 'clusters').iterdir()):
            if (root / 'kustomization.yaml').exists():
                self.assertFalse(any(o['metadata']['name'] == 'nextcloud-runtime-policy-writer'
                                     for o in build(root)))

    def test_explicit_accepted_selection_preserves_bootstrap_defaults(self):
        ansible = ROOT / 'configuration/ansible'
        selection = yaml.safe_load((ansible / 'vars/local-nextcloud-selection.yaml').read_text())
        self.assertEqual(selection, {
            'config_repository': 'https://github.com/perkforge/perkforge-platform.git',
            'config_tag': 'v0.26.0',
            'gitops_path': './big-bang-bootstrap/clusters/local-metrics-limited-pilot-ui',
            'deployment_environment': 'local', 'impact_profile': 'il2'})
        inventory = yaml.safe_load((ansible / 'inventory.yaml').read_text())
        defaults = inventory['all']['children']['bootstrap_clusters']['vars']
        self.assertEqual(defaults['config_tag'], 'UNCONFIGURED')
        self.assertFalse(defaults['bootstrap_apply'])
        self.assertEqual((ansible / 'seed.yaml.j2').read_text().count('suspend: true'), 2)
        objects = build(ROOT / selection['gitops_path'].split('big-bang-bootstrap/')[1])
        self.assertFalse(any(o['kind'] == 'GitRepository' and o['metadata']['name'] == 'cluster-config'
                             for o in objects))

    def test_accepted_selection_renders_paused_seed_offline(self):
        ansible = ROOT / 'configuration/ansible'
        with tempfile.TemporaryDirectory() as directory:
            args = json.dumps({'msg': "{{ lookup('ansible.builtin.template', '" +
                               str(ansible / 'seed.yaml.j2') + "') }}"})
            output = subprocess.check_output([
                'ansible', 'local', '-i', str(ansible / 'inventory.yaml'),
                '-m', 'ansible.builtin.debug', '-a', args,
                '-e', '@' + str(ansible / 'vars/local-nextcloud-selection.yaml')],
                text=True, env={**os.environ, 'KUBECONFIG': '/dev/null',
                                'ANSIBLE_LOCAL_TEMP': directory, 'ANSIBLE_NOCOLOR': '1'})
            response, _ = json.JSONDecoder().raw_decode(output[output.index('{'):])
            source, root = list(yaml.safe_load_all(response['msg']))
            self.assertEqual(source['spec']['ref'], {'tag': 'v0.26.0'})
            self.assertEqual(root['spec']['path'],
                             './big-bang-bootstrap/clusters/local-metrics-limited-pilot-ui')
            self.assertEqual(root['spec']['serviceAccountName'], 'platform-reconciler')
            self.assertFalse(root['spec']['prune'])
            self.assertTrue(source['spec']['suspend'])
            self.assertTrue(root['spec']['suspend'])

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
