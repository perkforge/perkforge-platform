"""Public store/role contracts and opt-in native, memory-only OpenBao ACL tests.
No Kubernetes API or real credentials are used by this test module.
"""
import importlib.util
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import unittest
import yaml

ROOT = Path(__file__).resolve().parents[2]
ESO = ROOT / 'configuration/external-secrets'


def policy_rules(name):
    text = (ESO / 'openbao/policies' / (name + '.hcl')).read_text()
    matches = re.findall(r'path "([^"]+)"\s*\{\s*capabilities\s*=\s*\[([^]]+)\]\s*\}', text)
    return {path: re.findall(r'"([^"]+)"', capabilities) for path, capabilities in matches}


def role(name):
    return json.loads((ESO / 'openbao/roles' / (name + '.json')).read_text())


class StoreContracts(unittest.TestCase):
    def test_public_fixture_pin_and_native_evidence_stay_aligned(self):
        native = yaml.safe_load((ESO / 'source-pin.yaml').read_text())
        fixture = yaml.safe_load((ROOT / 'tests/fixtures/source-pins.yaml').read_text())['external-secrets']
        self.assertEqual(fixture, {'url': native['source_url'], 'sha256': native['source_sha256'], 'chart': 'chart'})

    def test_platform_cluster_store_is_namespace_restricted_and_not_tenant_access(self):
        store = yaml.safe_load((ESO / 'stores/platform/store.yaml').read_text())
        self.assertEqual(store['apiVersion'], 'external-secrets.io/v1')
        self.assertEqual(store['kind'], 'ClusterSecretStore')
        self.assertEqual(store['metadata']['name'], 'openbao-platform')
        self.assertNotIn('namespace', store['metadata'])
        self.assertEqual(store['spec']['conditions'], [{'namespaces': ['external-secrets']}])
        self.assertEqual(store['spec']['controller'], 'perkforge')
        vault = store['spec']['provider']['vault']
        self.assertEqual(vault['server'], 'https://openbao.perkforge.home.arpa')
        self.assertEqual(vault['path'], 'platform')
        self.assertEqual(vault['version'], 'v2')
        self.assertEqual(vault['caProvider'], {'type': 'ConfigMap', 'name': 'openbao-ca',
                         'namespace': 'external-secrets', 'key': 'ca.crt'})
        self.assertEqual(vault['auth'], {'kubernetes': {'mountPath': 'kubernetes-eso',
            'role': 'eso-platform', 'serviceAccountRef': {'name': 'eso-platform',
                'namespace': 'external-secrets', 'audiences': ['openbao-eso']}}})

    def test_platform_identity_has_no_kubernetes_grants_or_mounted_token(self):
        objects = list(yaml.safe_load_all(subprocess.check_output(['kubectl', 'kustomize',
            str(ESO / 'stores/platform')], text=True, env={**os.environ, 'KUBECONFIG': '/dev/null'})))
        self.assertEqual({o['kind'] for o in objects}, {'ServiceAccount', 'ClusterSecretStore'})
        identity = next(o for o in objects if o['kind'] == 'ServiceAccount')
        self.assertEqual(identity['metadata'], {'name': 'eso-platform', 'namespace': 'external-secrets'})
        self.assertFalse(identity['automountServiceAccountToken'])

    def test_short_lived_exact_auth_bindings_do_not_reuse_human_or_legacy_roles(self):
        for name, namespace in [('eso-platform', 'external-secrets'), ('eso-tenant-portal', 'tenant-portal')]:
            with self.subTest(name=name):
                value = role(name)
                self.assertEqual(value['bound_service_account_names'], [name])
                self.assertEqual(value['bound_service_account_namespaces'], [namespace])
                self.assertEqual(value['audience'], 'openbao-eso')
                self.assertEqual(value['token_policies'], [name])
                self.assertTrue(value['token_no_default_policy'])
                self.assertEqual(value['token_ttl'], 300)
                self.assertEqual(value['token_max_ttl'], 900)
                self.assertEqual(value['token_explicit_max_ttl'], 900)
                self.assertFalse(value.get('bound_service_account_namespace_selector'))
                self.assertFalse(value.get('token_period'))
        config = json.loads((ESO / 'openbao/kubernetes-auth.json').read_text())
        self.assertEqual(config, {'kubernetes_host': 'https://kubernetes.default.svc:443',
                                 'disable_local_ca_jwt': False})

    def test_platform_has_no_implicit_data_grant_and_tenant_has_only_three_exact_reads(self):
        self.assertEqual(policy_rules('eso-platform'), {'auth/token/lookup-self': ['read']})
        expected = {'tenants/data/tenant-portal/' + p: ['read']
                    for p in ['oidc', 'registry/ghcr', 'tls']}
        expected['auth/token/lookup-self'] = ['read']
        self.assertEqual(policy_rules('eso-tenant-portal'), expected)
        for name in ['eso-platform', 'eso-tenant-portal']:
            for path in policy_rules(name):
                self.assertNotIn('*', path)
                self.assertNotIn('+', path)
                self.assertNotIn('/metadata', path)
                self.assertNotIn('home/tenant-home-portal', path)

    def test_reviewer_is_separate_exact_tokenreview_only_authority(self):
        objects = list(yaml.safe_load_all((ESO / 'openbao/reviewer.yaml').read_text()))
        self.assertEqual([o['kind'] for o in objects], ['ClusterRole', 'ClusterRoleBinding'])
        self.assertEqual(objects[0]['rules'], [{'apiGroups': ['authentication.k8s.io'],
            'resources': ['tokenreviews'], 'verbs': ['create']}])
        self.assertEqual(objects[1]['subjects'], [{'kind': 'ServiceAccount',
            'name': 'openbao', 'namespace': 'openbao'}])
        self.assertEqual(objects[1]['roleRef']['name'], objects[0]['metadata']['name'])

    def test_store_stage_contains_no_secrets_consumers_or_implicit_active_selection(self):
        for path in (ESO / 'stores').rglob('*.yaml'):
            for obj in yaml.safe_load_all(path.read_text()):
                if obj and obj.get('kind') != 'Kustomization':
                    self.assertNotIn(obj.get('kind'), ['Secret', 'ExternalSecret', 'ClusterExternalSecret', 'PushSecret'])
        for path in (ROOT / 'clusters').rglob('kustomization.yaml'):
            self.assertNotIn('stores/platform', path.read_text())


