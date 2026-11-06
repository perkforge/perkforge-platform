"""Exercise actual local Ansible with disposable fake inputs, never live credentials."""
from pathlib import Path
import json,os,subprocess,tempfile,unittest
ROOT=Path(__file__).resolve().parents[2]
PLAY=ROOT/'configuration/packages/gitlab/prepare-credentials.yaml'
class CredentialAssembly(unittest.TestCase):
 def test_default_check_repeat_drift_and_private_output(self):
  with tempfile.TemporaryDirectory(prefix='gitlab-credentials-fixture-') as d:
   root=Path(d);out=root/'output';out.mkdir(mode=0o700)
   marker='OFFLINE_FIXTURE_CANARY_ONLY_12345'
   variables={'gitlab_credentials_run':True,'gitlab_credentials_scope':'gitlab-application-private-assembly-v1','gitlab_credentials_output_dir':str(out),'gitlab_origin':'https://gitlab.example.invalid','gitlab_issuer':'https://identity.example.invalid/auth/realms/perkforge'}
   for name in ('database_password','valkey_password','client_secret'):
    p=root/name;p.write_text('glrt-OFFLINE_FIXTURE_CANARY' if name=='runner_token' else marker);p.chmod(0o600);variables['gitlab_'+name+'_file']=str(p)
   vf=root/'vars.json';vf.write_text(json.dumps(variables));vf.chmod(0o600)
   env={**os.environ,'ANSIBLE_LOCAL_TEMP':str(root/'local'),'ANSIBLE_REMOTE_TEMP':str(root/'remote'),'ANSIBLE_NOCOLOR':'1'}
   def run(*extra):
    r=subprocess.run(['ansible-playbook','-i','localhost,',str(PLAY),'-e','@'+str(vf),*extra],env=env,capture_output=True,text=True,timeout=45)
    self.assertNotIn(marker,r.stdout+r.stderr);return r
   self.assertEqual(run('--check').returncode,0);self.assertFalse((out/'application-credentials.json').exists())
   r=run();self.assertEqual(r.returncode,0,r.stdout+r.stderr)
   p=out/'application-credentials.json';self.assertEqual(p.stat().st_mode&0o777,0o600);items=json.loads(p.read_text())['items'];self.assertEqual(len(items),4);self.assertNotIn('gitlab-runner-auth',{x['metadata']['name'] for x in items})
   provider=json.loads(next(x for x in items if x['metadata']['name']=='gitlab-oidc-provider')['stringData']['provider']);self.assertTrue(provider['args']['pkce']);self.assertEqual(provider['args']['uid_field'],'sub')
   before=p.read_bytes();r=run();self.assertEqual(r.returncode,0,r.stdout+r.stderr);self.assertIn('changed=0',r.stdout)
   (root/'database_password').write_text('CHANGED_OFFLINE_PASSWORD_123456789');r=run();self.assertNotEqual(r.returncode,0);self.assertEqual(p.read_bytes(),before)
   variables['gitlab_credentials_scope']='WRONG';vf.write_text(json.dumps(variables));self.assertNotEqual(run().returncode,0)

 def test_legacy_and_routable_runner_tokens_and_malformed_refusal(self):
  from fixtures.gitlab_runner_tokens import routable_runner_token
  routed=routable_runner_token()
  cases=[('glrt-OFFLINE_FIXTURE_CANARY',True),(routed,True),(routed.replace('.01.','.02.'),False),(routed[:-1],False),('glpat-OFFLINE_FIXTURE_CANARY',False),(routed+'.extra',False),(routed[:12]+' '+routed[12:],False),(routed[:12]+'\n'+routed[12:],False),(routed.replace('.01.','..01.'),False)]
  with tempfile.TemporaryDirectory(prefix='gitlab-runner-shapes-') as d:
   root=Path(d)
   for number,(token,valid) in enumerate(cases):
    with self.subTest(case=number):
     out=root/str(number);out.mkdir(mode=0o700);source=root/('token-'+str(number));source.write_text(token);source.chmod(0o600)
     variables={'gitlab_credentials_run':True,'gitlab_credentials_profile':'runner','gitlab_credentials_scope':'gitlab-runner-private-assembly-v1','gitlab_credentials_output_dir':str(out),'gitlab_runner_token_file':str(source)}
     vf=root/'vars';vf.write_text(json.dumps(variables));vf.chmod(0o600)
     r=subprocess.run(['ansible-playbook','-i','localhost,',str(PLAY),'-e','@'+str(vf)],env={**os.environ,'ANSIBLE_LOCAL_TEMP':str(root/'local'),'ANSIBLE_REMOTE_TEMP':str(root/'remote')},capture_output=True,text=True,timeout=45)
     self.assertNotIn(token,r.stdout+r.stderr)
     if valid:
      self.assertEqual(r.returncode,0,r.stdout+r.stderr);f=out/'runner-credentials.json';self.assertEqual(f.stat().st_mode&0o777,0o600);item=json.loads(f.read_text())['items'][0];self.assertEqual(item['stringData']['runner-token'],token)
     else:self.assertNotEqual(r.returncode,0);self.assertFalse((out/'runner-credentials.json').exists())
