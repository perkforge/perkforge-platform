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

class IdentityPackageTests(IdentityFixture):
    def test_only_selected_apps_and_no_generated_storage_or_permissions(self):
        self.assertEqual({o['metadata']['name'] for o in self.outer if o['kind'] == 'HelmRelease'}, {'headlamp', 'keycloak'})
        self.assertEqual(Counter(o['kind'] for o in self.children['keycloak']),
                         {'PodDisruptionBudget': 1, 'ServiceAccount': 2, 'Service': 4, 'StatefulSet': 2})
        objects = self.root + self.outer + self.children['headlamp'] + self.children['keycloak']
        for o in objects:
            self.assertNotIn(o['kind'], ['Namespace', 'Ingress', 'PersistentVolumeClaim', 'ClusterRole', 'ClusterRoleBinding', 'RoleBinding'])
        self.assertEqual({o['metadata']['name'] for o in self.root if o['kind'] == 'ConfigMap'},
                         {'values-shared', 'values-provider', 'values-impact', 'values-cluster', 'values-keycloak', 'values-headlamp', 'values-app-stage'})
        for o in self.outer:
            if o['kind'] == 'HelmRelease':
                self.assertEqual(o['spec']['serviceAccountName'], o['metadata']['name'] + '-installer')
                self.assertEqual(o['spec']['storageNamespace'], 'bigbang')
                self.assertFalse(o['spec']['install']['createNamespace'])

    def test_database_readiness_selection_preserves_headlamp_and_installer_scope(self):
        values = ordered_values(self.root, self.parent)
        outer = helm(self.source / 'bigbang/chart', 'bigbang', 'bigbang', values,
                     ['--set', 'addons.keycloak.values.upstream.replicas=0'])
        headlamp = next(o for o in outer if o['kind'] == 'HelmRelease' and o['metadata']['name'] == 'headlamp')
        isolated = helm(self.source / 'headlamp/chart', release_name(headlamp), 'headlamp', child_values(outer,'headlamp'))
        self.assertEqual(isolated, self.children['headlamp'])
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

    def test_package_inventory_and_retained_storage_contract(self):
        report = inventory(self.children['headlamp'] + self.children['keycloak'])
        self.assertEqual(report['steadyRequestsMi'], 1152)
        self.assertEqual(report['steadyLimitsMi'], 2304)
        self.assertEqual(report['claims'], [])
        for obj in self.children['headlamp'] + self.children['keycloak']:
            if obj['kind'] in ['Deployment', 'StatefulSet']:
                pod = obj['spec']['template']['spec']
                self.assertEqual(pod['nodeSelector']['kubernetes.io/hostname'], 'REPLACE_WITH_WORKER_NODE')
                self.assertEqual(pod['imagePullSecrets'], [{'name': 'private-registry'}])
        pv = next(obj for obj in self.foundation if obj['kind'] == 'PersistentVolume')
        self.assertEqual(pv['spec']['persistentVolumeReclaimPolicy'], 'Retain')
        self.assertEqual(pv['spec']['capacity'], {'storage': '4Gi'})
        self.assertTrue(pv['spec']['local']['path'].startswith('/UNCONFIGURED/'))
        self.assertFalse(any(obj['kind'] == 'Deployment' for obj in self.foundation))

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
