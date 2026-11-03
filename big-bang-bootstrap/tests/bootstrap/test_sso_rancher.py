"""Execute per-app Rancher adapter against native-shaped CLI state, no cluster."""
import base64,copy,json,os,shutil,subprocess,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
PLAY=ROOT/'configuration/authorization/sso/reconcile-rancher.yaml'
def rancher_chart_ca_fixture():
 """Public trust shape cross-checked against the checksummed 2.15.2 chart."""
 return {'containers':[{'name':'rancher','image':'rancher/rancher:v2.15.2','volumeMounts':[
  {'name':'tls-ca-additional-volume','mountPath':path,'subPath':'ca-additional.pem','readOnly':True}
  for path in ('/etc/pki/trust/anchors/ca-additional.pem','/etc/rancher/ssl/ca-additional.pem')]}],
  'volumes':[{'name':'tls-ca-additional-volume','secret':{'secretName':'tls-ca-additional','defaultMode':256}}]}
@unittest.skipUnless(os.environ.get('RUN_PLATFORM_SSO_TESTS'), 'enable isolated SSO job explicitly')
class RancherSSO(unittest.TestCase):
 def setUp(self):
  self.t=tempfile.TemporaryDirectory();self.addCleanup(self.t.cleanup);self.d=Path(self.t.name)
  self.state=self.d/'state.json';self.cli=self.d/'kubectl';shutil.copy2(ROOT/'tests/fixtures/rancher-cli.py',self.cli);self.cli.chmod(0o700)
  self.secret=self.d/'secret';self.secret.write_text('synthetic-fixture-only');self.secret.chmod(0o600)
  self.ca=self.d/'ca';self.ca.write_text('fixture-public-ca')
  self.initial={'serverMetadata':True,'auth':[{'metadata':{'name':'local'},'enabled':True},{'metadata':{'name':'genericoidc','resourceVersion':'1'},'enabled':False,'type':'genericOIDCConfig'}], 'publicTrust':{'data':{'ca-additional.pem':base64.b64encode(b'fixture-public-ca').decode()}},'deployment':{'spec':{'template':{'spec':rancher_chart_ca_fixture()}}}}
  self.state.write_text(json.dumps(self.initial))
  self.v={'sso_rancher_run':True,'sso_rancher_operation':'apply','sso_rancher_reviewed_scope':'rancher-sso-v1','sso_rancher_recovery_verified':True,'rancher_kubectl':str(self.cli),'rancher_kubeconfig':'/fixture/kubeconfig','rancher_context':'fixture','rancher_cluster_uid':'fixture-cluster','rancher_oidc_secret_file':str(self.secret),'sso_public_ca_file':str(self.ca),'sso_keycloak_origin':'https://identity.fixture.test','sso_apps':{'rancher':{'client_id':'rancher','origin':'https://rancher.fixture.test','apply':False}}}
 def data(self):return json.loads(self.state.read_text())
 def run_play(self,extra=None,check=False):
  r=subprocess.run(['ansible-playbook',str(PLAY),'-e',json.dumps({**self.v,**(extra or {})})]+(['--check'] if check else []),env={**os.environ,'ANSIBLE_LOCAL_TEMP':str(self.d/'local'),'ANSIBLE_REMOTE_TEMP':str(self.d/'remote'),'RANCHER_FIXTURE_STATE':str(self.state)},capture_output=True,text=True,timeout=60)
  self.assertNotIn('synthetic-fixture-only',r.stdout+r.stderr);return r
 def test_default_and_check_do_not_contact_cluster(self):
  self.secret.unlink()
  for extra,check in (({'sso_rancher_run':False},False),({},True)):
   r=self.run_play(extra,check);self.assertEqual(r.returncode,0,r.stdout+r.stderr)
  self.assertNotIn('events',self.data())
 def test_apply_inspect_repeat_and_independent_rollback(self):
  r=self.run_play();self.assertEqual(r.returncode,0,r.stdout+r.stderr)
  self.assertEqual(self.data()['providerWrites'],1);self.assertEqual(self.data()['auth'][1]['pkceMethod'],'S256')
  for op in ('inspect','apply'):
   r=self.run_play({'sso_rancher_operation':op});self.assertEqual(r.returncode,0,r.stdout+r.stderr);self.assertIn('changed=0',r.stdout)
  self.assertEqual(self.data()['providerWrites'],1)
  r=self.run_play({'sso_rancher_operation':'rollback'});self.assertEqual(r.returncode,0,r.stdout+r.stderr)
  d=self.data();self.assertTrue(d['auth'][0]['enabled']);self.assertFalse(d['auth'][1]['enabled']);self.assertEqual(d['bindings'],[]);self.assertEqual(d['publicTrust'],self.initial['publicTrust'])
  r=self.run_play({'sso_rancher_operation':'rollback'});self.assertEqual(r.returncode,0,r.stdout+r.stderr);self.assertIn('changed=0',r.stdout)
 def test_public_drift_never_rotates_existing_provider_credential(self):
  r=self.run_play();self.assertEqual(r.returncode,0,r.stdout+r.stderr)
  original=self.data()['auth'][1]['clientSecret']
  self.secret.write_text('different-local-fixture-key')
  d=self.data();d['auth'][1]['scope']='openid profile email other';self.state.write_text(json.dumps(d))
  r=self.run_play();self.assertEqual(r.returncode,0,r.stdout+r.stderr)
  self.assertEqual(self.data()['auth'][1]['clientSecret'],original)
  self.assertEqual(self.data()['auth'][1]['scope'],'openid profile email')
 def test_partial_binding_failure_resumes_without_provider_rewrite(self):
  d=self.data();d['failBinding']=True;self.state.write_text(json.dumps(d))
  r=self.run_play();self.assertNotEqual(r.returncode,0);self.assertEqual(self.data()['providerWrites'],1)
  d=self.data();d['failBinding']=False;self.state.write_text(json.dumps(d))
  r=self.run_play();self.assertEqual(r.returncode,0,r.stdout+r.stderr);self.assertEqual(self.data()['providerWrites'],1)
 def test_untrusted_ca_competing_provider_and_wrong_cluster_refuse(self):
  for kind in ('ca','provider','cluster','mtls'):
   d=copy.deepcopy(self.initial);extra={}
   if kind=='ca':d['publicTrust']['data']['ca-additional.pem']=base64.b64encode(b'foreign-ca').decode()
   elif kind=='provider':d['auth'].append({'metadata':{'name':'keycloakoidc'},'enabled':True})
   elif kind=='mtls':d['auth'][1]['certificate']='foreign-client-certificate'
   else:extra={'rancher_cluster_uid':'foreign-cluster'}
   self.state.write_text(json.dumps(d));r=self.run_play(extra);self.assertNotEqual(r.returncode,0);self.assertNotIn('providerWrites',self.data())

 def test_wrong_chart_mounts_or_image_refuse_before_native_writes(self):
  for kind in ('old-path','missing','subpath','writable','extra','remapped-key','image'):
   with self.subTest(kind=kind):
    d=copy.deepcopy(self.initial);pod=d['deployment']['spec']['template']['spec'];mounts=pod['containers'][0]['volumeMounts']
    if kind=='old-path':mounts[0]['mountPath']='/etc/ssl/certs/ca-additional.pem'
    elif kind=='missing':mounts.pop()
    elif kind=='subpath':mounts[0]['subPath']='another.pem'
    elif kind=='writable':mounts[0]['readOnly']=False
    elif kind=='extra':mounts.append({**mounts[0],'mountPath':'/unexpected/ca.pem'})
    elif kind=='remapped-key':pod['volumes'][0]['secret']['items']=[{'key':'another.pem','path':'ca-additional.pem'}]
    else:pod['containers'][0]['image']='rancher/rancher:v2.15.3'
    self.state.write_text(json.dumps(d));r=self.run_play();self.assertNotEqual(r.returncode,0)
    result=self.data();self.assertNotIn('providerWrites',result);self.assertFalse(result.get('bindings'))
    self.assertTrue(all(x['verb']=='get' for x in result.get('events',[])))

if __name__=='__main__':unittest.main()
