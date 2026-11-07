"""Offline tier policy and guarded activation renderer regressions."""
from copy import deepcopy
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
import yaml

ROOT = Path(__file__).resolve().parents[2]
PLAY = ROOT / 'configuration/ansible/longhorn-disk-activation-plan.yaml'


class TierTests(unittest.TestCase):
    def test_class_prerequisites_default_check_and_unreviewed_apply_never_call_api(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); marker = root / 'api-called'; fake = root / 'kubectl'
            fake.write_text('#!/bin/sh\ntouch "' + str(marker) + '"\nexit 99\n'); fake.chmod(0o700)
            env = dict(os.environ, PATH=d + os.pathsep + os.environ['PATH'],
                       ANSIBLE_LOCAL_TEMP=str(root/'local'), ANSIBLE_REMOTE_TEMP=str(root/'remote'))
            for flags, success in (([], True), (['--check', '-e', 'longhorn_tiers_apply=true'], True),
                                   (['-e', 'longhorn_tiers_apply=true'], False)):
                r = subprocess.run(['ansible-playbook', '-i', str(ROOT/'configuration/ansible/inventory.yaml'),
                    str(ROOT/'configuration/ansible/longhorn-tier-prerequisites.yaml'), '--limit', 'local', *flags],
                    env=env, text=True, capture_output=True, timeout=30)
                self.assertEqual(r.returncode == 0, success, r.stdout + r.stderr)
                self.assertFalse(marker.exists())

    def plan(self):
        result = []
        for index, capacity in enumerate((500000000001, 1000000000000), 1):
            node = 'worker-' + str(index)
            reserve = (capacity * 30 + 99) // 100
            disk_uuid = '11111111-2222-3333-4444-' + str(index).zfill(12)
            result.append(dict(node=node, disk_name='dedicated-t7', path='/mnt/test-t7',
                capacity_bytes=capacity, reserve_bytes=reserve, disk_uuid=disk_uuid,
                single_replica_excess=index == 2, snapshot={
                    'apiVersion': 'longhorn.io/v1beta2', 'kind': 'Node',
                    'metadata': {'name': node, 'namespace': 'longhorn-system', 'uid': 'fixture-' + node, 'resourceVersion': '42'},
                    'spec': {'allowScheduling': True, 'tags': ['existing-node-tag'], 'disks': {
                        'root': {'path': '/var/lib/longhorn', 'allowScheduling': True, 'tags': [], 'storageReserved': 123},
                        'dedicated-t7': {'path': '/mnt/test-t7', 'diskType': 'filesystem',
                            'allowScheduling': False, 'evictionRequested': False,
                            'storageReserved': reserve, 'tags': ['dedicated-storage']}}},
                    'status': {'diskStatus': {'dedicated-t7': {'diskUUID': disk_uuid,
                        'storageMaximum': capacity, 'storageScheduled': 0, 'scheduledReplica': {},
                        'conditions': [{'type': 'Ready', 'status': 'True'}]}}}}))
        return result

    def render(self, plan, reviewed=True, check=False, prior=False):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); out = root / 'out'; out.mkdir(mode=0o700)
            if prior:
                (out / 'worker-1.json').write_text('[]')
            inputs = root / 'inputs.yaml'
            inputs.write_text(yaml.safe_dump({'longhorn_activation_plan': plan,
                'longhorn_activation_output': str(out), 'longhorn_activation_reviewed': reviewed}))
            r = subprocess.run(['ansible-playbook', '-i', 'localhost,', str(PLAY), '-e', '@' + str(inputs)]
                               + (['--check'] if check else []), text=True, capture_output=True, timeout=30,
                               env=dict(os.environ, ANSIBLE_LOCAL_TEMP=str(root/'local'),
                                        ANSIBLE_REMOTE_TEMP=str(root/'remote'), KUBECONFIG='/dev/null'))
            return r, {p.name: json.loads(p.read_text()) for p in out.glob('*.json')}

    def test_patch_preserves_roots_and_tags_and_designates_one_excess_node(self):
        plan = self.plan(); r, files = self.render(plan)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        for item in plan:
            patch = files[item['node'] + '.json']
            self.assertEqual([x['op'] for x in patch[:3]], ['test'] * 3)
            self.assertEqual(patch[2]['value'], item['snapshot']['spec']['disks'])
            result = deepcopy(item['snapshot'])
            for op in patch:
                pieces = op['path'].lstrip('/').split('/')
                parent = result
                for key in pieces[:-1]: parent = parent[key]
                if op['op'] == 'test': self.assertEqual(parent[pieces[-1]], op['value'])
                else: parent[pieces[-1]] = op['value']
            self.assertEqual(result['spec']['disks']['root'], item['snapshot']['spec']['disks']['root'])
            self.assertEqual(result['status'], item['snapshot']['status'])
            self.assertTrue(result['spec']['disks']['dedicated-t7']['allowScheduling'])
            self.assertEqual(result['spec']['disks']['dedicated-t7']['storageReserved'], item['reserve_bytes'])
            self.assertEqual('excess-capacity' in result['spec']['tags'], item['single_replica_excess'])
            self.assertIn('existing-node-tag', result['spec']['tags'])

    def test_invalid_or_occupied_disks_produce_no_patches(self):
        for bad in ('uuid', 'reserve', 'capacity', 'ready', 'occupied', 'enabled', 'duplicate-excess', 'old-excess', 'wrong-excess', 'node-disabled'):
            plan = self.plan(); d = plan[1]; s = d['snapshot']['status']['diskStatus']['dedicated-t7']
            if bad == 'uuid': d['disk_uuid'] = 'aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee'
            elif bad == 'reserve': d['reserve_bytes'] -= 1
            elif bad == 'capacity': d['capacity_bytes'] += 100
            elif bad == 'ready': s['conditions'][0]['status'] = 'False'
            elif bad == 'occupied': s['storageScheduled'] = 1073741824
            elif bad == 'enabled': d['snapshot']['spec']['disks']['dedicated-t7']['allowScheduling'] = True
            elif bad == 'duplicate-excess': plan[0]['single_replica_excess'] = True
            elif bad == 'wrong-excess': plan[0]['single_replica_excess'] = True; plan[1]['single_replica_excess'] = False
            elif bad == 'node-disabled': d['snapshot']['spec']['allowScheduling'] = False
            else: plan[0]['snapshot']['spec']['tags'].append('excess-capacity')
            with self.subTest(bad=bad):
                r, files = self.render(plan)
                self.assertNotEqual(r.returncode, 0)
                self.assertEqual(files, {})

    def test_review_check_and_existing_artifact_gates(self):
        r, files = self.render(self.plan(), reviewed=False)
        self.assertNotEqual(r.returncode, 0); self.assertEqual(files, {})
        r, files = self.render(self.plan(), check=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr); self.assertEqual(files, {})
        r, files = self.render(self.plan(), prior=True)
        self.assertNotEqual(r.returncode, 0); self.assertEqual(files, {'worker-1.json': []})

    def test_tiers_are_nondefault_retained_v1_and_single_is_explicitly_placed(self):
        base = ROOT / 'configuration/packages/longhorn/dedicated'
        important = yaml.safe_load((base/'storageclass.yaml').read_text())
        single = yaml.safe_load((base/'storageclass-single-excess.yaml').read_text())
        for sc in (important, single):
            self.assertEqual(sc['metadata']['annotations']['storageclass.kubernetes.io/is-default-class'], 'false')
            self.assertEqual(sc['reclaimPolicy'], 'Retain')
            self.assertEqual(sc['volumeBindingMode'], 'WaitForFirstConsumer')
            self.assertTrue(sc['allowVolumeExpansion'])
            self.assertEqual(sc['parameters']['dataEngine'], 'v1')
            self.assertEqual(sc['parameters']['replicaAutoBalance'], 'disabled')
        self.assertEqual(important['parameters']['numberOfReplicas'], '2')
        self.assertEqual(important['parameters']['diskSelector'], 'dedicated-storage')
        self.assertEqual(important['parameters']['replicaSoftAntiAffinity'], 'disabled')
        self.assertEqual(single['parameters']['numberOfReplicas'], '1')
        self.assertEqual(single['parameters']['dataLocality'], 'disabled')
        self.assertEqual(single['parameters']['diskSelector'], 'dedicated-storage,excess-capacity')
        self.assertEqual(single['parameters']['nodeSelector'], 'excess-capacity')
        settings = yaml.safe_load((base.parent/'values.yaml').read_text())['packages']['longhorn']['values']['defaultSettings']
        self.assertFalse(settings['allowEmptyDiskSelectorVolume'])
        self.assertNotIn('allowEmptyNodeSelectorVolume', settings)
        quota = yaml.safe_load((ROOT/'clusters/local/longhorn-single-excess-quota.example.yaml').read_text())
        self.assertEqual(quota['metadata']['namespace'], 'UNCONFIGURED')
        self.assertEqual(quota['spec']['hard']['longhorn-single-excess.storageclass.storage.k8s.io/requests.storage'], '300Gi')
        for p in (ROOT/'clusters').glob('*/kustomization.yaml'):
            self.assert_no_dedicated_configuration(p.read_text())

    def assert_no_dedicated_configuration(self, text):
        # Comments describe unrelated TLS/key custody; only YAML selects storage.
        self.assertNotIn('dedicated', yaml.safe_dump(yaml.safe_load(text)))

    def test_root_storage_guard_ignores_comments_but_rejects_selection(self):
        self.assert_no_dedicated_configuration(
            '# Prepare dedicated TLS before selection\nresources: [../local]\n')
        for manifest in (
                'resources: [../../configuration/packages/longhorn/dedicated]\n',
                'patches: [{patch: "diskSelector: dedicated-storage"}]\n'):
            with self.subTest(manifest=manifest), self.assertRaises(AssertionError):
                self.assert_no_dedicated_configuration(manifest)


if __name__ == '__main__': unittest.main()
