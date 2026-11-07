"""Real Ansible against local CLI fixtures; never a cluster or real credentials."""
import copy
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
import yaml

ROOT = Path(__file__).resolve().parents[2]
ANSIBLE = ROOT / 'configuration/ansible'
SHA = 'a' * 40
CLUSTER_UID = '00000000-0000-0000-0000-000000000001'
OPERATOR_UID = '00000000-0000-0000-0000-000000000002'

CLI = r'''#!/usr/bin/python3
import base64,json,os,sys
from pathlib import Path
root=Path(os.environ['HARBOR_FIXTURE'])
config=json.loads((root/'fixture.json').read_text())
args=sys.argv[1:];tool=Path(sys.argv[0]).name
with (root/'calls.jsonl').open('a') as f:f.write(json.dumps([tool,*args])+'\n')
sha='a'*40
if tool=='git':
 if 'ls-remote' in args:print(sha+'\trefs/tags/v0.99.0')
 elif 'rev-parse' in args:print(config.get('checkout',sha))
 elif 'status' in args:print(config.get('dirty',''),end='')
 else:sys.exit(91)
 sys.exit(0)
if tool=='gh':
 if args[:2]==['release','view']:print('v0.99.0\tfalse\tfalse')
 elif args[0]=='api' and '/commits/' in args[1]:print(sha)
 elif args[0]=='api' and '/contents/' in args[1]:
  print(base64.b64encode(b'commonAnnotations:\n  platform.perkforge.io/cluster: local\n  platform.perkforge.io/environment: local\n  platform.perkforge.io/profile: il2\n').decode())
 else:sys.exit(92)
 sys.exit(0)
if args[:1]==['--kubeconfig']:args=args[4:]
state=json.loads((root/'state.json').read_text())
if args[:2]==['config','view']:print(config.get('api','https://synthetic.invalid:6443'));sys.exit(0)
if args[:3]==['get','namespace','kube-system']:print(config.get('cluster_uid','00000000-0000-0000-0000-000000000001'));sys.exit(0)
if args[:3]==['get','deployment','platform-cnpg']:print(json.dumps(config['operator']));sys.exit(0)
def key(kind,name,namespace):return kind+'/'+namespace+'/'+name
if args[0]=='get':
 kind,name=args[1:3];namespace=args[args.index('-n')+1] if '-n' in args else ''
 obj=state.get(key(kind,name,namespace))
 if obj:print(json.dumps(obj))
 elif '--ignore-not-found' not in args:sys.exit(44)
 sys.exit(0)
if args==['create','-f','-']:
 obj=json.load(sys.stdin);meta=obj['metadata'];k=key(obj['kind'],meta['name'],meta.get('namespace',''))
 count=len(state)
 if k in state:sys.exit(45)
 if config.get('fail_at')==count+1:sys.exit(46)
 meta['uid']='00000000-0000-0000-0001-'+str(count+1).zfill(12)
 state[k]=obj;(root/'state.json').write_text(json.dumps(state))
 with (root/'writes.jsonl').open('a') as f:f.write(json.dumps(obj)+'\n')
 if config.get('uncertain_at')==count+1:sys.exit(47)
 print('created');sys.exit(0)
sys.exit(93)
'''


def identity(obj):
    return obj['kind'] + '/' + obj['metadata'].get('namespace', '') + '/' + obj['metadata']['name']


