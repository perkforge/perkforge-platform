"""Actual Ansible native-shaped fixture, not proof of Kubernetes token acceptance."""
import copy,json,os,shutil,subprocess,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];PLAY=ROOT/'configuration/authorization/sso/reconcile-headlamp.yaml'
@unittest.skipUnless(os.environ.get('RUN_PLATFORM_SSO_TESTS'), 'enable isolated SSO job explicitly')
class HeadlampSSO(unittest.TestCase):
 def setUp(self):
  self.t=tempfile.TemporaryDirectory();self.addCleanup(self.t.cleanup);self.d=Path(self.t.name)
  self.cli=self.d/'kubectl';shutil.copy2(ROOT/'tests/fixtures/sso-headlamp-cli.py',self.cli);self.cli.chmod(0o700)
  self.secret=self.d/'secret';self.secret.write_text('synthetic-headlamp-secret');self.secret.chmod(0o600);self.ca=self.d/'ca';self.ca.write_text('-----BEGIN CERTIFICATE-----\nPUBLIC-FIXTURE-ONLY\n-----END CERTIFICATE-----')
  args=['--oidc-issuer-url=https://identity.fixture.test/auth/realms/perkforge','--oidc-client-id=headlamp','--oidc-username-claim=sub','--oidc-username-prefix=oidc:','--oidc-groups-claim=groups','--oidc-groups-prefix=oidc:','--oidc-signing-algs=RS256','--oidc-required-claim=azp=headlamp','--oidc-ca-file=/etc/rancher/rke2/identity/ca.crt']
  self.initial={'objects':{},'apiPods':{'items':[{'spec':{'containers':[{'args':args,'volumeMounts':[{'mountPath':'/etc/rancher/rke2/identity/ca.crt','readOnly':True}]}]}}]},'deployment':{'spec':{'template':{'spec':{'containers':[{'image':'fixture/headlamp:v0.45.0','envFrom':[{'secretRef':{'name':'perkforge-headlamp-sso-v1'}}],'env':[{'name':'SSL_CERT_FILE','value':'/identity-ca/ca.crt'}],'args':['-in-cluster','-oidc-ca-file=/identity-ca/ca.crt'],'volumeMounts':[{'name':'identity-ca','mountPath':'/identity-ca','readOnly':True}]}],'volumes':[{'name':'identity-ca','configMap':{'name':'perkforge-headlamp-sso-v1-ca'}}]}}},'status':{'availableReplicas':1}}}
  self.state=self.d/'state.json';self.state.write_text(json.dumps(self.initial))
  self.v={'sso_headlamp_run':True,'sso_headlamp_operation':'deliver','sso_headlamp_reviewed_scope':'headlamp-sso-delivery-v1','sso_headlamp_recovery_verified':True,'sso_kubectl':str(self.cli),'sso_kubeconfig':'/fixture/kubeconfig','sso_context':'fixture','sso_cluster_uid':'fixture-cluster','sso_headlamp_secret_file':str(self.secret),'sso_public_ca_file':str(self.ca),'sso_headlamp_expected_image':'fixture/headlamp:v0.45.0','sso_keycloak_origin':'https://identity.fixture.test','sso_apps':{'headlamp':{'client_id':'headlamp','origin':'https://headlamp.fixture.test','apply':False}}}
 def data(self):return json.loads(self.state.read_text())
 def run_play(self,op='deliver',extra=None,check=False):
  values={**self.v,'sso_headlamp_operation':op,'sso_headlamp_reviewed_scope':'headlamp-sso-delivery-v1' if op=='deliver' else 'headlamp-sso-v1',**(extra or {})}
  r=subprocess.run(['ansible-playbook',str(PLAY),'-e',json.dumps(values)]+(['--check'] if check else []),env={**os.environ,'ANSIBLE_LOCAL_TEMP':str(self.d/'local'),'ANSIBLE_REMOTE_TEMP':str(self.d/'remote'),'HEADLAMP_FIXTURE_STATE':str(self.state)},capture_output=True,text=True,timeout=60)
  self.assertNotIn('synthetic-headlamp-secret',r.stdout+r.stderr);return r
 def ok(self,op='deliver',extra=None):
  r=self.run_play(op,extra);self.assertEqual(r.returncode,0,r.stdout+r.stderr);return r
 def test_default_check_delivery_repeat_activate_inspect_rollback(self):
  for extra,check in (({'sso_headlamp_run':False},False),({},True)):
   r=self.run_play(extra=extra,check=check);self.assertEqual(r.returncode,0,r.stdout+r.stderr)
  self.assertNotIn('events',self.data())
  self.ok();self.assertEqual(len(self.data()['writes']),2)
  self.assertIn('changed=0',self.ok().stdout)
  self.ok('activate');self.assertEqual(len(self.data()['writes']),3)
  for op in ('activate','inspect'):self.assertIn('changed=0',self.ok(op).stdout)
  self.ok('rollback');self.assertNotIn('clusterrolebinding/perkforge-sso-platform-admins',self.data()['objects'])
  self.assertIn('secret/perkforge-headlamp-sso-v1',self.data()['objects']);self.assertIn('configmap/perkforge-headlamp-sso-v1-ca',self.data()['objects']);self.assertIn('changed=0',self.ok('rollback').stdout)
 def test_missing_or_wrong_api_trust_never_grants(self):
  self.ok();initial=self.data()
  for args in ([],[a.replace('RS256','HS256') for a in initial['apiPods']['items'][0]['spec']['containers'][0]['args']]):
   s=copy.deepcopy(initial);s['apiPods']['items'][0]['spec']['containers'][0]['args']=args;self.state.write_text(json.dumps(s))
   r=self.run_play('activate');self.assertNotEqual(r.returncode,0);self.assertEqual(len(self.data()['writes']),2)
 def test_partial_delivery_resumes_and_secret_rotation_refuses(self):
  s=self.data();s['failCA']=True;self.state.write_text(json.dumps(s));r=self.run_play();self.assertNotEqual(r.returncode,0);self.assertEqual(len(self.data()['writes']),1)
  s=self.data();s['failCA']=False;self.state.write_text(json.dumps(s));self.ok();self.assertEqual(len(self.data()['writes']),2)
  self.secret.write_text('different-fixture-secret');r=self.run_play();self.assertNotEqual(r.returncode,0);self.assertEqual(len(self.data()['writes']),2)
 def test_private_key_in_public_trust_refuses_before_delivery(self):
  self.ca.write_text('-----BEGIN CERTIFICATE-----\nPUBLIC\n-----END CERTIFICATE-----\n-----BEGIN PRIVATE KEY-----\nDO-NOT-COPY')
  r=self.run_play();self.assertNotEqual(r.returncode,0);self.assertNotIn('writes',self.data())
 def test_wrong_cluster_or_unowned_rbac_refuses(self):
  r=self.run_play(extra={'sso_cluster_uid':'other'});self.assertNotEqual(r.returncode,0);self.assertNotIn('writes',self.data())
  self.ok();s=self.data();s['objects']['clusterrolebinding/perkforge-sso-platform-admins']={'metadata':{'labels':{'foreign':'true'}},'roleRef':{},'subjects':[]};self.state.write_text(json.dumps(s))
  r=self.run_play('activate');self.assertNotEqual(r.returncode,0);self.assertEqual(len(self.data()['writes']),2)

if __name__=='__main__':unittest.main()
