"""Exercise real Ansible label guards against isolated API state, never Kubernetes."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

PLAY = Path(__file__).resolve().parents[1] / 'playbooks/label-longhorn-workers.yml'
UID = '11111111-1111-1111-1111-111111111111'


class WorkerLabelTests(unittest.TestCase):
    def test_identity_conflict_default_and_success_boundaries(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            state = root / 'state.json'
            kubeconfig = root / 'kubeconfig'
            kubeconfig.touch(mode=0o600)
            cli = root / 'kubectl'
            cli.write_text('''#!/usr/bin/env python3
import json,os,sys
from pathlib import Path
p=Path(os.environ['LABEL_FIXTURE_STATE']);s=json.loads(p.read_text());a=sys.argv
s.setdefault('calls',[]).append(a[1:])
if 'namespace' in a: print(s['uid'])
elif 'patch' in a:
 n=next(n for n in s['nodes'] if n['metadata']['name']==a[a.index('node')+1]);patch=json.loads(a[a.index('--patch')+1])
 assert patch[0]['value']==n['metadata']['uid']
 assert patch[1]['value']==n['metadata']['resourceVersion']
 assert n['metadata']['name']!='control-1'
 for op in patch[2:]:n['metadata']['labels'][op['path'].split('/')[-1].replace('~1','/')]=op['value']
 s.setdefault('patched',[]).append(n['metadata']['name']);print('patched')
else:print(json.dumps({'items':s['nodes']}))
p.write_text(json.dumps(s))
''')
            cli.chmod(0o700)
            nodes = [{'metadata': {'name': name, 'uid': name+'-uid', 'resourceVersion': '1',
                                  'labels': {'kubernetes.io/hostname': name}},
                      'status': {'conditions': [{'type': 'Ready', 'status': 'True'}]}}
                     for name in ['control-1', 'worker-1', 'worker-2']]
            args = {'longhorn_labels_kubeconfig': str(kubeconfig), 'longhorn_labels_kubectl': str(cli),
                    'longhorn_labels_expected_cluster_uid': UID, 'longhorn_worker_labels_reviewed': True}
            for case in ['default', 'check', 'wrong-cluster', 'conflict', 'success', 'repeat']:
                with self.subTest(case=case):
                    data = {'uid': UID, 'nodes': json.loads(json.dumps(nodes))}
                    if case == 'wrong-cluster': data['uid'] = 'different'
                    if case == 'conflict': data['nodes'][1]['metadata']['labels']['storage.perkforge.io/worker'] = 'false'
                    if case != 'repeat': state.write_text(json.dumps(data))
                    values = {**args, 'longhorn_worker_labels_apply': case != 'default'}
                    result = subprocess.run(['ansible-playbook', '-i', 'localhost,', str(PLAY), '-e', json.dumps(values),
                                             *(['--check'] if case == 'check' else [])], capture_output=True, text=True, timeout=25,
                                            env={**os.environ, 'ANSIBLE_LOCAL_TEMP': directory+'/local',
                                                 'ANSIBLE_REMOTE_TEMP': directory+'/remote', 'LABEL_FIXTURE_STATE': str(state)})
                    after = json.loads(state.read_text())
                    self.assertEqual(result.returncode, 2 if case in ['wrong-cluster', 'conflict'] else 0, result.stdout+result.stderr)
                    if case in ['default', 'check']: self.assertEqual(after.get('calls', []), [])
                    if case in ['wrong-cluster', 'conflict']: self.assertEqual(after.get('patched', []), [])
                    if case in ['success', 'repeat']: self.assertEqual(after['patched'], ['worker-1', 'worker-2'])


if __name__ == '__main__': unittest.main()
