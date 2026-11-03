from pathlib import Path
import hashlib,importlib.util,json,os,shutil,subprocess,tempfile,unittest
ROOT=Path(__file__).resolve().parents[2]
class transport:
 @staticmethod
 def prepare(profile,cert_path,key_path,ca_path,output,ca_sha256):
  p=Path(output).parent.parent;vf=p/'assembly-vars.json'
  variables={'gitlab_transport_run':True,'gitlab_transport_scope':'gitlab-transport-private-assembly-v1','gitlab_transport_profile':profile,'gitlab_transport_domain':'perkforge.home.arpa','gitlab_transport_cert':cert_path,'gitlab_transport_key':key_path,'gitlab_transport_ca':ca_path,'gitlab_transport_ca_sha256':ca_sha256,'gitlab_private_output_directory':str(Path(output).parent)}
  vf.write_text(json.dumps(variables));vf.chmod(0o600)
  r=subprocess.run(['ansible-playbook','-i','localhost,',str(ROOT/'configuration/packages/gitlab/prepare-transport.yaml'),'-e','@'+str(vf)],env={**os.environ,'ANSIBLE_LOCAL_TEMP':str(p/'assembly-local'),'ANSIBLE_REMOTE_TEMP':str(p/'assembly-remote')},capture_output=True,text=True,timeout=60)
  if r.returncode:raise ValueError(r.stdout+r.stderr)
  return 'changed=0' not in r.stdout
class Transport(unittest.TestCase):
 def test_offline_certificate_assembly_delivery_repeat_and_refusal(self):
  with tempfile.TemporaryDirectory(prefix='gitlab-tls-fixture-') as directory:
   p=Path(directory);out=p/'out';out.mkdir(mode=0o700)
   def ssl(*args):
    r=subprocess.run(['openssl',*args],cwd=p,capture_output=True,text=True,timeout=20);self.assertEqual(r.returncode,0,r.stderr)
   ssl('req','-x509','-newkey','rsa:2048','-nodes','-keyout','ca.key','-out','ca.crt','-days','3','-subj','/CN=Offline CA','-addext','basicConstraints=critical,CA:TRUE')
   ssl('req','-new','-newkey','rsa:2048','-nodes','-keyout','leaf.key','-out','leaf.csr','-subj','/CN=ignored.invalid')
   (p/'ext').write_text('basicConstraints=critical,CA:FALSE\nextendedKeyUsage=serverAuth\nsubjectAltName=DNS:gitlab.perkforge.home.arpa,DNS:gitlab-objects.perkforge.home.arpa,DNS:gitlab-valkey.gitlab.svc.cluster.local\n')
   ssl('x509','-req','-in','leaf.csr','-CA','ca.crt','-CAkey','ca.key','-CAcreateserial','-out','leaf.crt','-days','2','-extfile','ext')
   (p/'leaf.key').chmod(0o600);sha=hashlib.sha256((p/'ca.crt').read_bytes()).hexdigest()
   env={**os.environ,'ANSIBLE_LOCAL_TEMP':str(p/'local'),'ANSIBLE_REMOTE_TEMP':str(p/'remote')}
   stub=p/'kubectl';shutil.copy2(ROOT/'tests/fixtures/gitlab_delivery_cli.py',stub);stub.chmod(0o700)
   state=p/'state';state.write_text(json.dumps({'api':'https://synthetic.invalid:6443','uid':'synthetic-cluster-uid','objects':{}}));env['GITLAB_DELIVERY_TEST_STATE']=str(state)
   kube=p/'kube';kube.write_text('not a kubeconfig');kube.chmod(0o600)
   for profile in ('web','objects','valkey'):
    destination=out/(profile+'.json');args=(profile,str(p/'leaf.crt'),str(p/'leaf.key'),str(p/'ca.crt'),str(destination),sha)
    self.assertTrue(transport.prepare(*args));self.assertFalse(transport.prepare(*args));self.assertEqual(destination.stat().st_mode&0o777,0o600)
    v={'gitlab_delivery_run':True,'gitlab_delivery_profile':'tls-'+profile,'gitlab_delivery_scope':'gitlab-tls-'+profile+'-delivery-v1','gitlab_kubectl':str(stub),'gitlab_kubeconfig':str(kube),'gitlab_context':'synthetic','gitlab_expected_api':'https://synthetic.invalid:6443','gitlab_expected_cluster_uid':'synthetic-cluster-uid','gitlab_credentials_manifest':str(destination)}
    def run(values):
     vf=p/'vars';vf.write_text(json.dumps(values));vf.chmod(0o600)
     return subprocess.run(['ansible-playbook','-i','localhost,',str(ROOT/'configuration/packages/gitlab/deliver-credentials.yaml'),'-e','@'+str(vf)],env=env,capture_output=True,text=True,timeout=60)
    before=state.read_bytes();self.assertNotEqual(run({**v,'gitlab_delivery_profile':'application'}).returncode,0);self.assertEqual(before,state.read_bytes())
    r=run(v);self.assertEqual(r.returncode,0,r.stdout+r.stderr);self.assertNotIn('BEGIN PRIVATE KEY',r.stdout+r.stderr)
    r=run(v);self.assertEqual(r.returncode,0,r.stdout+r.stderr);self.assertIn('changed=0',r.stdout)
    with self.assertRaises(ValueError):transport.prepare(*args[:-1],'0'*64)
   self.assertEqual(len(json.loads(state.read_text())['objects']),3)
   with self.assertRaises(ValueError):transport.prepare('wrong',str(p/'leaf.crt'),str(p/'leaf.key'),str(p/'ca.crt'),str(out/'wrong.json'),sha)
   (p/'leaf.key').chmod(0o644)
   with self.assertRaises(ValueError):transport.prepare('web',str(p/'leaf.crt'),str(p/'leaf.key'),str(p/'ca.crt'),str(out/'web.json'),sha)
