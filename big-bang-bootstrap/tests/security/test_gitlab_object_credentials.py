from pathlib import Path
import configparser,json,os,shutil,subprocess,tempfile,unittest
ROOT=Path(__file__).resolve().parents[2]
class ObjectCredentials(unittest.TestCase):
 def test_assembly_delivery_scope_repeat_and_drift_refusal(self):
  with tempfile.TemporaryDirectory(prefix='gitlab-object-fixture-') as directory:
   p=Path(directory);out=p/'out';out.mkdir(mode=0o700)
   for key,value in [('access','OFFLINEKEYID123'),('secret','OFFLINESECRETKEY123456789')]:
    path=p/key;path.write_text(value);path.chmod(0o600)
   env={**os.environ,'ANSIBLE_LOCAL_TEMP':str(p/'local'),'ANSIBLE_REMOTE_TEMP':str(p/'remote')}
   def run(play,v,check=False):
    vf=p/'vars';vf.write_text(json.dumps(v));vf.chmod(0o600)
    r=subprocess.run(['ansible-playbook','-i','localhost,',str(ROOT/'configuration/packages/gitlab'/play),'-e','@'+str(vf)]+(['--check'] if check else []),env=env,capture_output=True,text=True,timeout=60)
    for value in ('OFFLINEKEYID123','OFFLINESECRETKEY123456789'):self.assertNotIn(value,r.stdout+r.stderr)
    return r
   v={'gitlab_object_credentials_run':True,'gitlab_object_credentials_scope':'gitlab-object-private-assembly-v1','gitlab_object_endpoint':'https://objects.example.invalid','gitlab_object_access_key_file':str(p/'access'),'gitlab_object_secret_key_file':str(p/'secret'),'gitlab_object_output_directory':str(out)}
   r=run('prepare-object-credentials.yaml',v,True);self.assertEqual(r.returncode,0,r.stdout+r.stderr);self.assertFalse((out/'object-credentials.json').exists())
   r=run('prepare-object-credentials.yaml',v);self.assertEqual(r.returncode,0,r.stdout+r.stderr);manifest=out/'object-credentials.json';self.assertEqual(manifest.stat().st_mode&0o777,0o600)
   item=json.loads(manifest.read_text())['items'][0];conn=json.loads(item['stringData']['connection']);self.assertEqual(conn['endpoint'],'https://objects.example.invalid');self.assertTrue(conn['path_style'])
   cfg=configparser.ConfigParser();cfg.read_string(item['stringData']['s3cfg']);self.assertTrue(cfg['default'].getboolean('use_https'));self.assertTrue(cfg['default'].getboolean('check_ssl_hostname'));self.assertTrue(cfg['default'].getboolean('check_ssl_certificate'))
   r=run('prepare-object-credentials.yaml',v);self.assertEqual(r.returncode,0,r.stdout+r.stderr);self.assertIn('changed=0',r.stdout)
   stub=p/'kubectl';shutil.copy2(ROOT/'tests/fixtures/gitlab_delivery_cli.py',stub);stub.chmod(0o700);state=p/'state';state.write_text(json.dumps({'api':'https://synthetic.invalid:6443','uid':'synthetic-cluster-uid','objects':{}}));env['GITLAB_DELIVERY_TEST_STATE']=str(state)
   kube=p/'kube';kube.write_text('not a kubeconfig');kube.chmod(0o600)
   delivery={'gitlab_delivery_run':True,'gitlab_delivery_profile':'object-store','gitlab_delivery_scope':'gitlab-object-credential-delivery-v1','gitlab_kubectl':str(stub),'gitlab_kubeconfig':str(kube),'gitlab_context':'synthetic','gitlab_expected_api':'https://synthetic.invalid:6443','gitlab_expected_cluster_uid':'synthetic-cluster-uid','gitlab_credentials_manifest':str(manifest)}
   before=state.read_bytes();self.assertNotEqual(run('deliver-credentials.yaml',{**delivery,'gitlab_delivery_profile':'application'}).returncode,0);self.assertEqual(before,state.read_bytes())
   r=run('deliver-credentials.yaml',delivery);self.assertEqual(r.returncode,0,r.stdout+r.stderr);self.assertEqual(len(json.loads(state.read_text())['objects']),1)
   r=run('deliver-credentials.yaml',delivery);self.assertEqual(r.returncode,0,r.stdout+r.stderr);self.assertIn('changed=0',r.stdout)
   before=manifest.read_bytes();(p/'secret').write_text('CHANGEDOFFLINESECRET123456789');self.assertNotEqual(run('prepare-object-credentials.yaml',v).returncode,0);self.assertEqual(before,manifest.read_bytes())
