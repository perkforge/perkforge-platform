"""Check local-only tuning, real assembly and unchanged dev/security contracts."""
import copy
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

import yaml

from flux_render import render_flux
from render_helpers import build

ROOT = Path(__file__).resolve().parents[1]
REPOSITORY = ROOT.parent


def identity(obj):
    return obj['kind'], obj['metadata'].get('namespace', ''), obj['metadata']['name']


class LocalProfileTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sources = Path(os.environ['PREFLIGHT_SOURCES_DIR'])
        cls.pinned = build(cls.sources / 'bigbang/base/flux')
        cls.tiny = render_flux(cls.sources, ROOT / 'examples', 'local-tiny')

    def test_flux_only_changes_resources_and_hostname_placement(self):
        pinned = {identity(obj): copy.deepcopy(obj) for obj in self.pinned}
        tiny = {identity(obj): copy.deepcopy(obj) for obj in self.tiny}
        self.assertEqual(pinned.keys(), tiny.keys())
        for key in pinned:
            if key[0] == 'Deployment':
                for objects in (pinned, tiny):
                    spec = objects[key]['spec']['template']['spec']
                    spec.get('nodeSelector', {}).pop('kubernetes.io/hostname', None)
                    for container in spec['containers']:
                        if container['name'] == 'manager':
                            container.pop('resources')
            self.assertEqual(pinned[key], tiny[key], key)
        nodes = {obj['metadata']['name']: obj['spec']['template']['spec']['nodeSelector']['kubernetes.io/hostname']
                 for obj in self.tiny if obj['kind'] == 'Deployment'}
        self.assertEqual(nodes, {'source-controller': 'cks-control', 'helm-controller': 'cks-worker',
                                'kustomize-controller': 'cks-worker', 'notification-controller': 'cks-worker'})

    def test_dev_build_and_pinned_flux_equal_published_baseline(self):
        evidence = json.loads((ROOT / 'tests/fixtures/platform-v0.2.0.json').read_text())
        self.assertEqual(subprocess.check_output(['git', '-C', str(REPOSITORY), 'rev-parse', 'v0.2.0^{commit}'], text=True).strip(), evidence['resolvedCommit'])
        archive = subprocess.check_output(['git', '-C', str(REPOSITORY), 'archive',
                                          'v0.2.0', 'local-lab-big-bang/examples'])
        with tempfile.TemporaryDirectory() as directory:
            subprocess.run(['tar', '-xf', '-', '-C', directory], input=archive, check=True)
            old = build(Path(directory) / 'local-lab-big-bang/examples/clusters/dev')
            new = build(ROOT / 'examples/clusters/dev')
            # The common enrollment dependency advances; dev workloads/Flux stay identical.
            for objects, expected in [(old, 'v0.1.1'), (new, 'v0.4.0')]:
                source = next(o for o in objects if o['kind'] == 'GitRepository' and o['metadata']['name'] == 'tenant-enrollments')
                self.assertEqual(source['spec']['ref'], {'tag': expected})
                source['spec']['ref'] = {'tag': 'DEPENDENCY-COMPARED-SEPARATELY'}
            self.assertEqual(old, new)
        self.assertEqual(render_flux(self.sources, ROOT / 'examples', 'pinned'), self.pinned)

    def test_disabled_walkthrough_and_reject_tiny_for_dev_before_api(self):
        for target, extra, expected in [('local', [], 0), ('dev', ['-e', 'flux_resource_profile=local-tiny'], 2)]:
            with tempfile.TemporaryDirectory() as directory:
                result = subprocess.run(['ansible-playbook', '-i', str(ROOT / 'examples/ansible/inventory.yaml'),
                    str(ROOT / 'examples/ansible/bootstrap.yaml'), '--limit', target, *extra],
                    text=True, capture_output=True,
                    env={**os.environ, 'ANSIBLE_LOCAL_TEMP': directory, 'ANSIBLE_NOCOLOR': '1'})
                self.assertEqual(result.returncode, expected, result.stdout + result.stderr)
                if not expected:
                    self.assertIn('changed=0', result.stdout)
                    self.assertNotIn('Create temporary build directory', result.stdout)
                else:
                    self.assertNotIn('Verify a published configuration release', result.stdout)
