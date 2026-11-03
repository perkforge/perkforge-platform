from pathlib import Path
import hashlib,json,os,shutil,subprocess,tempfile,unittest
ROOT=Path(__file__).resolve().parents[2]
class PublicCA(unittest.TestCase):
 def test_create_repeat_fingerprint_and_foreign_object_refusal(self):
  with tempfile.TemporaryDirectory(prefix='gitlab-public-ca-fixture-') as directory:
   p=Path(directory);subprocess.run(['openssl','req','-x509','-newkey','rsa:2048','-nodes','-days','2','-subj','/CN=Offline CA fixture','-keyout',str(p/'key'),'-out',str(p/'ca')],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
   stub=p/'kubectl';shutil.copy2(ROOT/'tests/fixtures/gitlab_delivery_cli.py',stub);stub.chmod(0o700);state=p/'state';state.write_text(json.dumps({'api':'https://synthetic.invalid:6443','uid':'synthetic-cluster-uid','objects':{}}));state.chmod(0o600)
   kube=p/'kube';kube.write_text('not a kubeconfig');kube.chmod(0o600)
   v={'gitlab_ca_run':True,'gitlab_ca_stage':'platform','gitlab_ca_scope':'gitlab-ca-platform-v1','gitlab_ca_file':str(p/'ca'),'gitlab_ca_file_sha256':hashlib.sha256((p/'ca').read_bytes()).hexdigest(),'gitlab_kubectl':str(stub),'gitlab_kubeconfig':str(kube),'gitlab_context':'synthetic','gitlab_expected_api':'https://synthetic.invalid:6443','gitlab_expected_cluster_uid':'synthetic-cluster-uid'}
   def run(check=False):
    vf=p/'vars';vf.write_text(json.dumps(v));vf.chmod(0o600)
    return subprocess.run(['ansible-playbook','-i','localhost,',str(ROOT/'configuration/packages/gitlab/deliver-public-ca.yaml'),'-e','@'+str(vf)]+(['--check'] if check else []),env={**os.environ,'GITLAB_DELIVERY_TEST_STATE':str(state),'ANSIBLE_LOCAL_TEMP':str(p/'local'),'ANSIBLE_REMOTE_TEMP':str(p/'remote')},capture_output=True,text=True,timeout=60)
   def ok(**kw):
    r=run(**kw);self.assertEqual(r.returncode,0,r.stdout+r.stderr);return r
   ok(check=True);self.assertFalse(json.loads(state.read_text())['objects']);ok();self.assertIn('changed=0',ok().stdout)
   cm=json.loads(state.read_text())['objects']['gitlab/gitlab-platform-public-ca'];self.assertEqual(cm['data'],{'platform-ca.crt':(p/'ca').read_text().strip()});self.assertTrue(cm['immutable'])
   v['gitlab_ca_stage']='valkey';v['gitlab_ca_scope']='gitlab-ca-valkey-v1';ok();self.assertEqual(json.loads(state.read_text())['objects']['gitlab/gitlab-valkey-public-ca']['type'],'Opaque')
   v['gitlab_ca_stage']='runner';v['gitlab_ca_scope']='gitlab-ca-runner-v1';v['gitlab_origin']='https://gitlab.example.invalid:8443';ok();self.assertIn('changed=0',ok().stdout)
   runner=json.loads(state.read_text())['objects']['gitlab-runner/gitlab-runner-public-ca'];self.assertEqual(set(runner['data']),{'gitlab.example.invalid.crt'});self.assertTrue(runner['immutable']);self.assertNotIn('gitlab/gitlab-runner-public-ca',json.loads(state.read_text())['objects'])
   before=state.read_bytes();v['gitlab_origin']='https://UNCONFIGURED.invalid';self.assertNotEqual(run().returncode,0);self.assertEqual(state.read_bytes(),before)
   v['gitlab_ca_stage']='valkey';v['gitlab_ca_scope']='gitlab-ca-valkey-v1'
   before=state.read_bytes();v['gitlab_ca_file_sha256']='0'*64;self.assertNotEqual(run().returncode,0);self.assertEqual(before,state.read_bytes())
   v['gitlab_ca_file_sha256']=hashlib.sha256((p/'ca').read_bytes()).hexdigest();s=json.loads(state.read_text());s['objects']['gitlab/gitlab-valkey-public-ca']['metadata']['labels']={'foreign':'true'};state.write_text(json.dumps(s));before=state.read_bytes();self.assertNotEqual(run().returncode,0);self.assertEqual(before,state.read_bytes())
