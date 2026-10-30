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

class PostgresLookupTests(IdentityFixture):
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
