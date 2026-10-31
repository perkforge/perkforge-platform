"""Offline real-playbook tests with a file-backed kubectl mock; no Kubernetes API."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
import yaml

ROOT = Path(__file__).resolve().parent

MOCK = r'''#!/usr/bin/python3
import json,os,sys
from pathlib import Path
p=Path(os.environ['SMOKE_MOCK_STATE'])
state=json.loads(p.read_text())
a=sys.argv[1:]
while a and a[0] in ['--kubeconfig','--request-timeout=20s']:
 if a[0]=='--kubeconfig':a=a[2:]
 else:a=a[1:]
if a[:1]==['-n']:a=a[2:]
state['calls'].append(a)
status=0
if a[:3]==['get','namespace','kube-system']:
 print(json.dumps({'metadata':{'uid':state['uid']}}))
elif a[:2]==['get','node']:
 print(json.dumps({'metadata':{'labels':{'kubernetes.io/hostname':a[2]}},'status':{'conditions':[{'type':'Ready','status':'True'}]}}))
elif a[:2]==['get','namespace']:
 if state.get('namespace'):print(json.dumps(state['namespace']))
elif a[:1]==['create']:
 text=sys.stdin.read()
 if '"kind": "Namespace"' in text:
  obj=json.loads(text)
  obj['metadata']['uid']='11111111-2222-3333-4444-555555555555'
  state['namespace']=obj
  if state['scenario']=='foreign-cleanup':obj['metadata']['labels']['perkforge.io/smoke-run']='someone-else'
 else:state['resources_created']=True
elif a[:2]==['get','pods']:
 print(json.dumps({'items':[{'metadata':{'name':n},'spec':{'nodeName':w},'status':{'podIP':ip}}
 for n,w,ip in [('probe-a','worker-a','192.0.2.10'),('probe-b','worker-b','192.0.2.11')]]}))
elif a[:2]==['get','service']:
 print(json.dumps({'spec':{'clusterIP':'192.0.2.20' if a[2]=='smoke-http' else '192.0.2.21'}}))
elif a[:1]==['exec']:
 if 'nslookup' in a:print('Address: '+('192.0.2.21' if a[-1].startswith('kubernetes.') else '192.0.2.20'))
 else:
  if state['scenario']=='http-failure':status=1
  else:print('worker-a' if '192.0.2.10' in a[-1] else 'worker-b')
elif a[:2]==['delete','--raw']:
 body=json.loads(sys.stdin.read())
 assert body['preconditions']['uid']==state['namespace']['metadata']['uid']
 state['namespace']=None
 state['deleted']=True
elif a[:1]==['wait']:pass
elif a[:1]==['get']:print('{}')
else:raise SystemExit('Unexpected mocked command: '+repr(a))
p.write_text(json.dumps(state))
sys.exit(status)
'''

class WorkloadSmokeTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.work=Path(self.tmp.name)
        self.client=self.work/'kubectl'
        self.client.write_text(MOCK);self.client.chmod(0o700)
        self.kubeconfig=self.work/'kubeconfig'
        self.kubeconfig.write_text('SYNTHETIC_CREDENTIAL_MUST_NOT_APPEAR');self.kubeconfig.chmod(0o600)
        self.output=self.work/'results';self.output.mkdir(mode=0o700)
        self.state=self.work/'state.json'
        self.uid='aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee'
        self.values=dict(workload_smoke_apply=True,workload_smoke_kubeconfig=str(self.kubeconfig),
            workload_smoke_kubectl=str(self.client),workload_smoke_output_parent=str(self.output),
            workload_smoke_expected_cluster_uid=self.uid,workload_smoke_workers=['worker-a','worker-b'])
        # Execute the real task order with bounded, zero-delay synthetic retries.
        play=yaml.safe_load((ROOT/'workload-smoke.yml').read_text())
        def transform(value):
            if isinstance(value,dict):
                return {k:(1 if k=='retries' else 0 if k=='delay' else transform(v)) for k,v in value.items()}
            if isinstance(value,list):return [transform(x) for x in value]
            if isinstance(value,str):return value.replace('fixtures/workload-smoke.yaml',str(ROOT/'fixtures/workload-smoke.yaml'))
            return value
        self.play=self.work/'play.yml';self.play.write_text(yaml.safe_dump(transform(play)))

    def invoke(self,scenario='success',check=False,**overrides):
        namespace={'metadata':{'uid':'other-uid','labels':{}}} if scenario=='preexisting' else None
        self.state.write_text(json.dumps(dict(uid=self.uid,scenario=scenario,namespace=namespace,calls=[])))
        p=subprocess.run(['ansible-playbook','-i','localhost,',str(self.play),'-e',json.dumps({**self.values,**overrides}),*(['--check'] if check else [])],
            capture_output=True,text=True,timeout=90,env={**os.environ,'SMOKE_MOCK_STATE':str(self.state),
            'ANSIBLE_LOCAL_TEMP':str(self.work/'ansible'),'ANSIBLE_REMOTE_TEMP':str(self.work/'remote')})
        self.assertNotIn('SYNTHETIC_CREDENTIAL_MUST_NOT_APPEAR',p.stdout+p.stderr)
        return p,json.loads(self.state.read_text())

    def test_defaults_and_check_mode_make_no_api_call(self):
        for values in [dict(workload_smoke_apply=False),dict(check=True)]:
            p,state=self.invoke(**values)
            self.assertEqual(p.returncode,0,p.stdout+p.stderr)
            self.assertEqual(state['calls'],[])

    def test_wrong_cluster_and_existing_namespace_never_mutate(self):
        for scenario,extra in [('success',dict(workload_smoke_expected_cluster_uid='ffffffff-bbbb-cccc-dddd-eeeeeeeeeeee')),('preexisting',{})]:
            p,state=self.invoke(scenario,**extra)
            self.assertNotEqual(p.returncode,0,p.stdout+p.stderr)
            self.assertTrue(all(call[0]=='get' for call in state['calls']))
            self.assertFalse(list(self.output.iterdir()))

    def test_success_failure_and_foreign_cleanup(self):
        for scenario in ['success','http-failure','foreign-cleanup']:
            with self.subTest(scenario=scenario):
                p,state=self.invoke(scenario)
                self.assertEqual(p.returncode==0,scenario=='success',p.stdout+p.stderr)
                self.assertEqual(state.get('deleted',False),scenario!='foreign-cleanup')
                summary=max(self.output.glob('*/summary.yml'),key=lambda x:x.stat().st_mtime_ns)
                result=yaml.safe_load(summary.read_text())
                self.assertEqual(result['probes_passed'],scenario!='http-failure')
                self.assertEqual(result['cleanup_passed'],scenario!='foreign-cleanup')
                self.assertEqual(summary.stat().st_mode & 0o777,0o600)
                if scenario=='success':
                    probes=[c for c in state['calls'] if c[0]=='exec']
                    self.assertEqual(len([c for c in probes if 'nslookup' in c]),4)
                    self.assertEqual(len([c for c in probes if 'wget' in c]),6)

if __name__=='__main__':unittest.main()
