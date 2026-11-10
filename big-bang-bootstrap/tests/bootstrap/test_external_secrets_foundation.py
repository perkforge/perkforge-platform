"""Real Ansible apply-path tests with synthetic public CRDs and a local CLI double."""
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
import yaml

ROOT = Path(__file__).resolve().parents[2]
PLAY = ROOT / 'configuration/ansible/external-secrets-prerequisites.yaml'
GUARD = ROOT / 'configuration/ansible/filter_plugins/external_secrets_foundation_guard.py'
spec = importlib.util.spec_from_file_location('eso_guard', GUARD)
guard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)


class OwnedComparison(unittest.TestCase):
    def test_ownership_and_authority_drift_are_rejected(self):
        desired = {'apiVersion': 'rbac.authorization.k8s.io/v1', 'kind': 'ClusterRole',
                   'metadata': {'name': 'fixture', 'labels': {'perkforge.io/owner': guard.OWNER}},
                   'rules': [{'apiGroups': [''], 'resources': ['secrets'], 'verbs': ['list', 'watch']}]}
        actual = copy.deepcopy(desired)
        actual['metadata'].update(uid='fixture', resourceVersion='9')
        self.assertTrue(guard.matches(actual, desired))
        for mutate in (lambda x: x['metadata']['labels'].clear(),
                       lambda x: x['rules'][0]['verbs'].append('get'),
                       lambda x: x['metadata'].update(deletionTimestamp='now'),
                       lambda x: x.update(aggregationRule={'clusterRoleSelectors': [{}]})):
            wrong = copy.deepcopy(actual)
            mutate(wrong)
            self.assertFalse(guard.matches(wrong, desired))


