"""Real pinned Helm lookup against a loopback authorization model, never a cluster."""
from copy import deepcopy
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

import yaml
from fixtures.lookup_server import clusterrole_list_allowed, lookup_server
from fixtures.render_helpers import build, helm, ordered_values

ROOT = Path(__file__).resolve().parents[2]
LIST_RULE = {'apiGroups': ['rbac.authorization.k8s.io'],
             'resources': ['clusterroles'], 'verbs': ['list']}


class LonghornLookupTests(unittest.TestCase):
    def test_pinned_chart_unnamed_lookup_needs_only_clusterrole_list(self):
        sources = Path(os.environ['PREFLIGHT_SOURCES_DIR'])
        chart = sources / 'longhorn'
        self.assertEqual(str(yaml.safe_load((chart / 'Chart.yaml').read_text())['version']), '1.13.0')
        validation = (chart / 'templates/validate-psp-install.yaml').read_text()
        self.assertIn('lookup "rbac.authorization.k8s.io/v1" "ClusterRole" "" ""', validation)
        self.assertLess(validation.index('lookup '), validation.index('.Values.enablePSP'))
        root = build(ROOT / 'clusters/local')
        parent = next(o for o in root if o['kind'] == 'HelmRelease')
        outer = helm(sources / 'bigbang/chart', 'bigbang', 'bigbang', ordered_values(root, parent))
        values = next(o for o in outer if o['kind'] == 'Secret'
                      and o['metadata']['name'] == 'longhorn-values')['stringData']['values.yaml']
        foundation = build(ROOT / 'configuration/packages/longhorn/prerequisites')
        role = next(o for o in foundation if o['kind'] == 'ClusterRole')
        binding = next(o for o in foundation if o['kind'] == 'ClusterRoleBinding')
        self.assertEqual(binding['subjects'], [{'kind': 'ServiceAccount',
                                              'name': 'longhorn-installer', 'namespace': 'bigbang'}])
        self.assertEqual(binding['roleRef']['name'], role['metadata']['name'])
        self.assertEqual([r for r in role['rules'] if 'clusterroles' in r['resources']
                          and 'list' in r['verbs'] and not r.get('resourceNames')], [LIST_RULE])
        old = deepcopy(role)
        old['rules'].remove(LIST_RULE)
        named_only = deepcopy(old)
        named_only['rules'].append({**LIST_RULE, 'resourceNames': ['longhorn-role']})
        self.assertEqual([r for r in role['rules'] if r not in old['rules']], [LIST_RULE])
        for policy, success in [(old, False), (named_only, False), (role, True)]:
            self.assertEqual(clusterrole_list_allowed(policy), success)
            with self.subTest(unnamed_list_granted=success), tempfile.TemporaryDirectory() as directory, lookup_server(policy, clusterrole_lookup=True) as (url, requests):
                path = Path(directory)
                config = {'apiVersion': 'v1', 'kind': 'Config',
                          'clusters': [{'name': 'synthetic', 'cluster': {'server': url}}],
                          'users': [{'name': 'synthetic', 'user': {}}],
                          'contexts': [{'name': 'lookup-test', 'context': {'cluster': 'synthetic', 'user': 'synthetic'}}],
                          'current-context': 'lookup-test'}
                (path / 'kubeconfig').write_text(yaml.safe_dump(config))
                (path / 'values.yaml').write_text(values)
                args = ['helm', 'template', 'longhorn', str(chart), '--namespace', 'longhorn-system',
                        '--kube-version', '1.36.5', '--kubeconfig', str(path / 'kubeconfig'),
                        '--kube-context', 'lookup-test', '--dry-run=server',
                        '-f', str(path / 'values.yaml'), '--set', 'enablePSP=false']
                result = subprocess.run(args, text=True, capture_output=True, timeout=30,
                                        env={**os.environ, 'KUBECONFIG': str(path / 'kubeconfig')})
                self.assertEqual(result.returncode == 0, success, result.stderr)
                self.assertIn('/apis/rbac.authorization.k8s.io/v1/clusterroles', [p.split('?')[0] for p in requests])
                self.assertFalse(any('/secrets' in p or 'fieldSelector=' in p for p in requests))
                if not success:
                    self.assertIn('error calling lookup', result.stderr)
                    self.assertIn('forbidden', result.stderr.lower())
                else:
                    objects = [o for o in yaml.safe_load_all(result.stdout) if o]
                    self.assertFalse(any(o['kind'] in ['Ingress', 'PodSecurityPolicy'] for o in objects))
