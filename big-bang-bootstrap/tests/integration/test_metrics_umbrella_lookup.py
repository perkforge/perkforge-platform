"""Pinned umbrella lookup against a loopback API and the unchanged scoped installer Role."""
import copy
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
import yaml
from fixtures.lookup_server import lookup_server
from fixtures.render_helpers import build, helm, ordered_values, child_values, release_name
from security import test_gitlab_namespace_ownership as namespace_fixture

ROOT = Path(__file__).resolve().parents[2]
OMITTED = {('Alert', 'monitoring', 'grafana'), ('Provider', 'monitoring', 'grafana'),
           ('Secret', 'monitoring', 'grafana-flux-auth'), ('ConfigMap', 'monitoring', 'flux-grafana-dashboards')}
key = lambda o: (o['kind'], o['metadata'].get('namespace'), o['metadata']['name'])
render = namespace_fixture.GitLabNamespaceOwnership.render


def legacy_values(values):
    result = []
    for text in values:
        value = yaml.safe_load(text)
        grafana = value.get('grafana', {})
        if grafana.get('flux', {}).get('values', {}).get('upstream', {}).get('admin', {}).get('existingSecret') == 'grafana-admin':
            grafana['flux'].pop('values')
            upstream = grafana['values']['upstream']
            upstream['admin']['existingSecret'] = 'grafana-admin'
            upstream.pop('adminUser')
            upstream.pop('adminPassword')
        result.append(yaml.safe_dump(value))
    return result


