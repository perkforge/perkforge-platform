"""Actual Ansible on synthetic TLS. No real GitLab, token, runner or CI."""
import json,os,ssl,subprocess,tempfile,threading,unittest
from pathlib import Path
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from urllib.parse import urlsplit,unquote
ROOT=Path(__file__).resolve().parents[2]
D=ROOT/'configuration/packages/gitlab/enrollment/acceptance'
class Preparation(unittest.TestCase):
 observed=False
 def test_native_project_and_paused_runner_guards(self):
  with tempfile.TemporaryDirectory(prefix='acceptance-fixture-') as tmp:
   p=Path(tmp);p.chmod(0o700);rd=p/'runner';rd.mkdir(mode=0o700)
   subprocess.run(['openssl','req','-x509','-newkey','rsa:2048','-nodes','-days','1','-subj','/CN=localhost','-addext','subjectAltName=DNS:localhost','-keyout',str(p/'key'),'-out',str(p/'ca')],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL);(p/'ca').chmod(0o644)
   state={'project':None,'runner':None,'writes':[],'foreign':False,'wrong_parent':False,'branch_unsafe':False,'other_runner':False,'uncertain':False,'runner_uncertain':False,'expired':False,'foreign_authority':False}
   class H(BaseHTTPRequestHandler):
    def log_message(self,*a):pass
    def response(self,c,v):
     self.send_response(c);self.send_header('Content-Type','application/json');self.end_headers();self.wfile.write(json.dumps(v).encode())
    def do_GET(self):
     if self.headers.get('PRIVATE-TOKEN')!='SYNTHETIC-ONLY':return self.response(403,{})
     path=unquote(urlsplit(self.path).path)
     if path=='/api/v4/user':return self.response(200,{'id':8,'state':'active','bot':True})
     authority={'id':12,'user_id':8,'access_level':50,'active':True,'revoked':False,'scopes':['api'],'expires_at':'2000-01-01' if state['expired'] else '2099-01-01'}
     if path=='/api/v4/personal_access_tokens/self':return self.response(200,authority)
     if path=='/api/v4/groups/7/members/8':return self.response(200,{'id':8,'access_level':30 if state['foreign_authority'] else 50})
     if path=='/api/v4/groups/7/access_tokens/12':return self.response(200,authority)
     if path=='/api/v4/version':return self.response(200,{'version':'19.4.2-ee'})
     if path=='/api/v4/groups/7':return self.response(200,{'id':7,'full_path':'tenants','visibility':'private'})
     if path=='/api/v4/groups/9':return self.response(200,{'id':9,'parent_id':99 if state['wrong_parent'] else 7,'full_path':'tenants/portal','visibility':'private'})
     if path in ['/api/v4/projects/31','/api/v4/projects/tenants/portal/platform-acceptance']:
      if state['foreign']:return self.response(200,{'id':99})
      return self.response(200,state['project']) if state['project'] else self.response(404,{})
     if path=='/api/v4/projects/31/protected_branches/main':return self.response(200,{'name':'main','allow_force_push':state['branch_unsafe'],'push_access_levels':[{'access_level':0}]})
     if path=='/api/v4/projects/31/runners':return self.response(200,[{'id':1,'description':'foreign'}] if state['other_runner'] else ([{'id':22,'description':state['runner']['description']}] if state['runner'] else []))
     if path=='/api/v4/runners/22':return self.response(200,state['runner'])
     return self.response(404,{})
    def do_POST(self):
     body=json.loads(self.rfile.read(int(self.headers['Content-Length'])));state['writes'].append((self.path,body))
     if self.path=='/api/v4/projects':
      assert body['namespace_id']==9 and body['visibility']=='private' and body['builds_access_level']=='disabled'
      assert body['shared_runners_enabled'] is False and body['group_runners_enabled'] is False and body['initialize_with_readme'] is False
      state['project']={**body,'id':31,'namespace':{'id':9,'full_path':'tenants/portal'},'path_with_namespace':'tenants/portal/platform-acceptance','archived':False,'default_branch':None}
      return self.response(503,{}) if state['uncertain'] else self.response(201,state['project'])
     assert self.path=='/api/v4/user/runners';assert body['project_id']==31 and body['paused'] and body['locked'] and not body['run_untagged'];assert body['tag_list']=='perkforge-portal-acceptance' and body['access_level']=='ref_protected'
     state['runner']={k:v for k,v in body.items() if k!='project_id'};state['runner'].update(id=22,tag_list=[body['tag_list']],projects=[{'id':31}])
     return self.response(503,{}) if state['runner_uncertain'] else self.response(201,{'id':22,'token':'glrt-SYNTHETIC_ONLY_123'})
   server=ThreadingHTTPServer(('127.0.0.1',0),H);ctx=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER);ctx.load_cert_chain(p/'ca',p/'key');server.socket=ctx.wrap_socket(server.socket,server_side=True);threading.Thread(target=server.serve_forever,daemon=True).start();self.addCleanup(server.server_close);self.addCleanup(server.shutdown)
   origin='https://localhost:'+str(server.server_port)
   def save(name,data):
    f=p/name;f.write_text(data if isinstance(data,str) else json.dumps(data));f.chmod(0o600);return str(f)
   token=save('token','SYNTHETIC-ONLY');group=save('group.json',{'stage':'group-ready','context':'portal','origin':origin,'group_id':9,'parent_id':7})
   v={'gitlab_acceptance_run':True,'gitlab_acceptance_scope':'tenant-acceptance-project-v1','gitlab_acceptance_context':'portal','gitlab_acceptance_origin':origin,'gitlab_acceptance_ca':str(p/'ca'),'gitlab_acceptance_source_revision':'a'*40,'gitlab_acceptance_group_receipt':group,'gitlab_acceptance_actor_id':8}
   if self.observed:
    v.pop('gitlab_acceptance_group_receipt')
    v['gitlab_acceptance_group_expectation']=group
    save('group.json',{'stage':'native-group-expectation-v1','context':'portal','origin':origin,'source_revision':'a'*40,'group_id':9,'parent_id':7})
   receipt=str(p/'project.json')
   def run(mode='--project',changes=None):
    f=save('inputs.json',{**v,**(changes or {})});out=subprocess.run(['bash',str(D/'run.sh'),mode,token,receipt if mode!='--runner' else str(p/'transaction.json'),f],capture_output=True,text=True,env={**os.environ,'ANSIBLE_LOCAL_TEMP':str(p/'local'),'ANSIBLE_REMOTE_TEMP':str(p/'remote')},timeout=90)
    self.assertNotIn('SYNTHETIC-ONLY',out.stdout+out.stderr);return out
   def ok(*a,**kw):
    x=run(*a,**kw);self.assertEqual(x.returncode,0,x.stdout+x.stderr)
   ok('--validate');self.assertEqual(state['writes'],[]);self.assertFalse(Path(receipt).exists())
   x=run(changes={'gitlab_acceptance_context':'{{ lookup("pipe","false") }}'});self.assertNotEqual(x.returncode,0);self.assertEqual(state['writes'],[])
   state['foreign']=True;self.assertNotEqual(run().returncode,0);self.assertEqual(state['writes'],[]);state['foreign']=False
   state['wrong_parent']=True;self.assertNotEqual(run().returncode,0);self.assertEqual(state['writes'],[]);state['wrong_parent']=False
   for flag in ['expired','foreign_authority']:
    state[flag]=True;self.assertNotEqual(run().returncode,0);self.assertEqual(state['writes'],[]);state[flag]=False
   if self.observed:
    self.assertNotEqual(run(changes={'gitlab_acceptance_group_receipt':group}).returncode,0)
    self.assertNotEqual(run(changes={'gitlab_acceptance_source_revision':'b'*40}).returncode,0)
    self.assertEqual(state['writes'],[])
   ok();self.assertEqual(len(state['writes']),1);ok();self.assertEqual(len(state['writes']),1)
   observed=json.loads(Path(receipt).read_text())['group_evidence']
   self.assertRegex(observed.pop('observed_at'),r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$')
   self.assertEqual(observed,{'kind':'fresh-native-group-observation-v1','group_id':9,'parent_id':7,'group_path':'tenants/portal','parent_path':'tenants','actor_id':8,'token_id':12,'gitlab_version':'19.4.2-ee'})
   rv={'gitlab_acceptance_scope':'tenant-acceptance-runner-v1','gitlab_acceptance_project_receipt':receipt,'gitlab_acceptance_runner_directory':str(rd)}
   self.assertNotEqual(run('--runner',rv).returncode,0);self.assertEqual(len(state['writes']),1)
   # Separate reviewed seed/protection is not performed by this adapter.
   state['project']['default_branch']='main'
   for flag in ['wrong_parent','branch_unsafe','other_runner','expired','foreign_authority']:
    state[flag]=True;self.assertNotEqual(run('--runner',rv).returncode,0);self.assertEqual(len(state['writes']),1);state[flag]=False
   state['project']['namespace']['id']=77;self.assertNotEqual(run('--runner',rv).returncode,0);self.assertEqual(len(state['writes']),1);state['project']['namespace']['id']=9
   bad=rd/'runner-receipt.json';bad.write_text('x'*65537);bad.chmod(0o600)
   self.assertNotEqual(run('--runner',rv).returncode,0);self.assertEqual(len(state['writes']),1);bad.unlink()
   os.link(group,bad);self.assertNotEqual(run('--runner',rv).returncode,0);self.assertEqual(len(state['writes']),1);bad.unlink()
   ok('--runner',rv);self.assertEqual(len(state['writes']),2);self.assertTrue(state['runner']['paused']);ok('--runner',rv);self.assertEqual(len(state['writes']),2)
   state['runner']['projects']=[{'id':1}];self.assertNotEqual(run('--runner',rv).returncode,0);self.assertEqual(len(state['writes']),2)
   self.assertTrue(all(path!='/api/v4/projects/31/runners' for path,_ in state['writes']))
   # A separate runner directory models lost one-time response: no auto-remint.
   uncertain_dir=p/'uncertain-runner';uncertain_dir.mkdir(mode=0o700)
   state['runner']=None;state['runner_uncertain']=True
   urv={**rv,'gitlab_acceptance_runner_directory':str(uncertain_dir)}
   self.assertNotEqual(run('--runner',urv).returncode,0);n=len(state['writes'])
   self.assertEqual(json.loads((uncertain_dir/'runner-receipt.json').read_text())['phase'],'creation-pending')
   self.assertFalse((uncertain_dir/'.registration-lock').exists())
   self.assertNotEqual(run('--runner',urv).returncode,0);self.assertEqual(len(state['writes']),n)
   # A distinct disposable fixture demonstrates uncertain POST preserves pending
   # intent and refuses automatic second creation; never reset a live receipt.
   receipt=str(p/'uncertain.json');state['project']=None;state['uncertain']=True
   self.assertNotEqual(run().returncode,0);n=len(state['writes'])
   self.assertEqual(json.loads(Path(receipt).read_text())['stage'],'creation-pending')
   self.assertNotEqual(run().returncode,0);self.assertEqual(len(state['writes']),n)

class NativeObservation(Preparation):
 observed=True

if __name__=='__main__':unittest.main()
