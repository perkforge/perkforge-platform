"""Run the dedicated client adapter against independent Keycloak-shaped HTTPS."""
import copy,json,os,subprocess,unittest
from pathlib import Path
import integration.test_sso_clients as fixture
ROOT=Path(__file__).resolve().parents[2]
PLAY=ROOT/'configuration/packages/gitlab/reconcile-client.yaml'
class GitLabClient(unittest.TestCase):
 def test_disabled_prepare_repeat_activation_failure_resume_and_preservation(self):
  f=fixture.ClientAPI(methodName='runTest');f.setUp();self.addCleanup(f.doCleanups)
  handler=f.server.RequestHandlerClass;old_post=handler.do_POST
  def post(h):
   if h.path=='/auth/realms/master/protocol/openid-connect/token':
    h.rfile.read(int(h.headers.get('Content-Length',0)));return h.respond(200,{'access_token':'fixture-access-token','refresh_token':'fixture-refresh-token'})
   if h.path=='/auth/realms/master/protocol/openid-connect/logout':
    h.rfile.read(int(h.headers.get('Content-Length',0)));f.s.setdefault('logout',0);f.s['logout']+=1;return h.respond(204)
   return old_post(h)
  handler.do_POST=post
  variables={'gitlab_client_run':True,'gitlab_client_recovery_verified':True,'gitlab_client_native_ready':True,'gitlab_client_mfa_verified':True,'gitlab_keycloak_origin':'https://localhost:'+str(f.server.server_port),'gitlab_origin':'https://gitlab.example.invalid','gitlab_public_ca_file':str(f.d/'ca'),'gitlab_admin_username_file':str(f.d/'username'),'gitlab_admin_password_file':str(f.d/'password'),'gitlab_client_secret_file':str(f.d/'secret')}
  def run(op='prepare',extra=None,check=False):
   vf=f.d/'gitlab-vars.json';vf.write_text(json.dumps({**variables,'gitlab_client_operation':op,'gitlab_client_scope':'gitlab-client-'+op+'-v1',**(extra or {})}));vf.chmod(0o600)
   r=subprocess.run(['ansible-playbook','-i','localhost,',str(PLAY),'-e','@'+str(vf)]+(['--check'] if check else []),env={**os.environ,'ANSIBLE_LOCAL_TEMP':str(f.d/'local'),'ANSIBLE_REMOTE_TEMP':str(f.d/'remote')},capture_output=True,text=True,timeout=90)
   for secret in ('fixture-access-token','fixture-refresh-token','fixture-recovery-password','fixture-app-client-secret'):self.assertNotIn(secret,r.stdout+r.stderr)
   return r
  def ok(*args,**kwargs):
   r=run(*args,**kwargs);self.assertEqual(r.returncode,0,r.stdout+r.stderr);return r
  original=copy.deepcopy(f.s['foreign']);ok(check=True);self.assertFalse(f.s['calls']);ok();self.assertFalse(f.s['clients']['client-gitlab']['enabled']);self.assertEqual(len(f.s['writes']),1)
  before=len(f.s['writes']);self.assertIn('changed=0',ok().stdout);self.assertEqual(len(f.s['writes']),before)
  self.assertNotEqual(run('activate',{'gitlab_client_native_ready':False}).returncode,0);self.assertEqual(len(f.s['writes']),before)
  f.s['failEnable']=True;self.assertNotEqual(run('activate').returncode,0);self.assertTrue(f.s['clients']['client-gitlab']['enabled'])
  f.s['failEnable']=False;self.assertIn('changed=0',ok('activate').stdout)
  self.assertFalse(f.s['roles']);self.assertEqual(f.s['scopes']['client-gitlab'],[]);self.assertEqual(f.s['mapped']['client-gitlab'],[]);self.assertEqual(f.s['foreign'],original)
  ok('rollback');self.assertFalse(f.s['clients']['client-gitlab']['enabled']);self.assertIn('changed=0',ok('rollback').stdout)
  self.assertEqual(f.server.secrets['client-gitlab'],'fixture-app-client-secret')
  before=len(f.s['writes']);f.s['clients']['client-gitlab']['attributes']['perkforge-purpose']='foreign';self.assertNotEqual(run('activate').returncode,0);self.assertEqual(len(f.s['writes']),before)
  self.assertGreater(f.s['logout'],0)
