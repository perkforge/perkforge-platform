"""Reusable rendered package fixtures; no test cases or live API access."""
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

class HeadlampFixture(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sources = Path(os.environ['PREFLIGHT_SOURCES_DIR'])
        cls.root = build(CLUSTER)
        cls.foundation = build(ROOT / 'configuration/packages/bigbang/foundation')
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
        cls.child_release = next(o for o in cls.outer if o['kind'] == 'HelmRelease' and o['metadata']['name'] == 'headlamp')
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


class IdentityFixture(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = Path(os.environ['PREFLIGHT_SOURCES_DIR'])
        cls.root = build(CLUSTER)
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

    def permitted(self, group, ns, resource, verb, api=''):
        # Offline contract model, not a Kubernetes authorizer. cluster-admin is
        # the built-in wildcard role; it is referenced, never redefined here.
        roles = {o['metadata']['name']: o for o in self.access if o['kind'] == 'ClusterRole'}
        roles['cluster-admin'] = {'rules': [{'apiGroups': ['*'], 'resources': ['*'], 'verbs': ['*']}]}
        for b in self.access:
            if b['kind'] not in ['RoleBinding', 'ClusterRoleBinding']:
                continue
            if b['kind'] == 'RoleBinding' and b['metadata']['namespace'] != ns:
                continue
            if not any(s['kind'] == 'Group' and s['name'] == group for s in b['subjects']):
                continue
            for rule in roles[b['roleRef']['name']]['rules']:
                if all(value in rule[key] or '*' in rule[key] for key, value in
                       [('apiGroups', api), ('resources', resource), ('verbs', verb)]):
                    return True
        return False