class HarborFoundation(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='harbor-foundation-fixture-')
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name)
        self.repo = self.path / 'repo'
        self.ansible = self.repo / 'big-bang-bootstrap/configuration/ansible'
        for relative in ('harbor-prerequisites.yaml', 'inventory.yaml', 'verify-release.yaml',
                         'tasks/harbor-foundation-create.yaml', 'filter_plugins/harbor_foundation_guard.py'):
            target = self.ansible / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ANSIBLE / relative, target)
        for relative in ('harbor/data-services/prerequisites/installer.yaml',
                         'harbor/data-services/prerequisites/cnpg.yaml', 'harbor/prerequisites/installer.yaml',
                         'harbor/prerequisites/gitops.yaml', 'cloudnative-pg/values.yaml'):
            source = ROOT / 'configuration/packages' / relative
            target = self.ansible.parent / 'packages' / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
        (self.repo / 'scripts').mkdir()
        shutil.copy2(ROOT.parent / 'scripts/verify-release-ref.sh', self.repo / 'scripts')
        self.bin = self.path / 'bin'; self.bin.mkdir()
        for name in ('git', 'gh', 'kubectl'):
            executable = self.bin / name; executable.write_text(CLI); executable.chmod(0o700)
        values = yaml.safe_load((ROOT / 'configuration/packages/cloudnative-pg/values.yaml').read_text())
        self.operator = {
            'metadata': {'uid': OPERATOR_UID, 'generation': 1,
                         'labels': {'app.kubernetes.io/managed-by': 'Helm', 'helm.sh/chart': 'cloudnative-pg-0.29.1'},
                         'annotations': {'meta.helm.sh/release-name': 'platform-cnpg', 'meta.helm.sh/release-namespace': 'cnpg-system'}},
            'spec': {'replicas': 1, 'template': {'spec': {'serviceAccountName': 'platform-cnpg', 'containers': [
                {'name': 'manager', 'image': values['image']['repository'] + ':' + values['image']['tag'],
                 'env': [{'name': 'WATCH_NAMESPACE', 'value': 'gitlab,tenant-home-nextcloud'}]}]}}},
            'status': {'readyReplicas': 1, 'observedGeneration': 1}}
        self.config = {'operator': self.operator}
        self.state = {}
        self.save()
        kubeconfig = self.path / 'kubeconfig'; kubeconfig.write_text('synthetic fixture only'); kubeconfig.chmod(0o600)
        release = self.path / 'release.json'; release.write_text(json.dumps({'repository': 'perkforge/perkforge-platform', 'tag': 'v0.99.0', 'resolvedCommit': SHA}))
        self.params = {'harbor_foundation_apply': True, 'harbor_foundation_scope': 'harbor-foundation-v1',
                       'harbor_expected_api': 'https://synthetic.invalid:6443', 'harbor_expected_operator_uid': OPERATOR_UID,
                       'target_context': 'synthetic', 'expected_cluster_uid': CLUSTER_UID, 'target_kubeconfig': str(kubeconfig),
                       'config_tag': 'v0.99.0', 'config_release_evidence': str(release)}
        self.desired = []
        for filename in ('installer.yaml', 'cnpg.yaml'):
            self.desired += list(yaml.safe_load_all((ROOT / 'configuration/packages/harbor/data-services/prerequisites' / filename).read_text()))

        for filename in ('installer.yaml', 'gitops.yaml'):
            self.desired += [o for o in yaml.safe_load_all((ROOT / 'configuration/packages/harbor/prerequisites' / filename).read_text()) if o and o['kind'] != 'Namespace']

    def save(self):
        (self.path / 'fixture.json').write_text(json.dumps(self.config))
        (self.path / 'state.json').write_text(json.dumps(self.state))

    def calls(self):
        path = self.path / 'calls.jsonl'
        return [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []

    def writes(self):
        path = self.path / 'writes.jsonl'
        return [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []

    def run_play(self, changes=None, check=False):
        params = {**self.params, **(changes or {})}
        extra = self.path / 'params.json'; extra.write_text(json.dumps(params))
        command = ['ansible-playbook', '-i', str(self.ansible / 'inventory.yaml'), str(self.ansible / 'harbor-prerequisites.yaml'), '-e', '@' + str(extra)]
        if check: command.append('--check')
        return subprocess.run(command, capture_output=True, text=True, timeout=90, env={
            **os.environ, 'PATH': str(self.bin) + ':' + os.environ['PATH'], 'HARBOR_FIXTURE': str(self.path),
            'KUBECONFIG': '/dev/null', 'ANSIBLE_LOCAL_TEMP': str(self.path / 'ansible-local'),
            'ANSIBLE_REMOTE_TEMP': str(self.path / 'ansible-remote'), 'ANSIBLE_NOCOLOR': '1'})

    def test_default_and_check_modes_contact_nothing(self):
        for params, check in [({'harbor_foundation_apply': False}, False), ({}, True)]:
            result = self.run_play(params, check)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertFalse(self.calls())

    def test_scope_release_checkout_and_file_guards_precede_api_contact(self):
        for params, fixture in [({'harbor_foundation_scope': 'UNAPPROVED'}, {}),
                                ({'config_tag': 'main'}, {}), ({}, {'dirty': ' M source.yaml\n'}),
                                ({}, {'checkout': 'b' * 40})]:
            with self.subTest(params=params, fixture=fixture):
                self.config.update(fixture); self.save()
                result = self.run_play(params)
                self.assertNotEqual(result.returncode, 0)
                self.assertFalse([x for x in self.calls() if x[0] == 'kubectl'])
                self.config = {'operator': self.operator}
        Path(self.params['target_kubeconfig']).chmod(0o644)
        result = self.run_play()
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse([x for x in self.calls() if x[0] == 'kubectl'])

    def test_target_and_operator_drift_fail_before_creation(self):
        variants = [{'api': 'https://wrong.invalid:6443'}, {'cluster_uid': 'wrong'},
                    {'operator': {**self.operator, 'metadata': {**self.operator['metadata'], 'uid': 'wrong'}}}]
        changed = copy.deepcopy(self.operator)
        changed['spec']['template']['spec']['containers'][0]['env'][0]['value'] = 'gitlab'
        variants.append({'operator': changed})
        changed = copy.deepcopy(self.operator); changed['status']['readyReplicas'] = 0
        variants.append({'operator': changed})
        for fixture in variants:
            with self.subTest(fixture=fixture):
                self.config = {'operator': self.operator, **fixture}; self.save()
                result = self.run_play()
                self.assertNotEqual(result.returncode, 0)
                self.assertFalse(self.writes())

    def test_foreign_or_terminating_objects_refuse_before_first_write(self):
        for kind in ('Namespace', 'Role', 'RoleBinding', 'ServiceAccount'):
            obj = copy.deepcopy(next(o for o in self.desired if o['kind'] == kind))
            obj['metadata']['labels']['perkforge.io/owner'] = 'foreign'
            self.state = {identity(obj): obj}; self.save()
            result = self.run_play()
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(self.writes())
        obj = copy.deepcopy(self.desired[0]); obj['metadata']['deletionTimestamp'] = '2026-01-01T00:00:00Z'
        self.state = {identity(obj): obj}; self.save()
        result = self.run_play()
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.writes())

    def test_create_exact_thirteen_and_repeat_without_changes(self):
        result = self.run_play()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(len(self.writes()), 13)
        self.assertEqual({identity(o) for o in self.writes()}, {identity(o) for o in self.desired})
        state_before = (self.path / 'state.json').read_text()
        result = self.run_play()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('changed=0', result.stdout)
        self.assertEqual(len(self.writes()), 13)
        self.assertEqual((self.path / 'state.json').read_text(), state_before)
        self.assertFalse(any('patch' in call or 'apply' in call or 'delete' in call for call in self.calls()))

    def test_failed_or_uncertain_create_stops_and_resumes_without_recreation(self):
        for mode, expected in [('fail_at', 3), ('uncertain_at', 4)]:
            with self.subTest(mode=mode):
                self.state = {}; self.config = {'operator': self.operator, mode: 4}; self.save()
                (self.path / 'writes.jsonl').unlink(missing_ok=True)
                result = self.run_play()
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(len(self.writes()), expected)
                before = json.loads((self.path / 'state.json').read_text())
                self.config = {'operator': self.operator}
                (self.path / 'fixture.json').write_text(json.dumps(self.config))
                result = self.run_play()
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertEqual(len(self.writes()), 13)
                after = json.loads((self.path / 'state.json').read_text())
                self.assertTrue(all(after[k] == value for k, value in before.items()))

    def test_role_and_token_mount_drift_are_not_adopted(self):
        for kind, mutation in [('Role', lambda o: o['rules'][0]['verbs'].append('escalate')),
                               ('RoleBinding', lambda o: o['subjects'][0].update(name='foreign')),
                               ('ServiceAccount', lambda o: o.update(automountServiceAccountToken=True))]:
            obj = copy.deepcopy(next(o for o in self.desired if o['kind'] == kind))
            mutation(obj); self.state = {identity(obj): obj}; self.save()
            result = self.run_play()
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(self.writes())
