"""Offline native ESO pin, rendering, installer and runtime authorization contract."""
import copy
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
import yaml

ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / 'configuration/external-secrets'
VALUES = PACKAGE / 'runtime/native-values.yaml'


def load(path):
    return yaml.safe_load(path.read_text())


def objects(text):
    return [d for d in yaml.safe_load_all(text) if d]


def build(path):
    return objects(subprocess.check_output(['kubectl', 'kustomize', str(path)], text=True))


def key(d):
    return d['kind'], d['metadata'].get('namespace', ''), d['metadata']['name']


class NativeESOContract(unittest.TestCase):
    def test_native_only_inherited_pins_and_suspended(self):
        values = load(VALUES)
        self.assertEqual(set(values), {'addons'})
        addon = values['addons']['externalSecrets']
        self.assertTrue(addon['enabled'])
        self.assertTrue(addon['flux']['suspend'])
        self.assertNotIn('git', addon)
        self.assertNotIn('helmRepo', addon)
        self.assertNotIn('image', addon['values']['upstream'])
        for operation in ('install', 'upgrade'):
            self.assertEqual(addon['flux'][operation]['crds'], 'Skip')
        u = addon['values']['upstream']
        self.assertFalse(u['rbac']['create'])
        self.assertNotIn('scopedNamespace', u)
        for option in ('processPushSecret', 'processClusterPushSecret', 'processClusterExternalSecret', 'processClusterGenerator'):
            self.assertFalse(u[option])
        self.assertEqual(u['controllerClass'], 'perkforge')

    def test_explicit_global_read_and_finite_platform_write_boundary(self):
        docs = objects((PACKAGE / 'prerequisites/foundation.yaml').read_text())
        cluster = next(d for d in docs if d['kind'] == 'ClusterRole')
        secret = next(r for r in cluster['rules'] if 'secrets' in r['resources'])
        self.assertEqual(secret['verbs'], ['list', 'watch'])
        for rule in cluster['rules']:
            if set(rule['verbs']) - {'get', 'list', 'watch'}:
                self.assertEqual(rule['resources'], ['clustersecretstores/status'])
                self.assertEqual(rule['resourceNames'], ['openbao-platform'])
                self.assertEqual(rule['verbs'], ['patch'])
        runtime = next(d for d in docs if d['kind'] == 'Role' and d['metadata']['name'] == 'external-secrets-runtime')
        token = next(r for r in runtime['rules'] if 'serviceaccounts/token' in r['resources'])
        self.assertEqual(token['resourceNames'], ['eso-platform'])
        self.assertEqual(token['verbs'], ['create'])
        self.assertEqual(runtime['metadata']['namespace'], 'external-secrets')
        for d in docs:
            self.assertNotEqual(d['metadata'].get('namespace'), 'tenant-portal')
            if d['kind'] in ('Role', 'ClusterRole'):
                for r in d['rules']:
                    self.assertNotIn('*', r['verbs'] + r['resources'] + r['apiGroups'])
                    self.assertFalse(set(r['verbs']) & {'bind', 'escalate', 'impersonate'})
                    self.assertFalse(set(r['resources']) & {'pods/exec', 'customresourcedefinitions', 'tokenreviews'})

    @unittest.skipUnless(shutil.which('kubectl'), 'kubectl kustomize required')
    def test_optional_root_preserves_every_previous_resource(self):
        old = {key(d): d for d in build(ROOT / 'clusters/local-velero')}
        new = {key(d): d for d in build(ROOT / 'clusters/local-external-secrets')}
        self.assertTrue(old.keys() <= new.keys())
        self.assertEqual(set(new) - set(old), {('ConfigMap', 'bigbang', 'external-secrets-native-values')})
        for k in old:
            if k == ('HelmRelease', 'bigbang', 'bigbang'):
                adjusted = copy.deepcopy(new[k])
                self.assertEqual(adjusted['spec']['valuesFrom'].pop()['name'], 'external-secrets-native-values')
                patch = adjusted['spec']['postRenderers'][0]['kustomize']['patches'].pop()
                self.assertEqual(patch['target'], {'kind': 'Namespace', 'name': 'external-secrets'})
                self.assertEqual(adjusted, old[k])
            else:
                self.assertEqual(old[k], new[k])
        self.assertNotIn('external-secrets', (ROOT / 'clusters/local/kustomization.yaml').read_text())

    def test_foundation_has_no_credential_or_store_side_effects(self):
        docs = objects((PACKAGE / 'prerequisites/foundation.yaml').read_text())
        self.assertFalse({d['kind'] for d in docs} & {'Secret', 'SecretStore', 'ClusterSecretStore', 'ExternalSecret'})
        play = load(ROOT / 'configuration/ansible/external-secrets-prerequisites.yaml')[0]
        self.assertIs(play['vars']['external_secrets_foundation_apply'], False)
        block = play['tasks'][-1]
        self.assertEqual(block['when'], 'external_secrets_foundation_apply and not ansible_check_mode')
        text = yaml.safe_dump(block)
        for required in ('verify-release.yaml', 'expected_cluster_uid', 'crd_bundle_sha256', 'status', '--porcelain', '--field-manager=perkforge-external-secrets-crds'):
            self.assertIn(required, text)
        self.assertNotIn('get_url', text)
        self.assertNotIn('--force-conflicts', text)

    @unittest.skipUnless(shutil.which('ansible-playbook'), 'Ansible required')
    def test_default_and_check_modes_make_no_kubernetes_call(self):
        with tempfile.TemporaryDirectory() as directory:
            tmp = Path(directory)
            fake = tmp / 'kubectl'
            fake.write_text('#!/bin/sh\necho unexpected API call >&2\nexit 99\n')
            fake.chmod(0o755)
            inventory = tmp / 'inventory.yaml'
            inventory.write_text('all:\n  children:\n    bootstrap_clusters:\n      hosts:\n        local:\n          ansible_connection: local\n          deployment_environment: local\n')
            env = dict(os.environ, PATH=str(tmp) + ':' + os.environ['PATH'], ANSIBLE_LOCAL_TEMP=str(tmp / 'ansible'))
            play = ROOT / 'configuration/ansible/external-secrets-prerequisites.yaml'
            for extra in ([], ['--check', '-e', '{"external_secrets_foundation_apply": true}']):
                proc = subprocess.run(['ansible-playbook', '-i', str(inventory), str(play), *extra], env=env, capture_output=True, text=True)
                self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
                self.assertNotIn('unexpected API call', proc.stdout + proc.stderr)


