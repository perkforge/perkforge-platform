"""Actual Ansible/synthetic TLS only; never create real repositories or pipelines."""
import base64,json,os,ssl,subprocess,tempfile,threading,unittest
from pathlib import Path
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from urllib.parse import urlsplit,unquote
ROOT=Path(__file__).resolve().parents[2];D=ROOT/'configuration/packages/gitlab/enrollment/acceptance'
class Seed(unittest.TestCase):
 def test_native_seed_protect_repeat_and_uncertainty(self):
  with tempfile.TemporaryDirectory(prefix='acceptance-seed-') as tmp:
   p=Path(tmp);p.chmod(0o700)
   subprocess.run(['openssl','req','-x509','-newkey','rsa:2048','-nodes','-days','1','-subj','/CN=localhost','-addext','subjectAltName=DNS:localhost','-keyout',str(p/'key'),'-out',str(p/'ca')],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL);(p/'ca').chmod(0o644)
   state={'files':{},'sha':None,'protection':None,'writes':[],'loss':None,'foreign':False,'unsafe':False,'auto':False,'ci':False,'renamed':False}
   def protection():return {'id':55,'name':'main','allow_force_push':False,'push_access_levels':[{'access_level':40}],'merge_access_levels':[{'access_level':40}]}
   def project():return {'id':31,'path_with_namespace':'foreign/path' if state['renamed'] else 'tenants/portal/platform-acceptance','namespace':{'id':9,'full_path':'tenants/portal'},'visibility':'private','archived':False,'builds_access_level':'enabled' if state['ci'] else 'disabled','shared_runners_enabled':False,'group_runners_enabled':False,'auto_devops_enabled':False,'empty_repo':state['sha'] is None,'default_branch':'main' if state['sha'] else None}
   class H(BaseHTTPRequestHandler):
    def log_message(self,*a):pass
    def reply(self,c,v):self.send_response(c);self.send_header('Content-Type','application/json');self.end_headers();self.wfile.write(json.dumps(v).encode())
    def do_GET(self):
     if self.headers.get('PRIVATE-TOKEN')!='SYNTHETIC-ONLY':return self.reply(403,{})
     path=unquote(urlsplit(self.path).path)
     token={'id':12,'user_id':8,'active':True,'revoked':False,'scopes':['api'],'expires_at':'2099-01-01','access_level':50}
     if path=='/api/v4/user':return self.reply(200,{'id':8,'bot':True,'state':'active'})
     if path=='/api/v4/personal_access_tokens/self':return self.reply(200,token)
     if path=='/api/v4/version':return self.reply(200,{'version':'19.4.2-ee'})
     if path=='/api/v4/groups/7/members/8':return self.reply(200,{'id':8,'access_level':50})
     if path=='/api/v4/groups/7/access_tokens/12':return self.reply(200,token)
     if path=='/api/v4/groups/7':return self.reply(200,{'id':7,'full_path':'tenants','visibility':'private'})
     if path=='/api/v4/groups/9':return self.reply(200,{'id':9,'parent_id':7,'full_path':'tenants/portal','visibility':'private'})
     if path=='/api/v4/projects/31':return self.reply(200,project())
     if path.endswith('/repository/branches'):return self.reply(200,[{'name':'main'}] if state['sha'] or state['foreign'] else [])
     if path.endswith('/protected_branches'):return self.reply(200,[state['protection']] if state['protection'] else [])
     if path.endswith('/repository/branches/main'):return self.reply(200,{'name':'main','commit':{'id':state['sha']}})
     if path.endswith('/repository/tree'):return self.reply(200,[{'path':n,'type':'blob','mode':'100644'} for n in state['files']])
     if '/repository/files/' in path:
      name=path.split('/repository/files/')[1];return self.reply(200,{'file_path':name,'encoding':'base64','commit_id':state['sha'],'content':base64.b64encode(state['files'][name].encode()).decode()})
     if path.endswith('/protected_branches/main'):return self.reply(200,state['protection']) if state['protection'] else self.reply(404,{})
     return self.reply(404,{})
    def do_POST(self):
     assert self.headers.get('PRIVATE-TOKEN')=='SYNTHETIC-ONLY'
     body=json.loads(self.rfile.read(int(self.headers['Content-Length'])));state['writes'].append(self.path)
     if self.path.endswith('/repository/commits'):
      assert body['branch']=='main' and body['force'] is False and '[skip ci]' in body['commit_message']
      assert len(body['actions'])==3 and all(a['action']=='create' for a in body['actions'])
      state['files']={a['file_path']:a['content'] for a in body['actions']};state['sha']='b'*40
      if state['auto']:state['protection']=protection()
      return self.reply(503,{}) if state['loss']=='seed' else self.reply(201,{'id':state['sha']})
     assert self.path.endswith('/protected_branches');assert body=={'name':'main','push_access_level':40,'merge_access_level':40,'allow_force_push':False}
     state['protection']=protection()
     return self.reply(503,{}) if state['loss']=='protect' else self.reply(201,state['protection'])
   server=ThreadingHTTPServer(('127.0.0.1',0),H);ctx=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER);ctx.load_cert_chain(p/'ca',p/'key');server.socket=ctx.wrap_socket(server.socket,server_side=True);threading.Thread(target=server.serve_forever,daemon=True).start();self.addCleanup(server.server_close);self.addCleanup(server.shutdown)
   def save(name,v):
    f=p/name;f.write_text(v if isinstance(v,str) else json.dumps(v));f.chmod(0o600);return str(f)
   origin='https://localhost:'+str(server.server_port);token=save('token','SYNTHETIC-ONLY');group=save('group.json',{'stage':'group-ready','context':'portal','origin':origin,'group_id':9,'parent_id':7})
   pr=save('project.json',{'stage':'project-ready','context':'portal','origin':origin,'group_id':9,'project_id':31,'source_revision':'a'*40})
   v={'gitlab_acceptance_run':True,'gitlab_acceptance_scope':'tenant-acceptance-seed-v1','gitlab_acceptance_context':'portal','gitlab_acceptance_origin':origin,'gitlab_acceptance_ca':str(p/'ca'),'gitlab_acceptance_source_revision':'a'*40,'gitlab_acceptance_group_receipt':group,'gitlab_acceptance_project_receipt':pr,'gitlab_acceptance_actor_id':8}
   receipt=str(p/'seed.json');vf=save('inputs.json',v)
   def run(mode='--seed'):
    r=subprocess.run(['bash',str(D/'run.sh'),mode,token,receipt,vf],capture_output=True,text=True,timeout=90,env={**os.environ,'ANSIBLE_LOCAL_TEMP':str(p/'local'),'ANSIBLE_REMOTE_TEMP':str(p/'remote')});self.assertNotIn('SYNTHETIC-ONLY',r.stdout+r.stderr);return r
   def ok():
    r=run();self.assertEqual(r.returncode,0,r.stdout+r.stderr)
   self.assertEqual(run('--validate').returncode,0);self.assertEqual(state['writes'],[])
   state['foreign']=True;self.assertNotEqual(run().returncode,0);self.assertEqual(state['writes'],[]);state['foreign']=False
   state['ci']=True;self.assertNotEqual(run().returncode,0);self.assertEqual(state['writes'],[]);state['ci']=False
   ok();self.assertEqual(len(state['writes']),2);self.assertEqual(json.loads(Path(receipt).read_text())['stage'],'SeedReady');ok();self.assertEqual(len(state['writes']),2)
   state['renamed']=True;self.assertNotEqual(run().returncode,0);state['renamed']=False
   original=state['files']['README.md'];state['files']['README.md']='foreign';self.assertNotEqual(run().returncode,0);state['files']['README.md']=original
   state['protection']['allow_force_push']=True;self.assertNotEqual(run().returncode,0);state['protection']['allow_force_push']=False
   for loss in ['seed','protect',None]:
    # New isolated synthetic project state and receipt, not a runtime reset.
    receipt=str(p/('seed-'+str(loss)+'.json'));state.update(files={},sha=None,protection=None,loss=loss,auto=loss is None)
    before=len(state['writes'])
    if loss:
     self.assertNotEqual(run().returncode,0);self.assertIn(json.loads(Path(receipt).read_text())['stage'],['seed-pending','protection-pending']);n=len(state['writes']);self.assertNotEqual(run().returncode,0);self.assertEqual(len(state['writes']),n)
    else:
     ok();self.assertEqual(len(state['writes']),before+1);ok();self.assertEqual(len(state['writes']),before+1)
 def test_fixed_ci_and_smoke_allowlist(self):
  import yaml,importlib.util
  ci=yaml.safe_load((D/'seed/gitlab-ci.yml').read_text());self.assertEqual(ci['workflow']['rules'][-1],{'when':'never'});self.assertIn('"web"',ci['workflow']['rules'][0]['if']);self.assertIn('CI_COMMIT_REF_PROTECTED',ci['workflow']['rules'][0]['if']);self.assertEqual(ci['variables']['ACCEPTANCE_OUTCOME']['options'],['success','failure'])
  spec=importlib.util.spec_from_file_location('acceptance_smoke',D/'seed/smoke.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
  from unittest.mock import patch
  with tempfile.TemporaryDirectory() as tmp:
   old=os.getcwd();os.chdir(tmp)
   try:
    with patch.dict(os.environ,{'ACCEPTANCE_OUTCOME':'not-allowed'}):
     with self.assertRaises(SystemExit):m.main()
    with patch.dict(os.environ,{'ACCEPTANCE_OUTCOME':'success'}),patch.object(m.os,'geteuid',return_value=0):
     with self.assertRaises(SystemExit):m.main()
    for outcome, expected in [('success',0),('failure',1)]:
     with patch.dict(os.environ,{'ACCEPTANCE_OUTCOME':outcome}),patch.object(m.os,'geteuid',return_value=1001),patch.object(m.Path,'read_text',return_value='CapEff:\t0000000000000000\n'),patch.object(m.Path,'exists',return_value=False):
      self.assertEqual(m.main(),expected)
      with self.assertRaises(FileExistsError):m.main()
     self.assertEqual(Path('acceptance.txt').read_text(),'Platform acceptance: '+outcome+'\n');Path('acceptance.txt').unlink()
    for caps, token in [('0000000000000001',False),('0000000000000000',True)]:
     with patch.dict(os.environ,{'ACCEPTANCE_OUTCOME':'success'}),patch.object(m.os,'geteuid',return_value=1001),patch.object(m.Path,'read_text',return_value='CapEff:\t'+caps+'\n'),patch.object(m.Path,'exists',return_value=token):
      with self.assertRaises(SystemExit):m.main()
   finally:os.chdir(old)
if __name__=='__main__':unittest.main()