@unittest.skipUnless(shutil.which('ansible-playbook') and shutil.which('kubectl'), 'Ansible and kubectl kustomize required')
class FoundationApply(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.config = self.root / 'configuration'
        ansible = self.config / 'ansible'
        filters = ansible / 'filter_plugins'
        filters.mkdir(parents=True)
        shutil.copy(PLAY, ansible / PLAY.name)
        shutil.copy(GUARD, filters / GUARD.name)
        shutil.copy(PLAY.parent / 'verify-release.yaml', ansible / 'verify-release.yaml')
        package = self.config / 'external-secrets'
        package.mkdir()
        foundation = subprocess.check_output(['kubectl', 'kustomize', str(ROOT / 'configuration/external-secrets/prerequisites')], text=True)
        (self.root / 'foundation.yaml').write_text(foundation)
        self.foundation = [d for d in yaml.safe_load_all(foundation) if d]
        self.chart = self.root / 'chart'
        (self.chart / 'crds').mkdir(parents=True)
        (self.chart / 'Chart.yaml').write_text('version: 2.12.0-bb.0\n')
        crd = {'apiVersion': 'apiextensions.k8s.io/v1', 'kind': 'CustomResourceDefinition',
               'metadata': {'name': 'fixtures.eso.example.test'},
               'spec': {'group': 'eso.example.test', 'names': {'kind': 'Fixture', 'plural': 'fixtures'},
                        'scope': 'Namespaced', 'versions': [{'name': 'v1', 'served': True, 'storage': True,
                        'schema': {'openAPIV3Schema': {'type': 'object'}}}]}}
        bundle = yaml.safe_dump(crd)
        self.bundle_path = self.chart / 'crds/bundle.yaml'
        self.bundle_path.write_text(bundle)
        pin = {'package_version': '2.12.0-bb.0', 'crd_bundle_sha256': hashlib.sha256(bundle.encode()).hexdigest(), 'crd_count': 1}
        (package / 'source-pin.yaml').write_text(yaml.safe_dump(pin))
        self.desired_crd = copy.deepcopy(crd)
        self.desired_crd['metadata'].update(labels={'perkforge.io/owner': guard.OWNER}, annotations={guard.HASH_ANNOTATION: pin['crd_bundle_sha256']})
        (self.root / 'state.json').write_text('{}')
        (self.root / 'mode').write_text('normal')
        release = {'tag': 'v0.34.3', 'repository': 'perkforge/perkforge-platform', 'resolvedCommit': 'a' * 40}
        (self.root / 'release.json').write_text(json.dumps(release))
        values = {'external_secrets_foundation_apply': True,
                  'external_secrets_foundation_scope': 'external-secrets-foundation-v1',
                  'external_secrets_chart_directory': str(self.chart),
                  'config_tag': 'v0.34.3', 'config_release_evidence': str(self.root / 'release.json'),
                  'config_repository': 'https://github.com/perkforge/perkforge-platform.git',
                  'target_kubeconfig': str(self.root / 'synthetic-not-a-kubeconfig'),
                  'target_context': 'fixture', 'expected_cluster_uid': 'cluster-fixture',
                  'impact_profile': 'il2', 'deployment_environment': 'local'}
        self.values = self.root / 'values.json'
        self.values.write_text(json.dumps(values))
        (self.root / 'inventory.yaml').write_text('all:\n  children:\n    bootstrap_clusters:\n      hosts:\n        local:\n          ansible_connection: local\n')
        binary = self.root / 'bin'
        binary.mkdir()
        for name in ('kubectl', 'git', 'bash', 'gh'):
            target = binary / name
            shutil.copy(ROOT / 'tests/fixtures/external_secrets_foundation_cli.py', target)
            target.chmod(0o755)
        self.env = dict(os.environ, PATH=str(binary) + ':' + os.environ['PATH'],
                        ESO_FIXTURE=str(self.root), ANSIBLE_LOCAL_TEMP=str(self.root / 'ansible-tmp'),
                        KUBECONFIG='/dev/null')

    def tearDown(self):
        self.tmp.cleanup()

    def run_play(self, mode='normal'):
        (self.root / 'mode').write_text(mode)
        return subprocess.run(['ansible-playbook', '-i', str(self.root / 'inventory.yaml'),
                               str(self.config / 'ansible' / PLAY.name), '-e', '@' + str(self.values)],
                              env=self.env, text=True, capture_output=True, timeout=100)

    def calls(self):
        path = self.root / 'calls.jsonl'
        return [json.loads(x) for x in path.read_text().splitlines()] if path.exists() else []

    def assert_no_mutation(self, result):
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertFalse(any(c['tool'] == 'kubectl' and 'create' in c['args'] for c in self.calls()))

    def test_wrong_hash_release_checkout_dirty_target_refuse_before_apply(self):
        for mode in ('wrong_release', 'wrong_checkout', 'dirty', 'wrong_cluster', 'wrong_hash'):
            with self.subTest(mode=mode):
                (self.root / 'calls.jsonl').write_text('')
                original = self.bundle_path.read_text()
                if mode == 'wrong_hash':
                    self.bundle_path.write_text(original + '# tampered\n')
                result = self.run_play(mode)
                self.assert_no_mutation(result)
                if mode != 'wrong_cluster':
                    self.assertFalse(any(c['tool'] == 'kubectl' and 'get' in c['args'] for c in self.calls()))
                self.bundle_path.write_text(original)

    def test_success_and_exact_owned_repeat_make_no_second_apply(self):
        result = self.run_play()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        calls = self.calls()
        writes = [c for c in calls if c['tool'] == 'kubectl' and 'create' in c['args']]
        self.assertEqual(len(writes), len(self.foundation) + 1)
        first_apply = next(i for i, c in enumerate(calls) if c['tool'] == 'kubectl' and 'create' in c['args'])
        self.assertEqual(sum(c['tool'] == 'kubectl' and 'get' in c['args'] for c in calls[:first_apply]), len(self.foundation) + 2)
        (self.root / 'calls.jsonl').write_text('')
        result = self.run_play()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('changed=0', result.stdout)
        self.assertFalse(any(c['tool'] == 'kubectl' and 'create' in c['args'] for c in self.calls()))

    def test_readback_drift_stops_without_automatic_repair(self):
        result = self.run_play('readback_drift')
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('ESO foundation readback differs', result.stdout + result.stderr)
        self.assertFalse(any(c['tool'] == 'kubectl' and any(action in c['args']
                             for action in ('apply', 'patch', 'replace', 'delete')) for c in self.calls()))

    def test_concurrent_object_creation_fails_without_adoption(self):
        result = self.run_play('create_race')
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('AlreadyExists', result.stdout + result.stderr)
        self.assertEqual(json.loads((self.root / 'state.json').read_text()), {})
        creates = [c for c in self.calls() if c['tool'] == 'kubectl' and 'create' in c['args']]
        self.assertEqual(len(creates), 1)

    def test_unowned_or_drifting_objects_prevent_all_writes(self):
        role = next(x for x in self.foundation if x['kind'] == 'ClusterRole')
        cases = []
        unowned = copy.deepcopy(role)
        unowned['metadata']['labels'].clear()
        cases.append(unowned)
        broad = copy.deepcopy(role)
        broad['rules'][0]['verbs'].append('delete')
        cases.append(broad)
        no_manager = copy.deepcopy(self.desired_crd)
        cases.append(no_manager)
        wrong_schema = copy.deepcopy(self.desired_crd)
        wrong_schema['metadata']['managedFields'] = [{'manager': guard.CRD_MANAGER, 'operation': 'Apply'}]
        wrong_schema['spec']['versions'][0]['schema']['openAPIV3Schema']['description'] = 'unreviewed'
        cases.append(wrong_schema)
        for obj in cases:
            with self.subTest(kind=obj['kind'], obj=obj.get('rules')):
                key = '|'.join([obj['kind'], obj['metadata'].get('namespace', ''), obj['metadata']['name']])
                (self.root / 'state.json').write_text(json.dumps({key: obj}))
                (self.root / 'calls.jsonl').write_text('')
                self.assert_no_mutation(self.run_play())


if __name__ == '__main__':
    unittest.main()
