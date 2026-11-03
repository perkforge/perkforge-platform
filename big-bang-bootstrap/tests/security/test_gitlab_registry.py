from pathlib import Path
import base64,json,os,shutil,subprocess,tempfile,unittest
ROOT=Path(__file__).resolve().parents[2]
class Registry(unittest.TestCase):
 def test_private_profile_namespaces_create_repeat_and_no_credential_output(self):
  with tempfile.TemporaryDirectory(prefix='gitlab-registry-fixture-') as directory:
   p=Path(directory);out=p/'out';out.mkdir(mode=0o700)
   for name,value in [('username','offline-user'),('password','OFFLINEONLYNOTREAL123456789')]:
    file=p/name;file.write_text(value);file.chmod(0o600)
   state=p/'state';state.write_text(json.dumps({'api':'https://synthetic.invalid:6443','uid':'synthetic-cluster-uid','objects':{}}))
   stub=p/'kubectl';shutil.copy2(ROOT/'tests/fixtures/gitlab_delivery_cli.py',stub);stub.chmod(0o700);kube=p/'kube';kube.write_text('not a kubeconfig');kube.chmod(0o600)
   env={**os.environ,'GITLAB_DELIVERY_TEST_STATE':str(state),'ANSIBLE_LOCAL_TEMP':str(p/'local'),'ANSIBLE_REMOTE_TEMP':str(p/'remote')}
   def run(play,variables):
    vf=p/'vars';vf.write_text(json.dumps(variables));vf.chmod(0o600)
    result=subprocess.run(['ansible-playbook','-i','localhost,',str(ROOT/'configuration/packages/gitlab'/play),'-e','@'+str(vf)],env=env,capture_output=True,text=True,timeout=40)
    for value in ('offline-user','OFFLINEONLYNOTREAL123456789',base64.b64encode(b'offline-user:OFFLINEONLYNOTREAL123456789').decode()):self.assertNotIn(value,result.stdout+result.stderr)
    return result
   for target,namespace in [('gitlab','gitlab'),('manager','gitlab-runner'),('job','gitlab-ci-platform')]:
    variables={'gitlab_registry_run':True,'gitlab_registry_scope':'gitlab-registry-private-assembly-v1','gitlab_registry_target':target,'gitlab_registry_username_file':str(p/'username'),'gitlab_registry_password_file':str(p/'password'),'gitlab_private_output_directory':str(out)}
    r=run('prepare-registry.yaml',variables);self.assertEqual(r.returncode,0,r.stdout+r.stderr)
    manifest=out/('registry-'+target+'.json');item=json.loads(manifest.read_text())['items'][0];self.assertEqual(item['metadata']['namespace'],namespace);self.assertEqual(item['type'],'kubernetes.io/dockerconfigjson');self.assertEqual(set(json.loads(item['stringData']['.dockerconfigjson'])['auths']),{'registry1.dso.mil'})
    delivery={'gitlab_delivery_run':True,'gitlab_delivery_profile':'registry-'+target,'gitlab_delivery_scope':'gitlab-registry-'+target+'-delivery-v1','gitlab_kubectl':str(stub),'gitlab_kubeconfig':str(kube),'gitlab_context':'synthetic','gitlab_expected_api':'https://synthetic.invalid:6443','gitlab_expected_cluster_uid':'synthetic-cluster-uid','gitlab_credentials_manifest':str(manifest)}
    r=run('deliver-credentials.yaml',delivery);self.assertEqual(r.returncode,0,r.stdout+r.stderr);r=run('deliver-credentials.yaml',delivery);self.assertEqual(r.returncode,0,r.stdout+r.stderr);self.assertIn('changed=0',r.stdout)
   self.assertEqual(len(json.loads(state.read_text())['objects']),3)
