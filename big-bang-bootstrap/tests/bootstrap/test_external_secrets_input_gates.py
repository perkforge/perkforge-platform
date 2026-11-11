"""Exercise real top-level ESO release/checkout/UID gates using isolated CLIs."""
import base64
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
import yaml

ROOT = Path(__file__).resolve().parents[2]


class EnabledInputGates(unittest.TestCase):
    def test_wrong_release_dirty_checkout_head_and_uid_stop_before_secret_reads(self):
        with tempfile.TemporaryDirectory() as directory:
            tmp = Path(directory)
            repo = tmp / 'repository'
            ansible = repo / 'big-bang-bootstrap/configuration/ansible'
            shutil.copytree(ROOT / 'configuration/ansible', ansible)
            shutil.copytree(ROOT / 'configuration/external-secrets/prerequisites',
                            ansible.parent / 'external-secrets/prerequisites')
            (repo / 'scripts').mkdir()
            shutil.copy(ROOT.parent / 'scripts/verify-release-ref.sh', repo / 'scripts')
            binary = tmp / 'bin'; binary.mkdir()
            calls = tmp / 'calls.json'; calls.write_text('[]')
            namespace = next(yaml.safe_load_all((ROOT / 'configuration/external-secrets/prerequisites/foundation.yaml').read_text()))
            secret = {'apiVersion': 'v1', 'kind': 'Secret', 'type': 'kubernetes.io/dockerconfigjson',
                      'data': {'.dockerconfigjson': base64.b64encode(json.dumps({'auths': {
                          'registry1.dso.mil': {'auth': base64.b64encode(b'test:synthetic-only').decode()}}}).encode()).decode()}}
            entry = base64.b64encode(yaml.safe_dump({'commonAnnotations': {
                'platform.perkforge.io/cluster': 'local', 'platform.perkforge.io/environment': 'local',
                'platform.perkforge.io/profile': 'il2'}}).encode()).decode()
            script = '''#!/usr/bin/env python3
import json, os, sys
from pathlib import Path
a = sys.argv[1:]; tool = Path(sys.argv[0]).name; mode = os.environ['ESO_GATE_MODE']; sha = 'a' * 40
if tool == 'gh':
 if a[:2] == ['release', 'view']: print('v1.2.3\\t' + ('true' if mode == 'release' else 'false') + '\\tfalse')
 elif a[0] == 'api' and '/commits/' in a[1]: print(sha)
 elif a[0] == 'api' and '/contents/' in a[1]: print(os.environ['ESO_GATE_ENTRY'])
 else: raise SystemExit('Unexpected gh')
elif tool == 'git':
 if a[0] == 'ls-remote': print(('b' * 40 if mode == 'tag' else sha) + '\\trefs/tags/v1.2.3')
 elif a[-2:] == ['rev-parse', 'HEAD']: print('b' * 40 if mode == 'head' else sha)
 elif a[-2:] == ['status', '--porcelain']: print(' M dirty' if mode == 'dirty' else '')
 else: raise SystemExit('Unexpected git')
elif tool == 'kubectl':
 assert a[:4] == ['--kubeconfig', '/synthetic/kubeconfig', '--context', 'fixture']
 a = a[4:]; p = Path(os.environ['ESO_GATE_CALLS']); calls = json.loads(p.read_text()); calls.append(a); p.write_text(json.dumps(calls))
 if a[:3] == ['get', 'namespace', 'kube-system']: print('wrong-cluster' if mode == 'uid' else 'fixture-uid')
 elif a[:3] == ['get', 'namespace', 'external-secrets']: print(os.environ['ESO_GATE_NAMESPACE'])
 elif a[:5] == ['-n', 'flux-system', 'get', 'secret', 'private-registry']: print(os.environ['ESO_GATE_SECRET'])
 elif a[:5] == ['-n', 'external-secrets', 'get', 'secret', 'private-registry']:
  state = Path(os.environ['ESO_GATE_OBJECT'])
  if state.exists(): print(state.read_text())
  else: assert '--ignore-not-found' in a
 elif a[0] == 'create':
  obj = json.load(sys.stdin)
  if '--dry-run=server' not in a: Path(os.environ['ESO_GATE_OBJECT']).write_text(json.dumps(obj))
  print('created')
 else: raise SystemExit('Unexpected kubectl')
else: raise SystemExit('Unexpected tool')
'''
            for name in ('git', 'gh', 'kubectl'):
                path = binary / name; path.write_text(script); path.chmod(0o700)
            evidence = tmp / 'release.json'
            evidence.write_text(json.dumps({'repository': 'perkforge/perkforge-platform', 'tag': 'v1.2.3', 'resolvedCommit': 'a' * 40}))
            inventory = tmp / 'inventory.yaml'
            inventory.write_text(yaml.safe_dump({'all': {'children': {'bootstrap_clusters': {'hosts': {'local': {
                'ansible_connection': 'local', 'deployment_environment': 'local', 'impact_profile': 'il2',
                'target_kubeconfig': '/synthetic/kubeconfig', 'target_context': 'fixture', 'expected_cluster_uid': 'fixture-uid',
                'config_repository': 'https://github.com/perkforge/perkforge-platform.git', 'config_tag': 'v1.2.3',
                'config_release_evidence': str(evidence)}}}}}}))
            env = dict(os.environ, PATH=str(binary) + ':' + os.environ['PATH'], KUBECONFIG='/dev/null',
                       ANSIBLE_LOCAL_TEMP=str(tmp / 'local'), ANSIBLE_REMOTE_TEMP=str(tmp / 'remote'),
                       ESO_GATE_CALLS=str(calls), ESO_GATE_ENTRY=entry, ESO_GATE_NAMESPACE=json.dumps(namespace),
                       ESO_GATE_SECRET=json.dumps(secret), ESO_GATE_OBJECT=str(tmp / 'object.json'))
            for mode in ('release', 'tag', 'head', 'dirty', 'uid', 'valid'):
                calls.write_text('[]')
                result = subprocess.run(['ansible-playbook', '-i', str(inventory), str(ansible / 'external-secrets-inputs.yaml'),
                    '-e', '{"external_secrets_registry_apply":true,"external_secrets_inputs_scope":"external-secrets-inputs-v1"}'],
                    env=env | {'ESO_GATE_MODE': mode}, text=True, capture_output=True, timeout=45)
                self.assertNotIn(secret['data']['.dockerconfigjson'], result.stdout + result.stderr)
                actual = json.loads(calls.read_text())
                if mode == 'valid':
                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                    self.assertTrue((tmp / 'object.json').exists())
                else:
                    self.assertNotEqual(result.returncode, 0, mode)
                    self.assertEqual(len(actual), 1 if mode == 'uid' else 0, mode)
                    self.assertFalse((tmp / 'object.json').exists())


if __name__ == '__main__':
    unittest.main()
