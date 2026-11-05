"""Exercise the actual default-off Ansible runner handoff against a private fake API."""
import json,os,subprocess,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
class RunnerStage(unittest.TestCase):
 def test_guarded_selection_repeat_and_foreign_source_refusal(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);release=p/'release/scripts';release.mkdir(parents=True);(release/'verify-release-ref.sh').write_text('exit 0\n')
   state=p/'state.json';state.write_text(json.dumps({'path':'./big-bang-bootstrap/clusters/local-gitlab-app','source_uid':'source','patches':0}))
   fake=p/'kubectl';fake.write_text('''#!/usr/bin/env python3
import sys,json
from pathlib import Path
p=Path(__file__).with_name('state.json');s=json.loads(p.read_text());a=sys.argv
if 'get' in a:
 i=a.index('get');kind,name=a[i+1:i+3]
 if kind=='namespace':o={'metadata':{'uid':'cluster'}}
 elif kind=='gitrepository':o={'metadata':{'uid':s['source_uid']},'spec':{'url':'https://github.com/perkforge/perkforge-platform.git','ref':{'tag':'v1.2.3'}},'status':{'artifact':{'revision':'v1.2.3@sha1:'+'a'*40}}}
 elif kind=='kustomization':o={'metadata':{'uid':'root','resourceVersion':'7'},'spec':{'path':s['path'],'prune':False,'force':False,'suspend':False}}
 elif kind=='secret':
  owner,typ,keys={'gitlab-runner-auth':('gitlab-runner-v1','Opaque',['runner-registration-token','runner-token']),'gitlab-runner-public-ca':('gitlab-trust-v1','Opaque',['gitlab.example.test.crt']),'private-registry':('gitlab-registry-v1','kubernetes.io/dockerconfigjson',['.dockerconfigjson'])}[name]
  o={'metadata':{'labels':{'perkforge.io/owner':owner}},'type':typ,'immutable':True,'data':{k:'SYNTHETIC' for k in keys}}
 else:sys.exit(2)
 print(json.dumps(o))
elif 'patch' in a:
 patch=json.loads(a[a.index('-p')+1]);assert patch[0]=={'op':'test','path':'/metadata/uid','value':'root'};assert patch[1]['value']=='7';assert patch[2]['value']['path']==s['path'];assert patch[3]=={'op':'replace','path':'/spec/path','value':'./big-bang-bootstrap/clusters/local-gitlab-runner'}
 if '--dry-run=server' not in a:s['path']=patch[3]['value'];s['patches']+=1;p.write_text(json.dumps(s))
 print('validated')
else:sys.exit(3)
''');fake.chmod(0o700)
   values={'gitlab_runner_stage_run':True,'gitlab_runner_stage_scope':'gitlab-runner-stage-v1','gitlab_runner_stage_release':'v1.2.3','gitlab_runner_stage_commit':'a'*40,'gitlab_runner_stage_release_directory':str(release.parent),'gitlab_runner_stage_kubectl':str(fake),'gitlab_runner_stage_kubeconfig':'/SYNTHETIC','gitlab_runner_stage_context':'fixture','gitlab_runner_stage_cluster_uid':'cluster','gitlab_runner_stage_root_uid':'root','gitlab_runner_stage_source_uid':'source','gitlab_runner_stage_hostname':'gitlab.example.test','gitlab_runner_stage_native_paused_verified':True,'gitlab_runner_stage_app_sso_verified':True,'gitlab_runner_stage_network_verified':True}
   def run(changes={},flags=[]):
    f=p/'input.json';f.write_text(json.dumps({**values,**changes}));return subprocess.run(['ansible-playbook',str(ROOT/'configuration/ansible/activate-gitlab-runner.yaml'),'-e','@'+str(f),*flags],capture_output=True,text=True,timeout=60)
   for changes,flags in [({'gitlab_runner_stage_run':False},[]),({},['--check']),({'gitlab_runner_stage_native_paused_verified':False},[])]:
    r=run(changes,flags);self.assertEqual(json.loads(state.read_text())['patches'],0)
   r=run();self.assertEqual(r.returncode,0,r.stdout+r.stderr);self.assertEqual(json.loads(state.read_text())['patches'],1)
   r=run();self.assertEqual(r.returncode,0,r.stdout+r.stderr);self.assertIn('changed=0',r.stdout);self.assertEqual(json.loads(state.read_text())['patches'],1)
   s=json.loads(state.read_text());s['source_uid']='foreign';state.write_text(json.dumps(s));r=run();self.assertNotEqual(r.returncode,0);self.assertEqual(json.loads(state.read_text())['patches'],1)
