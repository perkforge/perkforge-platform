"""Render real charts/post-render ownership and check scoped installer coverage offline."""
from collections import Counter
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
import base64
import uuid

import yaml

from render_helpers import build, child_values, helm, ordered_values, release_name
from resource_inventory import inventory

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / 'examples'
STAGE = EXAMPLES / 'stages/local-headlamp'


class HeadlampStageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sources = Path(os.environ['PREFLIGHT_SOURCES_DIR'])
        cls.root = build(STAGE)
        cls.foundation = build(STAGE / 'foundation')
        cls.parent = next(o for o in cls.root if o['kind'] == 'HelmRelease')
        cls.outer_raw = helm(cls.sources / 'bigbang/chart', 'bigbang', 'bigbang',
                             ordered_values(cls.root, cls.parent))
        # Exercise the same native Kustomize operation Flux's Helm post-renderer uses.
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            (path / 'render.yaml').write_text(yaml.safe_dump_all(cls.outer_raw))
            recipe = {'apiVersion': 'kustomize.config.k8s.io/v1beta1',
                      'kind': 'Kustomization', 'resources': ['render.yaml'],
                      **cls.parent['spec']['postRenderers'][0]['kustomize']}
            (path / 'kustomization.yaml').write_text(yaml.safe_dump(recipe))
            cls.outer = build(path)
        cls.child_release = next(o for o in cls.outer if o['kind'] == 'HelmRelease')
        cls.child = helm(cls.sources / 'headlamp/chart', release_name(cls.child_release),
                         'headlamp', child_values(cls.outer, 'headlamp'))

    def allowed(self, identity, namespace, group, resource, verb):
        roles = {(o['metadata']['namespace'], o['metadata']['name']): o
                 for o in self.foundation if o['kind'] == 'Role'}
        for binding in (o for o in self.foundation if o['kind'] == 'RoleBinding'):
            if binding['metadata']['namespace'] != namespace:
                continue
            if not any((s['namespace'], s['name']) == identity for s in binding['subjects']):
                continue
            role = roles[namespace, binding['roleRef']['name']]
            for rule in role['rules']:
                if group in rule['apiGroups'] and resource in rule['resources'] and verb in rule['verbs']:
                    return True
        return False

    def test_exact_root_parent_child_inventory_without_other_apps(self):
        self.assertEqual(Counter(o['kind'] for o in self.root),
                         {'ConfigMap': 4, 'GitRepository': 1, 'HelmRelease': 1})
        self.assertEqual(Counter(o['kind'] for o in self.outer),
                         {'Secret': 2, 'GitRepository': 1, 'HelmRelease': 1})
        self.assertEqual(Counter(o['kind'] for o in self.child),
                         {'ServiceAccount': 1, 'Service': 1, 'Deployment': 1})
        self.assertEqual(self.child_release['metadata']['name'], 'headlamp')
        self.assertEqual({o['metadata']['name'] for o in self.outer if o['kind'] == 'GitRepository'}, {'headlamp'})
        self.assertEqual({o['metadata']['name'] for o in self.outer if o['kind'] == 'Secret'},
                         {'bigbang-headlamp-values', 'bigbang-prometheus-operator-crds-values'})
        self.assertEqual({o['metadata']['namespace'] for o in self.root}, {'bigbang'})
        self.assertEqual({o['metadata']['namespace'] for o in self.child}, {'headlamp'})
        self.assertEqual(Counter(o['kind'] for o in self.foundation),
                         {'Namespace': 2, 'ServiceAccount': 3, 'Role': 4, 'RoleBinding': 4})
        self.assertEqual({o['metadata']['name'] for o in self.foundation if o['kind'] == 'Namespace'},
                         {'bigbang', 'headlamp'})

    def test_namespaces_have_one_owner_and_no_installer_cluster_rights(self):
        self.assertEqual([o['metadata']['name'] for o in self.outer_raw if o['kind'] == 'Namespace'], ['headlamp'])
        self.assertFalse(any(o['kind'] == 'Namespace' for o in self.root + self.outer + self.child))
        for obj in self.foundation:
            self.assertNotIn(obj['kind'], ['ClusterRole', 'ClusterRoleBinding'])
            if obj['kind'] == 'Role':
                for rule in obj['rules']:
                    self.assertNotIn('*', rule['verbs'] + rule['apiGroups'] + rule['resources'])
                    self.assertFalse(set(rule['resources']) & {'roles', 'rolebindings', 'namespaces',
                                     'pods/exec', 'pods/portforward', 'serviceaccounts/token'})
            if obj['kind'] == 'RoleBinding':
                self.assertEqual(obj['roleRef']['kind'], 'Role')
        for identity in [('flux-system', 'platform-reconciler'), ('bigbang', 'platform-reconciler'),
                         ('bigbang', 'headlamp-installer')]:
            for verb in ['create', 'patch', 'delete']:
                self.assertFalse(self.allowed(identity, '', '', 'namespaces', verb))
                self.assertFalse(self.allowed(identity, 'kube-system', '', 'secrets', verb))

    def test_rbac_covers_actual_render_and_helm_readiness_without_ui_grants(self):
        kinds = {'ConfigMap': ('', 'configmaps'), 'Secret': ('', 'secrets'),
                 'GitRepository': ('source.toolkit.fluxcd.io', 'gitrepositories'),
                 'HelmRelease': ('helm.toolkit.fluxcd.io', 'helmreleases'),
                 'ServiceAccount': ('', 'serviceaccounts'), 'Service': ('', 'services'),
                 'Deployment': ('apps', 'deployments')}
        for objects, identity, verbs in [
            (self.root, ('flux-system', 'platform-reconciler'), ['get', 'list', 'watch', 'create', 'patch', 'update']),
            (self.outer, ('bigbang', 'platform-reconciler'), ['get', 'list', 'watch', 'create', 'patch', 'update', 'delete']),
            (self.child, ('bigbang', 'headlamp-installer'), ['get', 'list', 'watch', 'create', 'patch', 'update', 'delete']),
        ]:
            for obj in objects:
                group, resource = kinds[obj['kind']]
                for verb in verbs:
                    self.assertTrue(self.allowed(identity, obj['metadata']['namespace'], group, resource, verb),
                                    (identity, obj['kind'], verb))
        child = ('bigbang', 'headlamp-installer')
        for verb in ['get', 'list', 'watch']:
            self.assertTrue(self.allowed(child, 'headlamp', '', 'pods', verb))
            self.assertTrue(self.allowed(child, 'headlamp', 'apps', 'replicasets', verb))
        for verb in ['create', 'patch', 'delete']:
            self.assertFalse(self.allowed(child, 'headlamp', '', 'pods', verb))
            self.assertFalse(self.allowed(child, 'headlamp', 'apps', 'replicasets', verb))
        self.assertTrue(self.allowed(child, 'bigbang', '', 'secrets', 'create'))
        self.assertFalse(self.allowed(child, 'headlamp', '', 'secrets', 'get'))
        self.assertFalse(self.allowed(('flux-system', 'platform-reconciler'), 'bigbang', '', 'secrets', 'get'))
        app_sa = next(o['metadata']['name'] for o in self.child if o['kind'] == 'ServiceAccount')
        self.assertEqual(app_sa, 'headlamp-headlamp')
        for ns in ['headlamp', 'bigbang', 'kube-system']:
            self.assertFalse(self.allowed(('headlamp', app_sa), ns, '', 'secrets', 'get'))
        self.assertFalse(any(o['kind'].endswith('RoleBinding') for o in self.child))

    def test_actual_pull_wiring_limits_private_service_and_bounded_retries(self):
        deployment = next(o for o in self.child if o['kind'] == 'Deployment')
        pod = deployment['spec']['template']['spec']
        self.assertEqual(pod['imagePullSecrets'], [{'name': 'private-registry'}])
        self.assertEqual(pod['nodeSelector']['kubernetes.io/hostname'], 'cks-worker')
        self.assertEqual(pod['containers'][0]['resources'],
                         {'requests': {'cpu': '100m', 'memory': '128Mi'},
                          'limits': {'cpu': '500m', 'memory': '256Mi'}})
        self.assertFalse(any('unsafe' in arg for c in pod['containers'] for arg in c.get('args', [])))
        self.assertNotIn('hostNetwork', pod)
        self.assertTrue(all('hostPort' not in port for c in pod['containers'] for port in c.get('ports', [])))
        service = next(o for o in self.child if o['kind'] == 'Service')
        self.assertEqual(service['spec']['type'], 'ClusterIP')
        report = inventory(self.child)
        self.assertEqual(report['claims'], [])
        self.assertEqual(report['steadyRequestsMi'], 128)
        self.assertEqual(report['steadyLimitsMi'], 256)
        self.assertEqual(report['images'], ['registry1.dso.mil/ironbank/opensource/headlamp-k8s/headlamp:v0.45.0'])
        self.assertEqual(self.parent['spec']['serviceAccountName'], 'platform-reconciler')
        self.assertEqual(self.child_release['spec']['serviceAccountName'], 'headlamp-installer')
        self.assertEqual(self.child_release['spec']['storageNamespace'], 'bigbang')
        for release in [self.parent, self.child_release]:
            self.assertFalse(release['spec']['install']['createNamespace'])
            for action in ['install', 'upgrade']:
                self.assertEqual(release['spec'][action]['remediation'],
                                 {'retries': 0, 'remediateLastFailure': False})

    def test_pinned_crd_declares_stage_helm_fields(self):
        objects = yaml.safe_load_all((self.sources / 'bigbang/base/flux/gotk-components.yaml').read_text())
        crd = next(o for o in objects if o and o['kind'] == 'CustomResourceDefinition'
                   and o['metadata']['name'] == 'helmreleases.helm.toolkit.fluxcd.io')
        spec = next(v for v in crd['spec']['versions'] if v['name'] == 'v2')['schema']['openAPIV3Schema']['properties']['spec']['properties']
        for field in ['postRenderers', 'storageNamespace', 'serviceAccountName', 'install', 'upgrade']:
            self.assertIn(field, spec)
        for action in ['install', 'upgrade']:
            fields = spec[action]['properties']['remediation']['properties']
            self.assertIn('remediateLastFailure', fields)
            self.assertIn('retries', fields)

    def test_foundation_defaults_and_wrong_target_never_call_api(self):
        for target, extra, expected in [('local', {}, 0), ('dev', {}, 2),
            ('local', {'headlamp_registry_apply': True}, 2),
            ('local', {'foundation_apply': True, 'config_tag': 'main'}, 2)]:
            with self.subTest(target=target, extra=extra), tempfile.TemporaryDirectory() as directory:
                path = Path(directory)
                marker = path / 'api-called'
                for tool in ['kubectl', 'gh']:
                    stub = path / tool
                    stub.write_text('#!/bin/sh\ntouch "' + str(marker) + '"\nexit 99\n')
                    stub.chmod(0o700)
                result = subprocess.run(['ansible-playbook', '-i', str(EXAMPLES / 'ansible/inventory.yaml'),
                    str(EXAMPLES / 'ansible/headlamp-foundation.yaml'), '--limit', target,
                    '-e', json.dumps(extra)], text=True, capture_output=True,
                    env={**os.environ, 'PATH': directory + ':' + os.environ['PATH'],
                         'KUBECONFIG': '/dev/null', 'ANSIBLE_LOCAL_TEMP': directory + '/ansible',
                         'ANSIBLE_REMOTE_TEMP': directory + '/remote'})
                self.assertEqual(result.returncode, expected, result.stdout + result.stderr)
                self.assertFalse(marker.exists())
                if expected == 0:
                    self.assertIn('changed=0', result.stdout)

    def test_stage_inputs_really_render_a_paused_public_seed(self):
        with tempfile.TemporaryDirectory() as directory:
            template = EXAMPLES / 'ansible/seed.yaml.j2'
            args = json.dumps({'msg': "{{ lookup('ansible.builtin.template', '" + str(template) + "') }}"})
            output = subprocess.check_output(['ansible', 'local', '-i', str(EXAMPLES / 'ansible/inventory.yaml'),
                '-m', 'ansible.builtin.debug', '-a', args, '-e', '@' + str(STAGE / 'bootstrap-inputs.yaml')],
                text=True, env={**os.environ, 'ANSIBLE_LOCAL_TEMP': directory, 'ANSIBLE_NOCOLOR': '1'})
            response, _ = json.JSONDecoder().raw_decode(output[output.index('{'):])
            seed = list(yaml.safe_load_all(response['msg']))
            source = next(o for o in seed if o['kind'] == 'GitRepository')
            root = next(o for o in seed if o['kind'] == 'Kustomization')
            self.assertNotIn('secretRef', source['spec'])
            self.assertTrue(source['spec']['suspend'])
            self.assertTrue(root['spec']['suspend'])
            self.assertFalse(root['spec']['prune'])
            self.assertEqual(root['spec']['path'], './local-lab-big-bang/examples/stages/local-headlamp')
            self.assertEqual(root['spec']['serviceAccountName'], 'platform-reconciler')

    def test_registry_delivery_is_private_stdin_and_rejects_insecure_file(self):
        for mode, expected in [(0o600, 0), (0o644, 2)]:
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as directory:
                path = Path(directory)
                credential = path / 'fixture-only'
                value = 'fixture-' + uuid.uuid4().hex
                credential.write_text(value)
                credential.chmod(mode)
                payload = path / 'stdin.json'
                arguments = path / 'arguments.txt'
                stub = path / 'kubectl'
                stub.write_text('#!/bin/sh\ncat > "' + str(payload) + '"\nprintf "%s\\n" "$@" > "' + str(arguments) + '"\n')
                stub.chmod(0o700)
                play = path / 'fixture.yaml'
                play.write_text(yaml.safe_dump([{'hosts': 'localhost', 'connection': 'local',
                    'gather_facts': False, 'vars': {'registry_username': 'fixture-user',
                    'registry_credential_file': str(credential), 'target_kubeconfig': '/dev/null',
                    'target_context': 'fixture'}, 'tasks': [{'ansible.builtin.include_tasks':
                    str(EXAMPLES / 'ansible/headlamp-registry.yaml')}]}]))
                result = subprocess.run(['ansible-playbook', str(play)], text=True, capture_output=True,
                    env={**os.environ, 'PATH': directory + ':' + os.environ['PATH'],
                         'ANSIBLE_LOCAL_TEMP': directory + '/ansible',
                         'ANSIBLE_REMOTE_TEMP': directory + '/remote'})
                self.assertEqual(result.returncode, expected, result.stdout + result.stderr)
                self.assertNotIn(value, result.stdout + result.stderr)
                if expected:
                    self.assertFalse(payload.exists())
                    continue
                self.assertNotIn(value, arguments.read_text())
                secret = json.loads(payload.read_text())
                self.assertEqual(secret['metadata'], {'name': 'private-registry', 'namespace': 'headlamp'})
                self.assertEqual(secret['type'], 'kubernetes.io/dockerconfigjson')
                auths = json.loads(secret['stringData']['.dockerconfigjson'])['auths']
                self.assertEqual(set(auths), {'registry1.dso.mil'})
                decoded = base64.b64decode(auths['registry1.dso.mil']['auth']).decode()
                self.assertEqual(decoded, 'fixture-user:' + value)
                self.assertNotIn(auths['registry1.dso.mil']['auth'], result.stdout + result.stderr)