class MetricsUmbrellaLookup(unittest.TestCase):
    def stage(self, stage):
        objects = build(ROOT/'clusters'/stage)
        parent = next(o for o in objects if o['kind'] == 'HelmRelease' and o['metadata']['name'] == 'bigbang')
        return parent, ordered_values(objects, parent)

    def test_default_current_and_limited_roots_preserve_ownership_and_child_configuration(self):
        sources = Path(os.environ['PREFLIGHT_SOURCES_DIR'])
        for stage in ('local', 'local-metrics-crds', 'local-metrics-limited-pilot', 'local-logging-limited-pilot'):
            with self.subTest(stage=stage):
                parent, values = self.stage(stage)
                args = ('--api-versions', 'monitoring.coreos.com/v1', '--api-versions', 'monitoring.coreos.com/v1alpha1')
                raw = helm(sources/'bigbang/chart', 'bigbang', 'bigbang', values, args)
                old_raw = helm(sources/'bigbang/chart', 'bigbang', 'bigbang', legacy_values(values), args)
                renderer = parent['spec']['postRenderers'][0]['kustomize']
                legacy_renderer = copy.deepcopy(renderer)
                legacy_renderer['patches'] = [p for p in renderer['patches'] if
                    (p['target'].get('kind'), p['target'].get('namespace'), p['target'].get('name')) not in OMITTED]
                for obj in raw:
                    if key(obj) == ('Secret', 'monitoring', 'grafana-flux-auth'):
                        self.assertTrue(all(v in ('', None) for v in obj.get('stringData', {}).values()))
                current = render(raw, renderer)
                legacy = render(old_raw, legacy_renderer)
                omissions = {'patches': [p for p in renderer['patches'] if
                    (p['target'].get('kind'), p['target'].get('namespace'), p['target'].get('name')) in OMITTED]}
                self.assertEqual({key(o): o for o in current},
                                 {key(o): o for o in render(current, omissions)})
                self.assertFalse(any(o['metadata'].get('namespace') == 'monitoring' for o in current))
                a, b = {key(o): o for o in legacy}, {key(o): o for o in current}
                if stage in ('local', 'local-metrics-crds'):
                    self.assertEqual(a, b)
                    continue
                self.assertEqual(set(a)-set(b), OMITTED)
                self.assertEqual(set(b)-set(a), set())
                self.assertEqual({k for k in b if a[k] != b[k]},
                                 {('HelmRelease', 'bigbang', 'grafana'), ('Secret', 'bigbang', 'bigbang-grafana-values')})
                hr = next(o for o in current if key(o) == ('HelmRelease', 'bigbang', 'grafana'))
                self.assertEqual(hr['spec']['values'], {'upstream': {'admin': {
                    'existingSecret': 'grafana-admin', 'userKey': 'admin-user', 'passwordKey': 'admin-password'}}})
                self.assertEqual(hr['spec']['serviceAccountName'], 'grafana-installer')
                children = []
                for outer in (legacy, current):
                    child = helm(sources/'grafana/chart', release_name(hr), 'monitoring', child_values(outer, 'grafana'), args)
                    for pr in hr['spec'].get('postRenderers', []):
                        child = render(child, pr['kustomize'])
                    children.append({key(o): o for o in child})
                self.assertEqual(*children)
                self.assertFalse(any(o['kind'] in ('Secret', 'Ingress', 'Role', 'RoleBinding', 'ClusterRole', 'ClusterRoleBinding')
                                     for o in children[1].values()))
                self.assertEqual(sum(o['kind'] == 'ConfigMap' for o in children[1].values()), 37)
                for sentinel in ({'apiVersion': 'v1', 'kind': 'ConfigMap', 'metadata': {'name': 'foreign-dashboard', 'namespace': 'monitoring'}, 'data': {}},
                                 {'apiVersion': 'v1', 'kind': 'Secret', 'metadata': {'name': 'grafana-flux-auth', 'namespace': 'foreign'}, 'type': 'Opaque'}):
                    self.assertIn(key(sentinel), {key(o) for o in render(current+[sentinel], renderer)})

    def test_real_helm_lookup_fails_before_postrender_legacy_but_fixed_never_reads_secrets(self):
        sources = Path(os.environ['PREFLIGHT_SOURCES_DIR'])
        role = next(o for o in build(ROOT/'configuration/packages/bigbang/prerequisites')
                    if o['kind'] == 'Role' and o['metadata']['name'] == 'stage-umbrella-installer')
        for stage in ('local', 'local-metrics-crds', 'local-metrics-limited-pilot'):
            parent, values = self.stage(stage)
            modes = [('fixed', values)]
            if stage == 'local-metrics-limited-pilot':
                modes.insert(0, ('legacy', legacy_values(values)))
            for mode, selected in modes:
                with self.subTest(stage=stage, mode=mode), tempfile.TemporaryDirectory() as directory, lookup_server(
                        role, secrets={}, helmrelease_lookup=True, monitoring_api=True) as (url, requests):
                    self.assertTrue(url.startswith('http://127.0.0.1:'))
                    path = Path(directory)
                    config = {'apiVersion': 'v1', 'kind': 'Config',
                              'clusters': [{'name': 'synthetic', 'cluster': {'server': url}}],
                              'users': [{'name': 'synthetic', 'user': {}}],
                              'contexts': [{'name': 'synthetic', 'context': {'cluster': 'synthetic', 'user': 'synthetic'}}],
                              'current-context': 'synthetic'}
                    kubeconfig = path/'kubeconfig'; kubeconfig.write_text(yaml.safe_dump(config))
                    args = ['helm', 'template', 'bigbang', str(sources/'bigbang/chart'), '--namespace', 'bigbang',
                            '--kube-version', '1.36.5', '--kubeconfig', str(kubeconfig), '--kube-context', 'synthetic',
                            '--dry-run=server']
                    for index, value in enumerate(selected):
                        file = path/f'{index}.yaml'; file.write_text(value); args += ['-f', str(file)]
                    result = subprocess.run(args, capture_output=True, text=True, timeout=45,
                                            env={**os.environ, 'KUBECONFIG': str(kubeconfig)})
                    secret_requests = [p for p in requests if '/secrets/' in p]
                    if mode == 'legacy':
                        self.assertNotEqual(result.returncode, 0)
                        self.assertIn('error calling lookup', result.stderr)
                        self.assertIn('forbidden', result.stderr.lower())
                        self.assertEqual(secret_requests, ['/api/v1/namespaces/monitoring/secrets/grafana-admin'])
                    else:
                        self.assertEqual(result.returncode, 0, result.stderr)
                        self.assertEqual(secret_requests, [])
                        outer = render([o for o in yaml.safe_load_all(result.stdout) if o], parent['spec']['postRenderers'][0]['kustomize'])
                        self.assertFalse(any(key(o) in OMITTED for o in outer))
                        self.assertFalse(any(o['metadata'].get('namespace') == 'monitoring' for o in outer))
