"""Execute real Ansible against an offline fake kubectl; never accesses a cluster."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
PLAY = ROOT / 'configuration/packages/mattermost/runtime/local-mode.yaml'
FAKE = r'''#!/usr/bin/env python3
import json,os,sys
from pathlib import Path
p=Path(os.environ['FAKE_STATE']); s=json.loads(p.read_text()); a=sys.argv[1:]
s['calls'].append(a)
if a[:3]==['get','namespace','kube-system']: print('cluster-id')
elif 'patch' in a:
    patch=json.loads(sys.stdin.read()); assert [x['op'] for x in patch]==['test','test','test','replace']
    assert patch[0]['value']=='cr-id' and patch[1]['value']==str(s['revision']) and patch[2]['value']==s['env']
    s['env']=patch[3]['value']; s['revision']+=1
elif 'get' in a and 'mattermost' in a and 'deployment' not in a and 'pods' not in a:
    print(json.dumps({'metadata':{'uid':'cr-id','resourceVersion':str(s['revision'])},'spec':{'replicas':1,'mattermostEnv':s['env']}}))
elif 'deployment' in a:
    print(json.dumps({'spec':{'template':{'spec':{'containers':[{'name':'mattermost','env':s['env']}]}}}}))
elif 'pods' in a:
    print(json.dumps({'items':[{'metadata':{'name':'mattermost-test'},'status':{'conditions':[{'type':'Ready','status':'True'}]}}]}))
elif 'exec' in a:
    enabled=next(x['value'] for x in s['env'] if x['name']=='MM_SERVICESETTINGS_ENABLELOCALMODE')=='true'
    if enabled and os.environ.get('FAKE_ENABLE_FAILURE')=='1':
        p.write_text(json.dumps(s)); sys.exit(1)
    assert ('test -S' in a[-1])==enabled
elif 'rollout' not in a: raise RuntimeError(a)
p.write_text(json.dumps(s))
'''

class LocalMode(unittest.TestCase):
    def run_case(self, action='enabled', fail=False, extra=()):
        with tempfile.TemporaryDirectory() as tmp:
            d=Path(tmp); exe=d/'kubectl'; exe.write_text(FAKE); exe.chmod(0o700)
            state=d/'state.json'; state.write_text(json.dumps({'env':[{'name':'PRESERVED','value':'FIXTURE-PRIVATE'}], 'revision':1,'calls':[]}))
            env={**os.environ,'PATH':tmp+':'+os.environ['PATH'],'FAKE_STATE':str(state),'KUBECONFIG':'/dev/null','FAKE_ENABLE_FAILURE':'1' if fail else '0'}
            cmd=['ansible-playbook','-i','localhost,',str(PLAY),'-e','mattermost_local_mode_apply=true','-e','mattermost_local_mode_approved=true','-e','mattermost_runtime_cluster_uid=cluster-id','-e','mattermost_runtime_cr_uid=cr-id','-e','mattermost_local_mode_action='+action,*extra]
            result=subprocess.run(cmd,env=env,text=True,capture_output=True)
            data=json.loads(state.read_text())
            self.assertNotIn('FIXTURE-PRIVATE',result.stdout+result.stderr)
            return result,data
    def test_enable_preserves_unrelated_env_and_only_two_fields(self):
        r,s=self.run_case(); self.assertEqual(r.returncode,0,r.stdout+r.stderr)
        self.assertEqual(s['env'][0],{'name':'PRESERVED','value':'FIXTURE-PRIVATE'})
        self.assertEqual(s['env'][1:], [{'name':'MM_SERVICESETTINGS_ENABLELOCALMODE','value':'true'}, {'name':'MM_SERVICESETTINGS_LOCALMODESOCKETLOCATION','value':'/var/tmp/mattermost-bootstrap.socket'}])
    def test_enable_failure_forces_disabled_before_reporting_failure(self):
        r,s=self.run_case(fail=True); self.assertNotEqual(r.returncode,0)
        self.assertEqual(s['env'][1]['value'],'false'); self.assertEqual(s['revision'],3)
        self.assertIn('socket absence verified',r.stdout)
    def test_disable_and_checkmode(self):
        r,s=self.run_case(action='disabled'); self.assertEqual(r.returncode,0,r.stdout+r.stderr)
        self.assertEqual(s['env'][1]['value'],'false')
        r,s=self.run_case(extra=('--check',)); self.assertEqual(r.returncode,0); self.assertEqual(s['calls'],[])

if __name__=='__main__': unittest.main()