@unittest.skipUnless(os.environ.get('ESO_CRD_BUNDLE'), 'provide the exact pinned native CRD bundle')
class PinnedStoreSchema(unittest.TestCase):
    def test_platform_store_uses_actual_served_v1_schema(self):
        from jsonschema import Draft7Validator
        bundle = Path(os.environ['ESO_CRD_BUNDLE'])
        pin = yaml.safe_load((ESO / 'source-pin.yaml').read_text())
        self.assertEqual(hashlib.sha256(bundle.read_bytes()).hexdigest(), pin['crd_bundle_sha256'])
        crd = next(d for d in yaml.safe_load_all(bundle.read_text())
                   if d and d['metadata']['name'] == 'clustersecretstores.external-secrets.io')
        version = next(v for v in crd['spec']['versions'] if v['name'] == 'v1')
        self.assertTrue(version['served'])
        store = yaml.safe_load((ESO / 'stores/platform/store.yaml').read_text())
        Draft7Validator(version['schema']['openAPIV3Schema']).validate(store)
        # JSONSchema does not execute Kubernetes CEL; exact contract tests above
        # independently constrain the object. Live admission remains separate.


@unittest.skipUnless(os.environ.get('RUN_OPENBAO_POLICY_TESTS') == '1',
                     'opt in to the pinned memory-only OpenBao fixture')
