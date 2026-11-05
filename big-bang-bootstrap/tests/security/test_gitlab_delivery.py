from pathlib import Path
import json,os,shutil,subprocess,tempfile,unittest
ROOT=Path(__file__).resolve().parents[2]
class SecretDelivery(unittest.TestCase):
 def test_no_contact_gate_partial_resume_repeat_conflict_and_cluster_refusal(self):
  with tempfile.TemporaryDirectory(prefix='gitlab-delivery-fixture-') as d:
   p=Path(d);stub=p/'kubectl';shutil.copy2(ROOT/'tests/fixtures/gitlab_delivery_cli.py',stub);stub.chmod(0o700)
   state=p/'state.json';initial={'api':'https://synthetic.invalid:6443','uid':'synthetic-cluster-uid','objects':{},'fail_after':2};state.write_text(json.dumps(initial));state.chmod(0o600)
   kube=p/'kubeconfig';kube.write_text('synthetic, not a kubeconfig');kube.chmod(0o600)
   manifest=p/'credentials.json';items=[]
   for name,ns,owner,kind,data in [('gitlab-database','gitlab','gitlab-data-v1','kubernetes.io/basic-auth',{'username':'gitlab','password':'OFFLINE_CANARY_123456789'}),('gitlab-valkey-acl','gitlab','gitlab-data-v1','Opaque',{'default':'OFFLINE_CANARY_123456789'}),('gitlab-redis','gitlab','gitlab-data-v1','Opaque',{'password':'OFFLINE_CANARY_123456789'}),('gitlab-oidc-provider','gitlab','gitlab-sso-v1','Opaque',{'provider':'OFFLINE_CANARY_123456789'})]:
    items.append({'apiVersion':'v1','kind':'Secret','metadata':{'name':name,'namespace':ns,'labels':{'perkforge.io/owner':owner}},'type':kind,'stringData':data})
   manifest.write_text(json.dumps({'apiVersion':'v1','kind':'List','items':items}));manifest.chmod(0o600)
   variables={'gitlab_delivery_run':True,'gitlab_delivery_scope':'gitlab-application-credential-delivery-v1','gitlab_kubectl':str(stub),'gitlab_kubeconfig':str(kube),'gitlab_context':'synthetic','gitlab_expected_api':initial['api'],'gitlab_expected_cluster_uid':initial['uid'],'gitlab_credentials_manifest':str(manifest)}
   vf=p/'vars.json';vf.write_text(json.dumps(variables));vf.chmod(0o600)
   env={**os.environ,'GITLAB_DELIVERY_TEST_STATE':str(state),'ANSIBLE_LOCAL_TEMP':str(p/'local'),'ANSIBLE_REMOTE_TEMP':str(p/'remote'),'ANSIBLE_NOCOLOR':'1'}
   def run(*extra):
    r=subprocess.run(['ansible-playbook','-i','localhost,',str(ROOT/'configuration/packages/gitlab/deliver-credentials.yaml'),'-e','@'+str(vf),*extra],env=env,capture_output=True,text=True,timeout=60)
    self.assertNotIn('OFFLINE_CANARY',r.stdout+r.stderr);return r
   self.assertEqual(run('--check').returncode,0);self.assertFalse(json.loads(state.read_text())['objects'])
   r=run();self.assertNotEqual(r.returncode,0);self.assertEqual(len(json.loads(state.read_text())['objects']),2)
   current=json.loads(state.read_text());current.pop('fail_after');state.write_text(json.dumps(current))
   r=run();self.assertEqual(r.returncode,0,r.stdout+r.stderr);self.assertEqual(len(json.loads(state.read_text())['objects']),4)
   before=state.read_bytes();r=run();self.assertEqual(r.returncode,0,r.stdout+r.stderr);self.assertIn('changed=0',r.stdout);self.assertEqual(state.read_bytes(),before)
   current=json.loads(state.read_text());current['objects']['gitlab/gitlab-redis']['metadata']['labels']={'foreign':'true'};state.write_text(json.dumps(current));before=state.read_bytes();self.assertNotEqual(run().returncode,0);self.assertEqual(state.read_bytes(),before)
   variables['gitlab_expected_cluster_uid']='wrong-cluster-uid';vf.write_text(json.dumps(variables));self.assertNotEqual(run().returncode,0);self.assertEqual(state.read_bytes(),before)
