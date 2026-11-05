from pathlib import Path
import importlib.util,json,os,shutil,subprocess,sys,tempfile,unittest
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'configuration/packages/gitlab/verification'))
def prepare(root_file,rpc_file,admin_file,output):
 p=Path(output).parent.parent;vf=p/'assembly-vars.json'
 variables={'gitlab_foundation_run':True,'gitlab_foundation_assembly_scope':'gitlab-foundation-private-assembly-v1','gitlab_root_password_file':root_file,'gitlab_garage_rpc_file':rpc_file,'gitlab_garage_admin_file':admin_file,'gitlab_private_output_directory':str(Path(output).parent)}
 vf.write_text(json.dumps(variables));vf.chmod(0o600)
 r=subprocess.run(['ansible-playbook','-i','localhost,',str(ROOT/'configuration/packages/gitlab/prepare-foundation.yaml'),'-e','@'+str(vf)],env={**os.environ,'ANSIBLE_LOCAL_TEMP':str(p/'assembly-local'),'ANSIBLE_REMOTE_TEMP':str(p/'assembly-remote')},capture_output=True,text=True,timeout=60)
 if r.returncode:raise ValueError(r.stdout+r.stderr)
 return 'changed=0' not in r.stdout
class Foundation(unittest.TestCase):
 def test_private_assembly_delivery_repeat_and_drift_refusal(self):
  with tempfile.TemporaryDirectory(prefix='gitlab-foundation-fixture-') as directory:
   p=Path(directory);out=p/'out';out.mkdir(mode=0o700)
   for name,value in [('root','OFFLINE recovery password only!'),('rpc','a'*64),('admin','b'*64)]:
    path=p/name;path.write_text(value+'\n');path.chmod(0o600)
   destination=out/'foundation.json';args=tuple(str(p/n) for n in ('root','rpc','admin'))+(str(destination),)
   self.assertTrue(prepare(*args));self.assertFalse(prepare(*args));self.assertEqual(destination.stat().st_mode&0o777,0o600)
   manifest=json.loads(destination.read_text());self.assertEqual({i['metadata']['name'] for i in manifest['items']},{'gitlab-initial-admin','gitlab-garage-private'})
   state=p/'state';state.write_text(json.dumps({'api':'https://synthetic.invalid:6443','uid':'synthetic-cluster-uid','objects':{}}))
   stub=p/'kubectl';shutil.copy2(ROOT/'tests/fixtures/gitlab_delivery_cli.py',stub);stub.chmod(0o700)
   kube=p/'kube';kube.write_text('not a kubeconfig');kube.chmod(0o600)
   v={'gitlab_delivery_run':True,'gitlab_delivery_profile':'foundation','gitlab_delivery_scope':'gitlab-foundation-credential-delivery-v1','gitlab_kubectl':str(stub),'gitlab_kubeconfig':str(kube),'gitlab_context':'synthetic','gitlab_expected_api':'https://synthetic.invalid:6443','gitlab_expected_cluster_uid':'synthetic-cluster-uid','gitlab_credentials_manifest':str(destination)}
   env={**os.environ,'GITLAB_DELIVERY_TEST_STATE':str(state),'ANSIBLE_LOCAL_TEMP':str(p/'local'),'ANSIBLE_REMOTE_TEMP':str(p/'remote')}
   def run(values):
    vf=p/'vars';vf.write_text(json.dumps(values));vf.chmod(0o600)
    result=subprocess.run(['ansible-playbook','-i','localhost,',str(ROOT/'configuration/packages/gitlab/deliver-credentials.yaml'),'-e','@'+str(vf)],env=env,capture_output=True,text=True,timeout=60)
    for value in ('OFFLINE recovery password only!','a'*64,'b'*64):self.assertNotIn(value,result.stdout+result.stderr)
    return result
   before=state.read_bytes();self.assertNotEqual(run({**v,'gitlab_delivery_profile':'application'}).returncode,0);self.assertEqual(state.read_bytes(),before)
   first=run(v);self.assertEqual(first.returncode,0,first.stdout+first.stderr)
   second=run(v);self.assertEqual(second.returncode,0,second.stdout+second.stderr);self.assertIn('changed=0',second.stdout)
   before=destination.read_bytes();(p/'root').write_text('CHANGED OFFLINE recovery password!')
   with self.assertRaises(ValueError):prepare(*args)
   self.assertEqual(destination.read_bytes(),before)
