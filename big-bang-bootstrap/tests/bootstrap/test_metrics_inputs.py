"""Real Ansible against synthetic CLI state; no real credentials or cluster access."""
import base64
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
PLAY = ROOT / 'configuration/ansible/metrics-inputs.yaml'
PASSWORD = 'synthetic-only-password-$-123456789'


class MetricsInputs(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        self.private = self.folder / 'private'
        self.private.mkdir(mode=0o700)
        for name, value in [('admin-username', 'fixture-admin'), ('admin-password', PASSWORD)]:
            path = self.private / name
            path.write_text(value)
            path.chmod(0o600)
        self.state = self.folder / 'state.json'
        self.state.write_text(json.dumps({'secrets': {}, 'calls': [], 'uid': 'expected-uid'}))
        self.bin = self.folder / 'bin'; self.bin.mkdir()
        self.play = self.folder / 'metrics-inputs.yaml'; shutil.copyfile(PLAY, self.play)
        # Mock only publication lookup; production always includes verify-release.yaml.
        (self.folder / 'verify-release.yaml').write_text('- ansible.builtin.set_fact:\n    config_release:\n      resolvedCommit: "' + 'a' * 40 + '"\n')
        (self.bin / 'git').write_text('#!/bin/sh\ncase "$*" in *rev-parse*) printf "%s\\n" aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa;; *status*) exit 0;; *) exit 99;; esac\n')
        (self.bin / 'git').chmod(0o700)
        script = '''#!/usr/bin/python3
import base64,json,os,sys
from pathlib import Path
p=Path(os.environ['METRICS_FAKE_STATE']);s=json.loads(p.read_text());args=sys.argv[1:]
def save():p.write_text(json.dumps(s))
if 'create' in args:
 doc=json.load(sys.stdin);dry='--dry-run=server' in args
 s['calls'].append(['dry-run' if dry else 'create',doc['metadata']['name']]);save()
 if s.get('reject_validation') and dry:sys.exit(1)
 if not dry:s['secrets'][doc['metadata']['name']]=doc;save()
 print('validated' if dry else 'created');sys.exit(0)
s['calls'].append(['get',args]);save()
if 'kube-system' in args:print(s['uid'])
elif 'namespace' in args:print(json.dumps({'metadata':{'labels':{'app.kubernetes.io/managed-by':'Ansible','pod-security.kubernetes.io/enforce':'privileged','pod-security.kubernetes.io/enforce-version':'v1.36'}}}))
elif 'flux-system' in args:
 auth=base64.b64encode(b'fixture:synthetic-registry-only').decode()
 data=base64.b64encode(json.dumps({'auths':{'registry1.dso.mil':{'auth':auth}}}).encode()).decode()
 print(json.dumps({'type':'kubernetes.io/dockerconfigjson','data':{'.dockerconfigjson':data}}))
else:
 name=args[args.index('secret')+1]
 if name in s['secrets']:print(json.dumps(s['secrets'][name]))
'''
        (self.bin / 'kubectl').write_text(script); (self.bin / 'kubectl').chmod(0o700)
        self.inventory = self.folder / 'inventory.yaml'
        self.inventory.write_text('all:\n  children:\n    bootstrap_clusters:\n      hosts:\n        local:\n          ansible_connection: local\n      vars:\n        deployment_environment: local\n        impact_profile: il2\n        target_kubeconfig: /synthetic/kubeconfig\n        target_context: synthetic\n        expected_cluster_uid: expected-uid\n')

    def run_play(self, apply=False, check=False):
        variables = {'metrics_inputs_apply': apply, 'metrics_private_dir': str(self.private)}
        env = {**os.environ, 'PATH': str(self.bin) + ':' + os.environ['PATH'], 'KUBECONFIG': '/dev/null',
               'METRICS_FAKE_STATE': str(self.state), 'ANSIBLE_LOCAL_TEMP': str(self.folder / 'ansible-temp'),
               'ANSIBLE_REMOTE_TEMP': str(self.folder / 'ansible-remote')}
        result = subprocess.run(['ansible-playbook', '-i', str(self.inventory), str(self.play), '-e', json.dumps(variables)] + (['--check'] if check else []), capture_output=True, text=True, env=env, timeout=60)
        self.assertNotIn(PASSWORD, result.stdout + result.stderr)
        self.assertNotIn('synthetic-registry-only', result.stdout + result.stderr)
        return result

    def mutations(self):
        return [x for x in json.loads(self.state.read_text())['calls'] if x[0] in ('create', 'dry-run')]

    def test_default_and_check_modes_read_no_inputs_or_api(self):
        shutil.rmtree(self.private)
        for apply, check in [(False, False), (True, True)]:
            result = self.run_play(apply, check)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(json.loads(self.state.read_text())['calls'], [])

    def test_create_is_prevalidated_redacted_and_repeat_changes_nothing(self):
        result = self.run_play(True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual([x[0] for x in self.mutations()], ['dry-run', 'dry-run', 'create', 'create'])
        s = json.loads(self.state.read_text()); s['calls'] = []; self.state.write_text(json.dumps(s))
        result = self.run_play(True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(self.mutations(), [])
        self.assertIn('changed=0', result.stdout)

    def test_wrong_cluster_refuses_before_private_input_reads(self):
        s = json.loads(self.state.read_text()); s['uid'] = 'wrong'; self.state.write_text(json.dumps(s))
        shutil.rmtree(self.private)
        self.assertNotEqual(self.run_play(True).returncode, 0)
        self.assertEqual(self.mutations(), [])
        self.assertEqual(len(json.loads(self.state.read_text())['calls']), 1)

    def test_unsafe_file_refuses_without_delivery(self):
        (self.private / 'admin-password').chmod(0o644)
        self.assertNotEqual(self.run_play(True).returncode, 0)
        self.assertEqual(self.mutations(), [])

    def test_existing_unowned_credential_is_never_adopted_or_rotated(self):
        result = self.run_play(True); self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        s = json.loads(self.state.read_text()); s['secrets']['grafana-admin']['metadata']['labels'] = {}; s['calls'] = []; self.state.write_text(json.dumps(s))
        self.assertNotEqual(self.run_play(True).returncode, 0)
        self.assertEqual(self.mutations(), [])

    def test_server_validation_failure_creates_nothing(self):
        s = json.loads(self.state.read_text()); s['reject_validation'] = True; self.state.write_text(json.dumps(s))
        self.assertNotEqual(self.run_play(True).returncode, 0)
        self.assertTrue(self.mutations())
        self.assertFalse(any(x[0] == 'create' for x in self.mutations()))

    def test_owned_credential_with_changed_password_is_never_rotated(self):
        result = self.run_play(True); self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        s = json.loads(self.state.read_text()); s['calls'] = []; self.state.write_text(json.dumps(s))
        changed = 'synthetic-changed-password-123456789'
        (self.private / 'admin-password').write_text(changed)
        result = self.run_play(True)
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn(changed, result.stdout + result.stderr)
        self.assertEqual(self.mutations(), [])
