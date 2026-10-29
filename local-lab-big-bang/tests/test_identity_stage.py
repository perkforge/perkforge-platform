"""Pinned full renders and explicit authorization contracts; no live auth claims."""
from collections import Counter
from copy import deepcopy
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
import yaml
from render_helpers import build, helm, ordered_values, child_values, release_name
from resource_inventory import inventory
from lookup_server import lookup_server, secret_allowed

ROOT = Path(__file__).resolve().parents[1]
EX = ROOT / 'examples'
STAGE = EX / 'stages/local-identity'


class IdentityStageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = Path(os.environ['PREFLIGHT_SOURCES_DIR'])
        cls.root = build(STAGE)
        cls.parent = next(o for o in cls.root if o['kind'] == 'HelmRelease')
        raw = helm(cls.source / 'bigbang/chart', 'bigbang', 'bigbang', ordered_values(cls.root, cls.parent))
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)
            (p / 'objects.yaml').write_text(yaml.safe_dump_all(raw))
            (p / 'kustomization.yaml').write_text(yaml.safe_dump({
                'apiVersion': 'kustomize.config.k8s.io/v1beta1', 'kind': 'Kustomization',
                'resources': ['objects.yaml'], **cls.parent['spec']['postRenderers'][0]['kustomize']}))
            cls.outer = build(p)
        cls.children = {}
        for name in ['headlamp', 'keycloak']:
            hr = next(o for o in cls.outer if o['kind'] == 'HelmRelease' and o['metadata']['name'] == name)
            cls.children[name] = helm(cls.source / name / 'chart', release_name(hr), name, child_values(cls.outer, name))
        cls.foundation = build(STAGE / 'foundation')
        cls.routing = build(STAGE / 'routing')
        cls.access = build(STAGE / 'access')

    def test_only_selected_apps_and_no_generated_storage_or_permissions(self):
        self.assertEqual({o['metadata']['name'] for o in self.outer if o['kind'] == 'HelmRelease'}, {'headlamp', 'keycloak'})
        self.assertEqual(Counter(o['kind'] for o in self.children['keycloak']),
                         {'PodDisruptionBudget': 1, 'ServiceAccount': 2, 'Service': 4, 'StatefulSet': 2})
        objects = self.root + self.outer + self.children['headlamp'] + self.children['keycloak']
        for o in objects:
            self.assertNotIn(o['kind'], ['Namespace', 'Ingress', 'PersistentVolumeClaim', 'ClusterRole', 'ClusterRoleBinding', 'RoleBinding'])
        self.assertEqual({o['metadata']['name'] for o in self.root if o['kind'] == 'ConfigMap'},
                         {'values-shared', 'values-provider', 'values-impact', 'values-cluster', 'values-keycloak', 'values-identity'})
        for o in self.outer:
            if o['kind'] == 'HelmRelease':
                self.assertEqual(o['spec']['serviceAccountName'], o['metadata']['name'] + '-installer')
                self.assertEqual(o['spec']['storageNamespace'], 'bigbang')
                self.assertFalse(o['spec']['install']['createNamespace'])

    def test_database_stage_preserves_headlamp_and_installer_covers_render(self):
        root = build(EX / 'stages/local-keycloak')
        parent = next(o for o in root if o['kind'] == 'HelmRelease')
        outer = helm(self.source / 'bigbang/chart', 'bigbang', 'bigbang', ordered_values(root, parent))
        hr = next(o for o in outer if o['kind'] == 'HelmRelease' and o['metadata']['name'] == 'headlamp')
        private = helm(self.source / 'headlamp/chart', release_name(hr), 'headlamp', child_values(outer, 'headlamp'))
        original_root = build(EX / 'stages/local-headlamp')
        original_hr = next(o for o in original_root if o['kind'] == 'HelmRelease')
        original_outer = helm(self.source / 'bigbang/chart', 'bigbang', 'bigbang', ordered_values(original_root, original_hr))
        original = helm(self.source / 'headlamp/chart', release_name(hr), 'headlamp', child_values(original_outer, 'headlamp'))
        self.assertEqual(private, original)
        role = next(o for o in self.foundation if o['kind'] == 'Role' and o['metadata']['name'] == 'keycloak-workload-installer')
        kinds = {'StatefulSet': ('apps', 'statefulsets'), 'Service': ('', 'services'),
                 'ServiceAccount': ('', 'serviceaccounts'), 'PodDisruptionBudget': ('policy', 'poddisruptionbudgets')}
        for obj in self.children['keycloak']:
            group, resource = kinds[obj['kind']]
            for verb in ['get', 'list', 'watch', 'create', 'patch', 'update', 'delete']:
                self.assertTrue(any(group in r['apiGroups'] and resource in r['resources'] and verb in r['verbs'] for r in role['rules']))
        for obj in self.children['keycloak']:
            if obj['kind'] == 'StatefulSet':
                names = [e['name'] for e in obj['spec']['template']['spec']['containers'][0].get('env', [])]
                self.assertEqual(len(names), len(set(names)), names)

    def test_real_chart_server_lookup_needs_only_named_secret_get(self):
        role = next(o for o in self.foundation if o['kind'] == 'Role'
                    and o['metadata']['name'] == 'keycloak-workload-installer')
        secret_rules = [r for r in role['rules'] if 'secrets' in r['resources']]
        self.assertEqual(secret_rules, [{'apiGroups': [''], 'resources': ['secrets'],
                                        'resourceNames': ['keycloak-database-existing', 'keycloak-postgresql'], 'verbs': ['get']}])
        self.assertTrue(secret_allowed(role, 'keycloak', 'keycloak-database-existing', 'get'))
        for namespace, name in [('keycloak', 'private-registry'), ('keycloak', 'keycloak-bootstrap-existing'),
                                ('headlamp', 'keycloak-database-existing'), ('keycloak', 'another-secret')]:
            self.assertFalse(secret_allowed(role, namespace, name, 'get'))
        for name in ['keycloak-database-existing', 'keycloak-postgresql']:
            self.assertTrue(secret_allowed(role, 'keycloak', name, 'get'))
            for verb in ['list', 'watch', 'create', 'update', 'patch', 'delete']:
                self.assertFalse(secret_allowed(role, 'keycloak', name, verb))
        binding = next(o for o in self.foundation if o['kind'] == 'RoleBinding'
                       and o['metadata']['name'] == 'keycloak-workload-installer')
        self.assertEqual(binding['subjects'], [{'kind': 'ServiceAccount', 'name': 'keycloak-installer', 'namespace': 'bigbang'}])
        old = deepcopy(role)
        old['rules'] = [r for r in old['rules'] if 'secrets' not in r['resources']]
        one_name = deepcopy(role)
        next(r for r in one_name['rules'] if 'secrets' in r['resources'])['resourceNames'] = ['keycloak-database-existing']
        for policy, success in [(old, False), (one_name, False), (role, True)]:
            with self.subTest(named_lookup_granted=success), tempfile.TemporaryDirectory() as directory, lookup_server(policy) as (url, requests):
                path = Path(directory)
                config = {'apiVersion': 'v1', 'kind': 'Config',
                          'clusters': [{'name': 'synthetic', 'cluster': {'server': url}}],
                          'users': [{'name': 'synthetic', 'user': {}}],
                          'contexts': [{'name': 'lookup-test', 'context': {'cluster': 'synthetic', 'user': 'synthetic'}}],
                          'current-context': 'lookup-test'}
                (path / 'kubeconfig').write_text(yaml.safe_dump(config))
                args = ['helm', 'template', 'keycloak', str(self.source / 'keycloak/chart'),
                        '--namespace', 'keycloak', '--kubeconfig', str(path / 'kubeconfig'),
                        '--kube-context', 'lookup-test', '--dry-run=server']
                for i, value in enumerate(child_values(self.outer, 'keycloak')):
                    file = path / (str(i) + '.yaml')
                    file.write_text(value)
                    args += ['-f', str(file)]
                result = subprocess.run(args, text=True, capture_output=True, timeout=20,
                                        env={**os.environ, 'KUBECONFIG': str(path / 'kubeconfig')})
                self.assertEqual(result.returncode == 0, success, result.stderr + '\nObserved API requests: ' + repr(requests))
                self.assertIn('/api/v1/namespaces/keycloak/secrets/keycloak-database-existing', requests)
                secret_requests = [p for p in requests if '/secrets' in p]
                expected = {'/api/v1/namespaces/keycloak/secrets/keycloak-database-existing'}
                if policy != old:
                    expected.add('/api/v1/namespaces/keycloak/secrets/keycloak-postgresql')
                self.assertEqual(set(secret_requests), expected)
                if not success:
                    self.assertIn('error calling lookup', result.stderr)
                    self.assertIn('forbidden', result.stderr)
                else:
                    objects = [o for o in yaml.safe_load_all(result.stdout) if o]
                    self.assertFalse(any(o['kind'] == 'Secret' for o in objects))

    def test_native_postgres_separates_superuser_and_application_credentials(self):
        db = next(o for o in self.children['keycloak'] if o['kind'] == 'StatefulSet' and o['metadata']['name'] == 'keycloak-postgresql')
        pod = db['spec']['template']['spec']; c = pod['containers'][0]
        self.assertEqual(c['image'], 'registry1.dso.mil/ironbank/opensource/postgres/postgresql:18.6')
        env = {e['name']: e for e in c['env']}
        self.assertTrue(env['POSTGRES_PASSWORD_FILE']['value'].endswith('/postgres-password'))
        self.assertNotIn('POSTGRES_USER', env) # Native default postgres, not keycloak.
        self.assertEqual(env['KEYCLOAK_DB_PASSWORD']['valueFrom']['secretKeyRef']['key'], 'password')
        self.assertEqual(env['POSTGRES_DB']['value'], 'keycloak')
        self.assertNotIn('command', c); self.assertNotIn('args', c)
        self.assertEqual(next(v for v in pod['volumes'] if v['name'] == 'data')['persistentVolumeClaim']['claimName'], 'keycloak-postgres')
        self.assertFalse(db['spec'].get('volumeClaimTemplates'))
        init = next(o for o in self.foundation if o['kind'] == 'ConfigMap')['data']['01-keycloak.sql']
        self.assertIn('NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION', init)
        self.assertIn('\\getenv app_password KEYCLOAK_DB_PASSWORD', init)
        self.assertIn('/docker-entrypoint-initdb.d', yaml.safe_dump(pod))
        self.assertIn('keycloak-postgres-init', yaml.safe_dump(pod))
        self.assertFalse(any(o['kind'] == 'Secret' for o in self.children['keycloak']))

    def test_oidc_issuer_audience_pkce_ca_and_no_fallback(self):
        contract = yaml.safe_load((EX / 'identity/context.yaml').read_text())
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
        api = yaml.safe_load((EX / 'identity/rke2-oidc.yaml').read_text())
        flags = dict(v.split('=', 1) for v in api['kube-apiserver-arg+'])
        self.assertEqual(flags['oidc-issuer-url'], contract['identity_issuer'])
        self.assertEqual(flags['oidc-client-id'], contract['identity_client_id'])
        self.assertEqual(flags['oidc-required-claim'], 'azp=' + contract['identity_client_id'])
        self.assertEqual(flags['oidc-groups-prefix'], 'oidc:')
        self.assertEqual(flags['oidc-username-claim'], 'sub')
        self.assertEqual(flags['oidc-signing-algs'], 'RS256')
        self.assertIn('/etc/hosts:/etc/hosts:ro', api['kube-apiserver-extra-mount+'])

    def test_worker_budget_and_external_storage(self):
        report = inventory(self.children['headlamp'] + self.children['keycloak'])
        self.assertEqual(report['steadyRequestsMi'], 1152)
        self.assertEqual(report['steadyLimitsMi'], 2304)
        self.assertEqual(report['claims'], [])
        for o in self.children['headlamp'] + self.children['keycloak']:
            if o['kind'] in ['Deployment', 'StatefulSet']:
                pod = o['spec']['template']['spec']
                self.assertEqual(pod['nodeSelector']['kubernetes.io/hostname'], 'cks-worker')
                self.assertEqual(pod['imagePullSecrets'], [{'name': 'private-registry'}])
        pv = next(o for o in self.foundation if o['kind'] == 'PersistentVolume')
        self.assertEqual(pv['spec']['persistentVolumeReclaimPolicy'], 'Retain')
        self.assertEqual(pv['spec']['capacity'], {'storage': '4Gi'})
        self.assertEqual(pv['spec']['local']['path'], '/opt/local-path-provisioner/bigbang-keycloak18')
        self.assertFalse(any(o['kind'] == 'Deployment' for o in self.foundation))

    def permitted(self, group, ns, resource, verb, api=''):
        roles = {o['metadata']['name']: o for o in self.access if o['kind'] == 'ClusterRole'}
        for b in self.access:
            if b['kind'] not in ['RoleBinding', 'ClusterRoleBinding']:
                continue
            if b['kind'] == 'RoleBinding' and b['metadata']['namespace'] != ns:
                continue
            if not any(s['name'] == group for s in b['subjects']):
                continue
            for rule in roles[b['roleRef']['name']]['rules']:
                if api in rule['apiGroups'] and resource in rule['resources'] and verb in rule['verbs']:
                    return True
        return False

    def test_authorization_matrix_and_no_indirect_secret_escalation(self):
        self.assertTrue(self.permitted('oidc:/platform/admins', '', 'nodes', 'list'))
        self.assertTrue(self.permitted('oidc:/platform/admins', 'keycloak', 'statefulsets/scale', 'patch', 'apps'))
        self.assertTrue(self.permitted('oidc:/platform/developers', 'headlamp', 'pods', 'list'))
        for group in ['oidc:/platform/admins', 'oidc:/platform/developers', 'oidc:/platform', 'oidc:/tenants/home/admins', 'no-grants']:
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

    def test_https_routes_exact_selectors_and_no_additional_controller(self):
        routes = [o for o in self.routing if o['kind'] == 'Ingress']
        self.assertEqual(len(routes), 2)
        for obj in routes:
            self.assertEqual(obj['spec']['ingressClassName'], 'traefik')
            self.assertEqual(obj['metadata']['annotations']['traefik.ingress.kubernetes.io/router.entrypoints'], 'websecure')
            self.assertEqual(obj['spec']['tls'][0]['hosts'], [obj['spec']['rules'][0]['host']])
        policies = [o for o in self.routing if o['kind'] == 'NetworkPolicy']
        self.assertEqual(len(policies), 3)
        for obj in policies:
            for rule in obj['spec']['ingress']:
                for source in rule['from']:
                    if 'namespaceSelector' in source:
                        self.assertEqual(source['podSelector']['matchLabels']['app.kubernetes.io/name'], 'rke2-traefik')
        self.assertFalse(any(o['kind'] == 'Secret' for o in self.routing + self.foundation))

    def test_one_shot_realm_claims_and_gated_ansible(self):
        # Parse without rendering secret lookups; never read private files offline.
        realm = yaml.safe_load((EX / 'identity/realm.yaml').read_text())
        client = realm['clients'][0]
        self.assertTrue(client['standardFlowEnabled'])
        for key in ['publicClient', 'implicitFlowEnabled', 'directAccessGrantsEnabled', 'serviceAccountsEnabled', 'fullScopeAllowed']:
            self.assertFalse(client[key])
        self.assertEqual(client['attributes']['pkce.code.challenge.method'], 'S256')
        self.assertEqual(client['protocolMappers'][0]['config']['full.path'], 'true')
        self.assertEqual([u['groups'] for u in realm['users']], [['/platform/admins'], ['/platform/developers'], []])
        for name in ['identity-foundation', 'identity-realm', 'identity-verify']:
            play = yaml.safe_load((EX / 'ansible' / (name + '.yaml')).read_text())[0]
            self.assertFalse(next(v for k, v in play['vars'].items() if k.endswith('_apply') or k == 'identity_verify'))
            with tempfile.TemporaryDirectory() as temp:
                env = {**os.environ, 'ANSIBLE_LOCAL_TEMP': temp + '/local', 'ANSIBLE_REMOTE_TEMP': temp + '/remote'}
                result = subprocess.run(['ansible-playbook', '-i', str(EX / 'ansible/inventory.yaml'),
                                         str(EX / 'ansible' / (name + '.yaml')), '--limit', 'local', '--check'],
                                        env=env, text=True, capture_output=True)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertNotIn('UNCONFIGURED/id-tokens', result.stdout)
                self.assertIn('changed=0', result.stdout)
