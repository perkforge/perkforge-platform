"""Run the real offline renderer with synthetic Longhorn metadata; no cluster."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
import yaml

ROOT = Path(__file__).resolve().parents[2]
PLAY = ROOT / 'configuration/ansible/longhorn-disk-plan.yaml'


class DedicatedDiskPlanTests(unittest.TestCase):
    def render(self, plan, check=False):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            out = root / 'output'
            out.mkdir(mode=0o700)
            inputs = root / 'inputs.yaml'
            inputs.write_text(yaml.safe_dump({'longhorn_disk_plan': plan,
                                             'longhorn_disk_output': str(out)}))
            result = subprocess.run(
                ['ansible-playbook', '-i', 'localhost,', str(PLAY), '-e', '@' + str(inputs)]
                + (['--check'] if check else []), capture_output=True, text=True,
                env={**os.environ, 'ANSIBLE_LOCAL_TEMP': str(root / 'tmp'),
                     'ANSIBLE_REMOTE_TEMP': str(root / 'remote-tmp'), 'KUBECONFIG': '/dev/null'}, timeout=30)
            return result, {p.name: json.loads(p.read_text()) for p in out.glob('*.json')}

    def plan(self):
        plan = yaml.safe_load((ROOT / 'clusters/local/longhorn-disks.example.yaml').read_text())['longhorn_disk_plan']
        for disk in plan:
            disk['snapshot'] = {
                'apiVersion': 'longhorn.io/v1beta2', 'kind': 'Node',
                'metadata': {'name': disk['node'], 'namespace': 'longhorn-system',
                             'uid': 'dummy-' + disk['node'], 'resourceVersion': '42'},
                'spec': {'disks': {'existing-root': {'path': '/var/lib/longhorn',
                                                    'allowScheduling': True}}}}
        return plan

    def test_additive_disabled_patches_preserve_existing_disks(self):
        plan = self.plan()
        result, files = self.render(plan)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(len(files), 2)
        for disk in plan:
            patch = files[disk['node'] + '.json']
            self.assertEqual([op['op'] for op in patch], ['test', 'test', 'test', 'add'])
            self.assertEqual(patch[2]['value'], disk['snapshot']['spec']['disks'])
            self.assertEqual(patch[3]['path'], '/spec/disks/dedicated-t7')
            self.assertEqual(patch[3]['value']['storageReserved'], disk['reserve_bytes'])
            self.assertFalse(patch[3]['value']['allowScheduling'])
            self.assertNotIn('diskUUID', patch[3]['value'])

    def test_refuses_missing_identity_conflict_and_invalid_reserve_before_output(self):
        for invalid in ('identity', 'conflict', 'reserve', 'duplicate', 'missing'):
            with self.subTest(invalid=invalid):
                plan = self.plan()
                if invalid == 'identity':
                    plan[1]['snapshot']['metadata']['name'] = 'control-1'
                elif invalid == 'conflict':
                    plan[1]['snapshot']['spec']['disks']['dedicated-t7'] = {'path': '/elsewhere'}
                elif invalid == 'reserve':
                    plan[1]['reserve_bytes'] = 0
                elif invalid == 'duplicate':
                    plan[1]['node'] = plan[0]['node']
                else:
                    plan[1]['snapshot'] = {}
                result, files = self.render(plan)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn('Validate all inputs' if invalid != 'duplicate' else 'Require explicit complete plan', result.stdout)
                self.assertNotIn('UNREACHABLE', result.stdout)
                self.assertEqual(files, {})

    def test_check_mode_creates_no_patch(self):
        result, files = self.render(self.plan(), check=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(files, {})

    def test_class_restricts_new_claims_to_tagged_two_worker_storage(self):
        sc = yaml.safe_load((ROOT / 'configuration/packages/longhorn/dedicated/storageclass.yaml').read_text())
        self.assertEqual(sc['parameters']['numberOfReplicas'], '2')
        self.assertEqual(sc['parameters']['diskSelector'], 'dedicated-storage')
        self.assertEqual(sc['parameters']['replicaSoftAntiAffinity'], 'disabled')
        self.assertEqual(sc['reclaimPolicy'], 'Retain')
        self.assertEqual(sc['volumeBindingMode'], 'WaitForFirstConsumer')