@unittest.skipUnless(os.environ.get('ESO_CHART_SOURCE') and os.environ.get('PREFLIGHT_SOURCES_DIR') and shutil.which('helm'), 'exact native fixtures and Helm required')
class PinnedESOChart(unittest.TestCase):
    def test_exact_chart_schema_flags_and_installer_cover_render(self):
        chart = Path(os.environ['ESO_CHART_SOURCE']) / 'chart'
        pin = load(PACKAGE / 'source-pin.yaml')
        self.assertEqual(load(chart / 'Chart.yaml')['version'], pin['package_version'])
        self.assertEqual(hashlib.sha256((chart / 'crds/bundle.yaml').read_bytes()).hexdigest(), pin['crd_bundle_sha256'])
        self.assertEqual(hashlib.sha256((chart / 'charts/external-secrets-2.12.0.tgz').read_bytes()).hexdigest(), pin['upstream_archive_sha256'])
        umbrella = Path(os.environ['PREFLIGHT_SOURCES_DIR']) / 'bigbang/chart'
        self.assertEqual(load(umbrella / 'Chart.yaml')['version'], pin['bigbang_version'])
        self.assertEqual(load(umbrella / 'values.yaml')['addons']['externalSecrets']['git']['tag'], pin['package_version'])
        # Exercise native umbrella defaults/common/overlay precedence as Flux does.
        from fixtures.render_helpers import helm, child_values, ordered_values
        root_objects = build(ROOT / 'clusters/local-external-secrets')
        parent = next(d for d in root_objects if d['kind'] == 'HelmRelease' and d['metadata']['name'] == 'bigbang')
        maps = {d['metadata']['name']: d for d in root_objects if d['kind'] == 'ConfigMap'}
        missing = [r['name'] for r in parent['spec']['valuesFrom'] if r['name'] not in maps and not r.get('optional')]
        self.assertEqual(missing, ['velero-runtime-values'])
        # Only this externally generated input is absent from Git. Use the existing
        # public Velero-only disabled fixture, not fabricated live backup settings.
        velero_fixture = load(ROOT / 'configuration/packages/velero/candidate-values.yaml')
        self.assertEqual(set(velero_fixture), {'addons'})
        self.assertEqual(set(velero_fixture['addons']), {'velero'})
        root_objects.append({'apiVersion': 'v1', 'kind': 'ConfigMap',
                             'metadata': {'name': 'velero-runtime-values', 'namespace': 'bigbang'},
                             'data': {'velero.yaml': yaml.safe_dump(velero_fixture)}})
        outer = helm(umbrella, 'bigbang', 'bigbang', ordered_values(root_objects, parent))
        release = next(d for d in outer if d['kind'] == 'HelmRelease' and d['metadata']['name'] == 'external-secrets')
        self.assertTrue(release['spec']['suspend'])
        self.assertEqual(release['spec']['serviceAccountName'], 'external-secrets-installer')
        self.assertEqual(release['spec']['storageNamespace'], 'external-secrets')
        effective_child_values = child_values(outer, 'external-secrets')
        self.assertTrue(yaml.safe_load(effective_child_values[1])['monitoring']['enabled'])
        self.assertFalse(yaml.safe_load(effective_child_values[1])['istio']['enabled'])
        inherited_render = helm(chart, 'external-secrets', 'external-secrets', effective_child_values,
                                ('--api-versions', 'monitoring.coreos.com/v1/ServiceMonitor'))
        self.assertFalse({d['kind'] for d in inherited_render} & {'PeerAuthentication', 'ServiceMonitor'})
        self.assertTrue(all(d['metadata'].get('namespace') == 'external-secrets' for d in inherited_render))
        root_objects[-1]['data']['velero.yaml'] = '{}'
        without_velero = helm(umbrella, 'bigbang', 'bigbang', ordered_values(root_objects, parent))
        self.assertEqual(child_values(without_velero, 'external-secrets'), effective_child_values)
        foundation = objects((PACKAGE / 'prerequisites/foundation.yaml').read_text())
        installer = next(d for d in foundation if d['kind'] == 'Role' and d['metadata']['name'] == 'external-secrets-installer')
        plural = {'NetworkPolicy': 'networkpolicies', 'ServiceAccount': 'serviceaccounts',
                  'ConfigMap': 'configmaps', 'Deployment': 'deployments', 'Service': 'services'}
        for d in inherited_render:
            self.assertIn(d['kind'], plural)
            group = d['apiVersion'].split('/')[0] if '/' in d['apiVersion'] else ''
            self.assertTrue(any(group in r['apiGroups'] and plural[d['kind']] in r['resources']
                                and {'get', 'create', 'patch', 'update', 'delete'} <= set(r['verbs'])
                                for r in installer['rules']), d['kind'])
        crds = objects((chart / 'crds/bundle.yaml').read_text())
        self.assertEqual(len(crds), pin['crd_count'])
        for d in crds:
            if d['metadata']['name'] in ('externalsecrets.external-secrets.io', 'secretstores.external-secrets.io', 'clustersecretstores.external-secrets.io'):
                self.assertEqual([v['name'] for v in d['spec']['versions'] if v['served']], ['v1'])
        candidate = load(VALUES)['addons']['externalSecrets']['values']
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'values.yaml'
            path.write_text(yaml.safe_dump(candidate))
            rendered = objects(subprocess.check_output(['helm', 'template', 'external-secrets', str(chart), '-n', 'external-secrets', '-f', str(path)], text=True))
        self.assertFalse({d['kind'] for d in rendered} & {'ClusterRole', 'ClusterRoleBinding', 'Role', 'RoleBinding', 'CustomResourceDefinition', 'SecretStore', 'ClusterSecretStore', 'ExternalSecret'})
        deployment = next(d for d in rendered if d['kind'] == 'Deployment')
        self.assertEqual(deployment['spec']['template']['spec']['imagePullSecrets'], [{'name': 'private-registry'}])
        args = deployment['spec']['template']['spec']['containers'][0]['args']
        self.assertIn('--controller-class=perkforge', args)
        self.assertIn('--enable-managed-secrets-caching=false', args)
        self.assertIn('--enable-generator-state=false', args)
        self.assertNotIn('--enable-cluster-store-reconciler=false', args)
        self.assertFalse(any(a.startswith('--namespace=') for a in args))
        allowed = {'NetworkPolicy', 'ServiceAccount', 'ConfigMap', 'Deployment', 'Service'}
        self.assertTrue({d['kind'] for d in rendered} <= allowed)
        self.assertFalse(any('secrets-api-subnets' in d['metadata']['name'] for d in rendered))
        self.assertTrue(all(d['metadata'].get('namespace', 'external-secrets') == 'external-secrets' for d in rendered))


if __name__ == '__main__':
    unittest.main()
