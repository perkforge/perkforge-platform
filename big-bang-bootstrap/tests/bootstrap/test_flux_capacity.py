"""Offline optional capacity overlay preservation against pinned Flux manifests."""
import copy
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
import yaml

ROOT = Path(__file__).resolve().parents[2]

class FluxCapacity(unittest.TestCase):
    def test_opt_in_composition_and_refusal(self):
        sources = Path(os.environ['PREFLIGHT_SOURCES_DIR'])
        with tempfile.TemporaryDirectory() as directory:
            p = Path(directory)
            (p/'base').mkdir()
            shutil.copytree(sources/'bigbang/base/flux', p/'base/flux')
            def render(name):
                raw = subprocess.check_output(['kubectl', 'kustomize', str(p/'base'/name)], env={**os.environ, 'KUBECONFIG': '/dev/null'})
                return {(o['kind'], o.get('metadata', {}).get('namespace'), o['metadata']['name']): o for o in yaml.safe_load_all(raw) if o}
            baseline = render('flux')
            def run(values):
                play = [{'hosts': 'localhost', 'connection': 'local', 'gather_facts': False,
                         'vars': {'flux_checkout': directory, **values},
                         'tasks': [{'ansible.builtin.include_tasks': str(ROOT/'configuration/ansible/prepare-flux.yaml')},
                                   {'ansible.builtin.debug': {'var': 'flux_manifest_path'}}]}]
                file = p/'test.yaml'; file.write_text(yaml.safe_dump(play))
                return subprocess.run(['ansible-playbook', '-i', 'localhost,', str(file)], capture_output=True, text=True,
                                      env={**os.environ, 'KUBECONFIG': '/dev/null'})
            initial = run({})
            self.assertEqual(initial.returncode, 0, initial.stderr)
            self.assertFalse((p/'base/perkforge-flux-capacity').exists())
            settings = {'flux_helm_capacity_overlay': True, 'flux_helm_cpu_request_millicores': 500,
                        'flux_helm_node_selector': {'kubernetes.io/os': 'linux', 'storage.perkforge.io/worker': 'true'}}
            for placement in ({}, {'node-role.kubernetes.io/control-plane': ''}):
                with self.subTest(placement=placement):
                    result = run({**settings, 'flux_kustomize_node_selector': placement})
                    self.assertEqual(result.returncode, 0, result.stdout+result.stderr)
                    actual = render('perkforge-flux-capacity')
                    expected = copy.deepcopy(baseline)
                    spec = expected[('Deployment', 'flux-system', 'helm-controller')]['spec']
                    spec['strategy'] = {'type': 'Recreate'}
                    spec['template']['spec']['nodeSelector'] = settings['flux_helm_node_selector']
                    next(c for c in spec['template']['spec']['containers'] if c['name']=='manager')['resources']['requests']['cpu'] = '500m'
                    if placement:
                        expected[('Deployment', 'flux-system', 'kustomize-controller')]['spec']['template']['spec']['nodeSelector'].update(placement)
                    self.assertEqual(expected, actual)
                    self.assertEqual(baseline, render('flux'))
            for bad in ({'flux_helm_cpu_request_millicores': 0}, {'flux_helm_cpu_request_millicores': 901},
                        {'flux_helm_cpu_request_millicores': '500m'}, {'flux_helm_node_selector': {}},
                        {'flux_helm_node_selector': {'kubernetes.io/os': 'windows'}}):
                self.assertNotEqual(run({**settings, **bad}).returncode, 0)
            disabled = run({'flux_helm_capacity_overlay': False})
            self.assertEqual(disabled.returncode, 0, disabled.stdout+disabled.stderr)
            self.assertIn(str(p/'base/flux'), disabled.stdout)
