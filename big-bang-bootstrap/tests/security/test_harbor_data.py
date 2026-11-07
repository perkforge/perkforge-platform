"""Pinned offline Harbor data proposal; no API, credentials or live acceptance."""
import os
from pathlib import Path
import tempfile
import unittest
import yaml

from fixtures.collaboration import package_render
from fixtures.render_helpers import build, helm

ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / 'configuration/packages/harbor'
DATA = PACKAGE / 'data-services'


def named(objects, kind, name):
    return next(o for o in objects if o['kind'] == kind and o['metadata']['name'] == name)


def allows(rules, group, resource, verb):
    return any(group in r['apiGroups'] and resource in r['resources'] and verb in r['verbs'] for r in rules)


class HarborDataCandidate(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sources = Path(os.environ['PREFLIGHT_SOURCES_DIR'])
        cls.objects = build(DATA)
        cls.foundation = build(DATA / 'prerequisites')
        cls.cache = helm(cls.sources / 'valkey', 'harbor-valkey', 'harbor',
                         [(DATA / 'valkey-values.yaml').read_text()])
        cls.app = package_render(ROOT, 'harbor', extra_values=(PACKAGE / 'data-connections-values.yaml',))['harbor'][1]

    def test_no_existing_root_selects_data_app_watch_or_foundation(self):
        for root in (ROOT / 'clusters').iterdir():
            if root.name in ('local-harbor-data', 'local-harbor-app') or not (root / 'kustomization.yaml').exists():
                continue
            with self.subTest(root=root.name):
                objects = build(root)
                self.assertFalse(any(o['metadata']['name'].startswith(('harbor', 'values-harbor'))
                                     or o['metadata'].get('namespace') == 'harbor' for o in objects))
                for obj in objects:
                    if obj['kind'] == 'HelmRelease' and obj['metadata']['name'] == 'platform-cnpg':
                        self.assertNotIn('harbor', obj['spec'].get('values', {}).get('config', {}).get('data', {}).get('WATCH_NAMESPACE', '').split(','))
        self.assertFalse(any(o['kind'] in ('Role', 'RoleBinding', 'Namespace', 'Secret') for o in self.objects))
        release = named(self.objects, 'HelmRelease', 'harbor-valkey')['spec']
        self.assertTrue(release['suspend'])
        self.assertFalse(release['test']['enable'])
        self.assertFalse(release['install']['createNamespace'])
        self.assertEqual(release['install']['crds'], 'Skip')
        self.assertEqual(release['upgrade']['crds'], 'Skip')
        self.assertTrue(release['uninstall']['keepHistory'])
        self.assertEqual(release['chart']['spec']['version'], '0.12.1')
        for phase in ('install', 'upgrade'):
            self.assertEqual(release[phase]['remediation']['retries'], 0)

    def test_postgres_dedicated_native_tls_owner_and_bounded_pool(self):
        pg = named(self.objects, 'Cluster', 'harbor-postgres')
        spec = pg['spec']
        self.assertEqual(pg['metadata']['namespace'], 'harbor')
        self.assertEqual(spec['instances'], 1)
        self.assertFalse(spec['enableSuperuserAccess'])
        self.assertEqual(spec['storage'], {'storageClass': 'longhorn-dedicated', 'size': '8Gi'})
        self.assertEqual(spec['affinity']['nodeSelector'], {'storage.perkforge.io/worker': 'true'})
        self.assertEqual(spec['bootstrap']['initdb'], {'database': 'harbor', 'owner': 'harbor', 'secret': {'name': 'harbor-database'}})
        self.assertIn('hostnossl all all all reject', spec['postgresql']['pg_hba'])
        self.assertEqual(spec['postgresql']['parameters']['max_connections'], '100')
        existing = yaml.safe_load((ROOT / 'configuration/packages/gitlab/data-services/runtime/postgres.yaml').read_text())
        self.assertEqual(spec['imageName'], existing['spec']['imageName'])
        core = named(self.app, 'ConfigMap', 'harbor-core')['data']
        self.assertEqual(core['POSTGRESQL_HOST'], 'harbor-postgres-rw.harbor.svc.cluster.local')
        self.assertEqual(core['POSTGRESQL_SSLMODE'], 'verify-full')
        self.assertEqual(core['POSTGRESQL_MAX_OPEN_CONNS'], '50')
        self.assertEqual(core['POSTGRESQL_MAX_IDLE_CONNS'], '10')
        pod = named(self.app, 'Deployment', 'harbor-core')['spec']['template']['spec']
        env = pod['containers'][0]['env']
        self.assertIn({'name': 'PGSSLROOTCERT', 'value': '/harbor_cust_cert/custom-ca.crt'}, env)
        self.assertIn({'name': 'POSTGRESQL_PASSWORD', 'valueFrom': {'secretKeyRef': {'name': 'harbor-database', 'key': 'password'}}}, env)

    def test_valkey_tls_only_acl_references_and_persistence_render_natively(self):
        self.assertFalse(any(o['kind'] == 'Secret' for o in self.cache))
        values = yaml.safe_load((DATA / 'valkey-values.yaml').read_text())
        existing = yaml.safe_load((ROOT / 'configuration/packages/gitlab/data-services/valkey-values.yaml').read_text())
        self.assertEqual(values['image'], existing['image'])
        self.assertIn('@sha256:', values['image']['tag'])
        script = named(self.cache, 'ConfigMap', 'harbor-valkey-init-scripts')['data']['init.sh']
        self.assertIn('echo "port 0"', script)
        self.assertIn('echo "tls-port 6379"', script)
        self.assertIn('echo "tls-auth-clients no"', script)
        self.assertIn('user default on #$PASSHASH', script)
        conf = named(self.cache, 'ConfigMap', 'harbor-valkey-config')['data']['valkey.conf']
        for line in ('maxmemory 128mb', 'maxmemory-policy noeviction', 'appendonly yes', 'appendfsync everysec'):
            self.assertIn(line, conf)
        pod = named(self.cache, 'Deployment', 'harbor-valkey')['spec']['template']['spec']
        secrets = {v['secret']['secretName'] for v in pod['volumes'] if 'secret' in v}
        self.assertEqual(secrets, {'harbor-valkey-tls', 'harbor-valkey-acl'})
        self.assertFalse(pod['automountServiceAccountToken'])
        self.assertEqual(pod['nodeSelector'], {'storage.perkforge.io/worker': 'true'})
        for c in pod['containers'] + pod['initContainers']:
            self.assertTrue(c['securityContext']['readOnlyRootFilesystem'])
            self.assertTrue(c['securityContext']['runAsNonRoot'])
            self.assertFalse(c['securityContext']['allowPrivilegeEscalation'])
            self.assertEqual(c['securityContext']['capabilities']['drop'], ['ALL'])
            self.assertTrue(c['resources']['requests'])
            self.assertTrue(c['resources']['limits'])
        pvc = named(self.cache, 'PersistentVolumeClaim', 'harbor-valkey')
        self.assertEqual(pvc['spec']['storageClassName'], 'longhorn-dedicated')
        self.assertEqual(pvc['spec']['resources']['requests']['storage'], '2Gi')
        self.assertEqual(pvc['metadata']['annotations']['helm.sh/resource-policy'], 'keep')
        self.assertEqual(named(self.cache, 'Deployment', 'harbor-valkey')['spec']['strategy'], {'type': 'Recreate'})

    def test_app_tls_cache_indices_and_rwo_placement_render_natively(self):
        core = named(self.app, 'ConfigMap', 'harbor-core')['data']
        self.assertIn('@harbor-valkey.harbor.svc.cluster.local:6379/0?', core['_REDIS_URL_CORE'])
        self.assertTrue(core['_REDIS_URL_CORE'].startswith('rediss://'))
        self.assertIn('@harbor-valkey.harbor.svc.cluster.local:6379/2?', core['_REDIS_URL_REG'])
        job = yaml.safe_load(named(self.app, 'ConfigMap', 'harbor-jobservice')['data']['config.yml'])
        self.assertEqual(job['worker_pool']['backend'], 'redis')
        self.assertIn('@harbor-valkey.harbor.svc.cluster.local:6379/1', job['worker_pool']['redis_pool']['redis_url'])
        registry = yaml.safe_load(named(self.app, 'ConfigMap', 'harbor-registry')['data']['config.yml'])
        self.assertTrue(registry['redis']['enableTLS'])
        self.assertEqual(registry['redis']['addr'], 'harbor-valkey.harbor.svc.cluster.local:6379')
        for name in ('harbor-registry', 'harbor-jobservice'):
            deploy = named(self.app, 'Deployment', name)
            self.assertEqual(deploy['spec']['strategy']['type'], 'Recreate')
            self.assertEqual(deploy['spec']['template']['spec']['nodeSelector'], {'storage.perkforge.io/worker': 'true'})
        self.assertFalse(any(o.get('data') or o.get('stringData') for o in self.app if o['kind'] == 'Secret'))

    def test_installer_covers_native_objects_but_has_only_harbor_authority(self):
        release = named(self.objects, 'HelmRelease', 'harbor-valkey')
        spec = release['spec']
        self.assertEqual(spec['storageNamespace'], 'harbor')
        self.assertEqual(spec['targetNamespace'], 'harbor')
        self.assertEqual(spec['serviceAccountName'], 'harbor-data-installer')
        account = named(self.foundation, 'ServiceAccount', spec['serviceAccountName'])
        self.assertEqual(account['metadata']['namespace'], release['metadata']['namespace'])
        self.assertFalse(account['automountServiceAccountToken'])
        role = named(self.foundation, 'Role', spec['serviceAccountName'])
        self.assertEqual(role['metadata']['namespace'], 'harbor')
        mapping = {'ServiceAccount': ('', 'serviceaccounts'), 'ConfigMap': ('', 'configmaps'),
                   'PersistentVolumeClaim': ('', 'persistentvolumeclaims'), 'Service': ('', 'services'),
                   'Deployment': ('apps', 'deployments')}
        for obj in self.cache:
            if obj['metadata'].get('annotations', {}).get('helm.sh/hook') == 'test':
                continue  # Explicitly disabled; not mistaken for a live acceptance check.
            group, resource = mapping[obj['kind']]
            for verb in ('get', 'list', 'watch', 'create', 'update', 'patch', 'delete'):
                self.assertTrue(allows(role['rules'], group, resource, verb), (obj['kind'], verb))
        self.assertTrue(allows(role['rules'], '', 'secrets', 'create'))  # Harbor-only Helm history.
        self.assertFalse(allows(role['rules'], '', 'pods', 'create'))
        self.assertFalse(allows(role['rules'], '', 'pods/exec', 'create'))
        self.assertFalse(any(o['kind'] in ('ClusterRole', 'ClusterRoleBinding') for o in self.foundation))
        for obj in self.foundation:
            if obj['kind'] == 'Role':
                self.assertEqual(obj['metadata']['namespace'], 'harbor')
                for rule in obj['rules']:
                    self.assertFalse(set(rule['verbs']) & {'bind', 'escalate', '*'})
                    self.assertNotIn('*', rule['resources'])
        binding = named(self.foundation, 'RoleBinding', 'harbor-data-installer')
        self.assertEqual(binding['subjects'], [{'kind': 'ServiceAccount', 'name': 'harbor-data-installer', 'namespace': 'bigbang'}])

    def test_additive_operator_role_is_exact_current_namespace_authority(self):
        original = list(yaml.safe_load_all((ROOT / 'configuration/packages/cloudnative-pg/prerequisites.yaml').read_text()))
        old_role = named(original, 'Role', 'platform-cnpg-databases')
        new_role = named(self.foundation, 'Role', 'platform-cnpg-databases')
        self.assertEqual(old_role['rules'], new_role['rules'])
        self.assertEqual(new_role['metadata']['namespace'], 'harbor')
        old_binding = named(original, 'RoleBinding', 'platform-cnpg-databases')
        binding = named(self.foundation, 'RoleBinding', 'platform-cnpg-databases')
        self.assertEqual(old_binding['roleRef'], binding['roleRef'])
        self.assertEqual(old_binding['subjects'], binding['subjects'])
        self.assertEqual(binding['metadata']['namespace'], 'harbor')
        # Existing app foundation has the same Namespace identity/content.
        original_app = build(PACKAGE / 'prerequisites')
        self.assertEqual(named(original_app, 'Namespace', 'harbor'), named(self.foundation, 'Namespace', 'harbor'))

    def test_watch_patch_keeps_current_namespaces_and_native_env_consistent(self):
        proposal = yaml.safe_load((DATA / 'operator-watch-review.yaml').read_text())
        watch = proposal['spec']['values']['config']['data']['WATCH_NAMESPACE']
        self.assertEqual(watch, 'gitlab,tenant-home-nextcloud,harbor')
        existing = named(build(ROOT / 'clusters/local-metrics-limited-pilot-ui'), 'HelmRelease', 'platform-cnpg')
        self.assertEqual(set(existing['spec']['values']['config']['data']['WATCH_NAMESPACE'].split(',')),
                         set(watch.split(',')) - {'harbor'})
        native = helm(self.sources / 'cnpg', 'platform-cnpg', 'cnpg-system',
                      [(ROOT / 'configuration/packages/cloudnative-pg/values.yaml').read_text(),
                       yaml.safe_dump(proposal['spec']['values'])])
        with tempfile.TemporaryDirectory(prefix='harbor-cnpg-watch-') as directory:
            path = Path(directory)
            (path / 'objects.yaml').write_text(yaml.safe_dump_all(native))
            (path / 'kustomization.yaml').write_text(yaml.safe_dump({
                'resources': ['objects.yaml'], 'patches': proposal['spec']['postRenderers'][0]['kustomize']['patches']}))
            patched = build(path)
        env = named(patched, 'Deployment', 'platform-cnpg')['spec']['template']['spec']['containers'][0]['env']
        self.assertEqual([item for item in env if item['name'] == 'WATCH_NAMESPACE'], [{'name': 'WATCH_NAMESPACE', 'value': watch}])
        # Runtime native namespaced rules match the proposed Harbor grant.
        runtime = next(o for o in native if o['kind'] == 'Role')
        self.assertEqual(runtime['rules'], named(self.foundation, 'Role', 'platform-cnpg-databases')['rules'])

    def test_data_ingress_is_scoped_to_exact_components_and_operator(self):
        deny = named(self.objects, 'NetworkPolicy', 'harbor-data-default-deny-ingress')['spec']
        self.assertEqual(deny, {'podSelector': {}, 'policyTypes': ['Ingress']})
        pg = named(self.objects, 'NetworkPolicy', 'harbor-postgres-from-core')['spec']
        self.assertEqual(pg['podSelector'], {'matchLabels': {'cnpg.io/cluster': 'harbor-postgres'}})
        self.assertEqual(pg['ingress'][0], {
            'from': [{'podSelector': {'matchLabels': {'app': 'harbor', 'release': 'harbor', 'component': 'core'}}}],
            'ports': [{'protocol': 'TCP', 'port': 5432}]})
        operator = pg['ingress'][1]['from'][0]
        self.assertEqual(operator['namespaceSelector']['matchLabels'], {'kubernetes.io/metadata.name': 'cnpg-system'})
        self.assertEqual(operator['podSelector']['matchLabels'], {'app.kubernetes.io/instance': 'platform-cnpg', 'app.kubernetes.io/name': 'cloudnative-pg'})
        cache = named(self.objects, 'NetworkPolicy', 'harbor-valkey-from-components')['spec']
        self.assertEqual(cache['podSelector']['matchLabels'],
                         named(self.cache, 'Deployment', 'harbor-valkey')['spec']['template']['metadata']['labels'])
        allowed = cache['ingress'][0]['from'][0]['podSelector']
        self.assertEqual(allowed['matchLabels'], {'app': 'harbor', 'release': 'harbor'})
        self.assertEqual(allowed['matchExpressions'], [{'key': 'component', 'operator': 'In', 'values': ['core', 'jobservice', 'registry']}])
        self.assertEqual(cache['ingress'][0]['ports'], [{'protocol': 'TCP', 'port': 6379}])
        for policy in [o for o in self.objects if o['kind'] == 'NetworkPolicy']:
            self.assertEqual(policy['metadata']['namespace'], 'harbor')
            for rule in policy['spec'].get('ingress', []):
                self.assertTrue(rule['from'])
                self.assertTrue(rule['ports'])
                self.assertFalse(any('ipBlock' in peer for peer in rule['from']))

    def test_reviewed_request_and_storage_budget_is_not_silently_expanded(self):
        pg = named(self.objects, 'Cluster', 'harbor-postgres')['spec']
        self.assertEqual(pg['resources'], {'requests': {'cpu': '250m', 'memory': '512Mi'}, 'limits': {'cpu': '1', 'memory': '1Gi'}})
        cache = named(self.cache, 'Deployment', 'harbor-valkey')['spec']['template']['spec']
        self.assertEqual(cache['containers'][0]['resources'], {'requests': {'cpu': '100m', 'memory': '256Mi'}, 'limits': {'cpu': '500m', 'memory': '512Mi'}})
        for obj in self.app:
            if obj['kind'] == 'Deployment':
                self.assertEqual(obj['spec']['replicas'], 1)
                for container in obj['spec']['template']['spec']['containers']:
                    self.assertEqual(container['resources']['requests'], {'cpu': '100m', 'memory': '256Mi'})
        self.assertEqual(sum(len(o['spec']['template']['spec']['containers']) for o in self.app if o['kind'] == 'Deployment'), 6)
        claims = {o['metadata']['name']: o['spec'] for o in self.app if o['kind'] == 'PersistentVolumeClaim'}
        self.assertEqual(claims['harbor-registry']['resources']['requests']['storage'], '10Gi')
        self.assertEqual(claims['harbor-jobservice']['resources']['requests']['storage'], '1Gi')
