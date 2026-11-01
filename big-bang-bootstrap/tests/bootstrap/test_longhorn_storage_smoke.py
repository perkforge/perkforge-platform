"""Offline checks for the scoped storage smoke; never contacts a cluster."""
from copy import deepcopy
import importlib.util
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

from jinja2 import Environment
import yaml

ROOT = Path(__file__).resolve().parents[2]
ANSIBLE = ROOT / 'configuration/ansible'
SPEC = importlib.util.spec_from_file_location('storage_verifier', ANSIBLE / 'files/verify-longhorn-smoke.py')
VERIFIER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VERIFIER)


class LonghornStorageSmokeTests(unittest.TestCase):
    def test_default_and_check_mode_cannot_call_kubernetes(self):
        with tempfile.TemporaryDirectory() as directory:
            p = Path(directory)
            executable = p / 'kubectl'
            executable.write_text('#!/bin/sh\necho unexpected > "$API_MARKER"\nexit 99\n')
            executable.chmod(0o700)
            env = {**os.environ, 'PATH': str(p) + os.pathsep + os.environ['PATH'],
                   'API_MARKER': str(p / 'api-called'), 'ANSIBLE_LOCAL_TEMP': str(p / 'ansible-tmp')}
            base = ['ansible-playbook', '-i', str(ANSIBLE / 'inventory.yaml'),
                    str(ANSIBLE / 'longhorn-storage-smoke.yaml'), '--limit', 'local']
            for flags in [[], ['--check', '-e', 'storage_test_apply=true']]:
                result = subprocess.run(base + flags, env=env, text=True, capture_output=True, timeout=30)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertFalse((p / 'api-called').exists())
                self.assertIn('changed=0', result.stdout)

    def test_real_templates_are_nonprivileged_and_scheduler_placed(self):
        render = Environment().from_string((ANSIBLE / 'fixtures/longhorn-smoke-pod.yaml.j2').read_text())
        pod = yaml.safe_load(render.render(storage_test_namespace='pf-longhorn-smoke-example', storage_stage={'worker': 'worker-2'}))
        spec = pod['spec']; container = spec['containers'][0]
        self.assertNotIn('nodeName', spec)
        self.assertEqual(spec['nodeSelector']['kubernetes.io/hostname'], 'worker-2')
        self.assertFalse(spec['automountServiceAccountToken'])
        self.assertFalse(container['securityContext']['allowPrivilegeEscalation'])
        self.assertTrue(container['securityContext']['readOnlyRootFilesystem'])
        self.assertEqual(container['securityContext']['capabilities']['drop'], ['ALL'])
        self.assertTrue(spec['securityContext']['runAsNonRoot'])
        self.assertNotEqual(spec['securityContext']['runAsUser'], 0)
        self.assertEqual(spec['securityContext']['seccompProfile']['type'], 'RuntimeDefault')
        self.assertNotIn('hostPath', str(spec['volumes']))
        self.assertIn('@sha256:', container['image'])
        foundation = list(yaml.safe_load_all(Environment().from_string(
            (ANSIBLE / 'fixtures/longhorn-smoke-foundation.yaml.j2').read_text()).render(storage_test_namespace='pf-longhorn-smoke-example')))
        self.assertEqual([o['kind'] for o in foundation], ['Namespace', 'PersistentVolumeClaim'])
        self.assertEqual(foundation[0]['metadata']['labels']['pod-security.kubernetes.io/enforce'], 'restricted')
        self.assertEqual(foundation[1]['spec']['resources']['requests']['storage'], '1Gi')
        self.assertEqual(foundation[1]['spec']['storageClassName'], 'longhorn')

    def test_positive_health_and_meaningful_replica_failures(self):
        volume = {'metadata': {'name': 'synthetic'}, 'spec': {'numberOfReplicas': 2},
                  'status': {'state': 'attached', 'robustness': 'healthy', 'currentNodeID': 'worker-2'}}
        replicas = [{'spec': {'volumeName': 'synthetic', 'nodeID': worker, 'healthyAt': '2026-01-01T00:00:00Z', 'failedAt': ''},
                     'status': {'currentState': 'running'}} for worker in ['worker-1', 'worker-2']]
        engines = [{'spec': {'volumeName': 'synthetic'}, 'status': {'currentState': 'running', 'replicaModeMap': {'one': 'RW', 'two': 'RW'}}}]
        self.assertTrue(VERIFIER.replica_health(volume, replicas, engines, 'worker-2'))
        self.assertFalse(VERIFIER.replica_health(volume, replicas, engines, 'worker-1'))
        for field, value in [('nodeID', 'worker-1'), ('healthyAt', ''), ('failedAt', '2026-01-02T00:00:00Z')]:
            changed = deepcopy(replicas); changed[1]['spec'][field] = value
            self.assertFalse(VERIFIER.replica_health(volume, changed, engines, 'worker-2'))
        changed = deepcopy(engines); changed[0]['status']['replicaModeMap']['two'] = 'WO'
        self.assertFalse(VERIFIER.replica_health(volume, replicas, changed, 'worker-2'))
        changed = deepcopy(volume); changed['status']['robustness'] = 'degraded'
        self.assertFalse(VERIFIER.replica_health(changed, replicas, engines, 'worker-2'))
        changed['spec']['numberOfReplicas'] = 1
        with self.assertRaisesRegex(ValueError, 'replica count drift'):
            VERIFIER.replica_health(changed, replicas, engines, 'worker-2')