class NativeESOReadPolicies(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = ROOT / 'tests/integration/test_sso_openbao_self_session.py'
        spec = importlib.util.spec_from_file_location('eso_native_acl_fixture', path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        cls.engine = module.PinnedEngine
        cls.engine.setUpClass()
        cls.addClassCleanup(cls.engine.doClassCleanups)
        for name in ['eso-platform', 'eso-tenant-portal']:
            result = cls.engine.call('PUT', '/sys/policies/acl/' + name,
                {'policy': (ESO / 'openbao/policies' / (name + '.hcl')).read_text()})
            assert result.status_code == 204
        assert cls.engine.call('POST', '/sys/auth/kubernetes-eso', {'type': 'kubernetes'}).status_code == 204
        for path in ['tenants/data/tenant-portal/oidc', 'tenants/data/tenant-portal/registry/ghcr',
                     'tenants/data/tenant-portal/tls', 'tenants/data/sibling/oidc',
                     'tenants/data/home/tenant-home-portal/registry/ghcr',
                     'platform/data/bootstrap/local/registry']:
            assert cls.engine.call('POST', '/' + path, {'data': {'fixture': 'not-a-real-secret'}}).status_code == 200

    def token(self, policy):
        result = self.engine.call('POST', '/auth/token/create', {'policies': [policy],
            'no_default_policy': True, 'ttl': '5m', 'explicit_max_ttl': '15m', 'renewable': False})
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.json()['auth']['policies'], [policy])
        return result.json()['auth']['client_token']

    def test_exact_roles_accepted_by_pinned_kubernetes_auth_api(self):
        for name in ['eso-platform', 'eso-tenant-portal']:
            desired = role(name)
            result = self.engine.call('POST', '/auth/kubernetes-eso/role/' + name, desired)
            self.assertEqual(result.status_code, 204, result.text)
            readback = self.engine.call('GET', '/auth/kubernetes-eso/role/' + name)
            self.assertEqual(readback.status_code, 200)
            actual = readback.json()['data']
            for key, value in desired.items():
                self.assertEqual(actual[key], value, key)
            self.assertFalse(actual.get('bound_service_account_namespace_selector'))
            self.assertFalse(actual.get('token_period'))

    def test_platform_lookup_only_never_reads_recovery_or_tenant_values(self):
        token = self.token('eso-platform')
        self.assertEqual(self.engine.call('GET', '/auth/token/lookup-self', token=token).status_code, 200)
        for path in ['/platform/data/bootstrap/local/registry', '/tenants/data/tenant-portal/oidc',
                     '/platform/metadata', '/tenants/metadata', '/sys/policies/acl/eso-platform']:
            with self.subTest(path=path):
                self.assertEqual(self.engine.call('GET', path, token=token).status_code, 403)

    def test_tenant_reads_only_approved_records_and_denies_write_and_escape(self):
        token = self.token('eso-tenant-portal')
        for path in ['/auth/token/lookup-self', '/tenants/data/tenant-portal/oidc',
                     '/tenants/data/tenant-portal/registry/ghcr', '/tenants/data/tenant-portal/tls']:
            self.assertEqual(self.engine.call('GET', path, token=token).status_code, 200)
        for method, path, body in [
            ('GET', '/tenants/data/sibling/oidc', None),
            ('GET', '/tenants/data/home/tenant-home-portal/registry/ghcr', None),
            ('GET', '/platform/data/bootstrap/local/registry', None),
            ('GET', '/tenants/metadata/tenant-portal/oidc', None),
            ('LIST', '/tenants/metadata/tenant-portal', None),
            ('POST', '/tenants/data/tenant-portal/oidc', {'data': {'fixture': 'forbidden'}}),
            ('DELETE', '/tenants/data/tenant-portal/oidc', None),
            ('POST', '/tenants/destroy/tenant-portal/oidc', {'versions': [1]}),
            ('PUT', '/sys/policies/acl/escape', {'policy': 'path "*" { capabilities=["sudo"] }'}),
            ('POST', '/auth/token/create', {}),
            ('POST', '/auth/kubernetes-eso/role/escape', {})]:
            with self.subTest(method=method, path=path):
                self.assertEqual(self.engine.call(method, path, body, token=token).status_code, 403)
