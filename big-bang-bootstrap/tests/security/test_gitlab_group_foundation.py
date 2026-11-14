"""Actual Ansible with synthetic HTTPS; no installed GitLab or credentials."""
import copy,json,os,ssl,subprocess,tempfile,threading,unittest,fcntl,importlib.util,time
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote,urlsplit
ROOT=Path(__file__).resolve().parents[2]
PLAY=ROOT/'configuration/packages/gitlab/enrollment/ensure-groups.yaml'
class GroupFoundation(unittest.TestCase):
 def test_custody_path_negative_cases(self):
  spec=importlib.util.spec_from_file_location('group_paths',PLAY.parent/'verify_group_paths.py');guard=importlib.util.module_from_spec(spec);spec.loader.exec_module(guard)
  with tempfile.TemporaryDirectory() as directory:
   d=Path(directory);d.chmod(0o700);p=d/'value';p.write_text('synthetic');p.chmod(0o600);guard.safe(str(p))
   d.chmod(0o770)
   with self.assertRaises(ValueError):guard.safe(str(p))
   d.chmod(0o700);link=d/'link';link.symlink_to(p)
   with self.assertRaises(ValueError):guard.safe(str(link))
   link.unlink();os.link(p,link)
   with self.assertRaises(ValueError):guard.safe(str(p))
   link.unlink();fifo=d/'fifo';os.mkfifo(fifo,0o600)
   with self.assertRaises(ValueError):guard.safe(str(fifo))
   with self.assertRaises(ValueError):guard.safe(str(p),limit=1)
   alias=d/'alias';alias.symlink_to(d,target_is_directory=True)
   with self.assertRaises(ValueError):guard.safe(str(alias/'value'))
 def test_native_protocol_and_fail_closed_state(self):
  with tempfile.TemporaryDirectory() as directory:
   d=Path(directory);d.chmod(0o700)
   subprocess.run(['openssl','req','-x509','-newkey','rsa:2048','-nodes','-days','1','-subj','/CN=localhost','-addext','subjectAltName=DNS:localhost','-keyout',str(d/'key'),'-out',str(d/'ca')],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
   state={'groups':{},'calls':[],'next':10,'post_status':201}
   class Handler(BaseHTTPRequestHandler):
    def log_message(self,*args):pass
    def reply(self,status,body):
     self.send_response(status);self.send_header('Content-Type','application/json');self.end_headers();self.wfile.write(json.dumps(body).encode())
    def do_GET(self):
     state['calls'].append(('GET',self.path));path=unquote(urlsplit(self.path).path)
     if self.headers.get('PRIVATE-TOKEN')!='SYNTHETIC-GROUP-TOKEN':return self.reply(403,{})
     if path=='/api/v4/version':return self.reply(200,{'version':'19.4.2-ee'})
     key=path.removeprefix('/api/v4/groups/');group=next((v for k,v in state['groups'].items() if k==key or str(v['id'])==key),None)
     self.reply(200 if group else 404,group or {})
    def do_POST(self):
     body=json.loads(self.rfile.read(int(self.headers['Content-Length'])));state['calls'].append(('POST',self.path))
     if state['post_status']!=201:return self.reply(state['post_status'],{})
     assert self.path=='/api/v4/groups';assert body['visibility']=='private';assert body['request_access_enabled'] is False
     parent=body.get('parent_id')
     if parent is not None and state.get('fail_child'):return self.reply(503,{})
     path=body['path'] if parent is None else 'tenants/'+body['path']
     if path in state['groups']:return self.reply(409,{})
     state['next']+=1;group={**body,'id':state['next'],'full_path':path,'parent_id':parent};state['groups'][path]=group;self.reply(201,group)
    def do_DELETE(self):raise AssertionError('No deletion allowed')
    do_PUT=do_PATCH=do_DELETE
   server=ThreadingHTTPServer(('127.0.0.1',0),Handler);ctx=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER);ctx.load_cert_chain(d/'ca',d/'key');server.socket=ctx.wrap_socket(server.socket,server_side=True)
   threading.Thread(target=server.serve_forever,daemon=True).start();self.addCleanup(server.server_close);self.addCleanup(server.shutdown)
   token=d/'token';token.write_text('SYNTHETIC-GROUP-TOKEN');token.chmod(0o600);receipt=d/'receipt.json'
   vals={'gitlab_group_run':True,'gitlab_group_scope':'gitlab-enrollment-group-foundation-v1','gitlab_group_context':'example','gitlab_group_source_revision':'a'*40,'gitlab_group_allow_parent_create':True,'gitlab_native_origin':'https://localhost:'+str(server.server_port),'gitlab_native_ca_file':str(d/'ca')}
   def run(extra=None,check=False):
    state['calls']=[];vf=d/'vars.json';vf.write_text(json.dumps(vals| (extra or {})));vf.chmod(0o600)
    command=['ansible-playbook','-i','localhost,',str(PLAY),'-e','@'+str(vf)]+(['--check'] if check else []) if check or not (vals|(extra or {}))['gitlab_group_run'] else [str(PLAY.parent/'run-groups.sh'),'--apply',str(token),str(receipt),str(vf)]
    p=subprocess.run(command,capture_output=True,text=True,timeout=60,env=os.environ|{'ANSIBLE_LOCAL_TEMP':str(d/'ansible')})
    self.assertNotIn('SYNTHETIC-GROUP-TOKEN',p.stdout+p.stderr);return p
   vf=d/'validate-inputs.json';vf.write_text(json.dumps(vals));vf.chmod(0o600)
   p=subprocess.run([str(PLAY.parent/'run-groups.sh'),'--validate',str(token),str(receipt),str(vf)],capture_output=True,text=True);self.assertEqual(p.returncode,0,p.stdout+p.stderr);self.assertFalse(receipt.exists());self.assertFalse(Path(str(receipt)+'.lock').exists());self.assertEqual(state['calls'],[])
   for extra,check in [({'gitlab_group_run':False},False),({},True)]:
    p=run(extra,check);self.assertEqual(p.returncode,0,p.stdout+p.stderr);self.assertEqual(state['calls'],[]);self.assertFalse(receipt.exists())
   for forbidden in ['group_prior','group_headers','ansible_connection','ansible_python_interpreter','gitlab_native_token_file','gitlab_group_receipt_file']:
    p=run({forbidden:'untrusted'});self.assertNotEqual(p.returncode,0);self.assertEqual(state['calls'],[])
   marker=d/'must-not-execute'
   for key in ['gitlab_group_context','gitlab_group_source_revision','gitlab_native_origin','gitlab_native_ca_file']:
    p=run({key:"{{ lookup('pipe', 'touch "+str(marker)+"') }}"});self.assertNotEqual(p.returncode,0);self.assertEqual(state['calls'],[]);self.assertFalse(marker.exists())
   for key,value in [('gitlab_group_run','true'),('gitlab_group_expected_parent_id',True),('gitlab_group_context',{'unsafe':'nested'})]:
    p=run({key:value});self.assertNotEqual(p.returncode,0);self.assertEqual(state['calls'],[])
   vf=d/'duplicate.json';vf.write_text('{"gitlab_group_run":false,"gitlab_group_run":true}');vf.chmod(0o600)
   p=subprocess.run([str(PLAY.parent/'run-groups.sh'),'--validate',str(token),str(receipt),str(vf)],capture_output=True,text=True);self.assertNotEqual(p.returncode,0);self.assertEqual(state['calls'],[])
   (d/'ca').chmod(0o666);p=run();self.assertNotEqual(p.returncode,0);self.assertEqual(state['calls'],[]);(d/'ca').chmod(0o644)
   p=run({'gitlab_group_allow_parent_create':False});self.assertNotEqual(p.returncode,0);self.assertFalse(any(m=='POST' for m,_ in state['calls']))
   p=run();self.assertEqual(p.returncode,0,p.stdout+p.stderr);self.assertEqual(sum(m=='POST' for m,_ in state['calls']),2)
   with open(str(receipt)+'.lock','r+') as lock:
    fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);p=run();self.assertNotEqual(p.returncode,0);self.assertEqual(state['calls'],[])
   holder=subprocess.Popen(['flock','--no-fork','--exclusive','--nonblock',str(receipt)+'.lock','sleep','20'])
   try:
    for _ in range(40):
     if any(' '+str(holder.pid)+' ' in line for line in Path('/proc/locks').read_text().splitlines()):break
     time.sleep(.05)
    else:self.fail('fixture holder never acquired lock')
    state['calls']=[];vf=d/'vars.json';vf.write_text(json.dumps(vals));vf.chmod(0o600)
    p=subprocess.run(['ansible-playbook','-i','localhost,',str(PLAY),'-e','@'+str(vf),'-e','gitlab_native_token_file='+str(token),'-e','gitlab_group_receipt_file='+str(receipt)],capture_output=True,text=True,timeout=30,env=os.environ|{'PERKFORGE_GROUP_LOCK_OWNER':str(holder.pid),'ANSIBLE_LOCAL_TEMP':str(d/'ansible')})
    self.assertNotEqual(p.returncode,0);self.assertEqual(state['calls'],[])
   finally:holder.terminate();holder.wait(timeout=5)
   saved=json.loads(receipt.read_text());self.assertEqual(saved['stage'],'group-ready');self.assertEqual(set(saved),{'schema','origin','context','source_revision','parent_id','group_id','stage','previous_revisions'})
   groups=copy.deepcopy(state['groups']);p=run();self.assertEqual(p.returncode,0,p.stdout+p.stderr);self.assertFalse(any(m=='POST' for m,_ in state['calls']));self.assertEqual(json.loads(receipt.read_text()),saved)
   for key,value in [('visibility','public'),('parent_id',999),('id',999),('full_path','tenants/foreign')]:
    state['groups']=copy.deepcopy(groups);state['groups']['tenants/example'][key]=value;p=run();self.assertNotEqual(p.returncode,0);self.assertFalse(any(m=='POST' for m,_ in state['calls']))
   state['groups']=copy.deepcopy(groups)
   state['groups']['tenants']['visibility']='public';p=run();self.assertNotEqual(p.returncode,0);self.assertFalse(any(m=='POST' for m,_ in state['calls']))
   state['groups']=copy.deepcopy(groups)
   p=run({'gitlab_group_source_revision':'b'*40});self.assertNotEqual(p.returncode,0);self.assertEqual(state['calls'],[])
   p=run({'gitlab_group_source_revision':'b'*40,'gitlab_group_previous_revision':'c'*40});self.assertNotEqual(p.returncode,0);self.assertEqual(state['calls'],[])
   state['groups']['tenants/example']['visibility']='public';p=run({'gitlab_group_source_revision':'b'*40,'gitlab_group_previous_revision':'a'*40});self.assertNotEqual(p.returncode,0);self.assertEqual(json.loads(receipt.read_text())['source_revision'],'a'*40)
   state['groups']=copy.deepcopy(groups);p=run({'gitlab_group_source_revision':'b'*40,'gitlab_group_previous_revision':'a'*40});self.assertEqual(p.returncode,0,p.stdout+p.stderr);self.assertFalse(any(m=='POST' for m,_ in state['calls']));transition=json.loads(receipt.read_text());self.assertEqual(transition['source_revision'],'b'*40);self.assertEqual(transition['previous_revisions'],['a'*40]);self.assertEqual(transition['group_id'],saved['group_id'])
   capped=copy.deepcopy(transition);capped['previous_revisions']=[format(i,'040x') for i in range(32)];receipt.write_text(json.dumps(capped));p=run({'gitlab_group_source_revision':'b'*40});self.assertEqual(p.returncode,0,p.stdout+p.stderr)
   p=run({'gitlab_group_source_revision':'c'*40,'gitlab_group_previous_revision':'b'*40});self.assertNotEqual(p.returncode,0);self.assertEqual(state['calls'],[]);self.assertEqual(json.loads(receipt.read_text()),capped)
   receipt.unlink();p=run();self.assertNotEqual(p.returncode,0);self.assertFalse(any(m=='POST' for m,_ in state['calls']))
   p=run({'gitlab_group_expected_parent_id':groups['tenants']['id']});self.assertNotEqual(p.returncode,0);self.assertFalse(any(m=='POST' for m,_ in state['calls']))
   del state['groups']['tenants/example'];p=run({'gitlab_group_expected_parent_id':groups['tenants']['id'],'gitlab_group_allow_parent_create':False});self.assertEqual(p.returncode,0,p.stdout+p.stderr);self.assertEqual(sum(m=='POST' for m,_ in state['calls']),1)
   receipt.unlink();state['groups']={};state['fail_child']=True;p=run();self.assertNotEqual(p.returncode,0);self.assertEqual(json.loads(receipt.read_text())['stage'],'parent-ready');self.assertEqual(len(state['groups']),1)
   state['fail_child']=False;p=run({'gitlab_group_allow_parent_create':False});self.assertEqual(p.returncode,0,p.stdout+p.stderr);self.assertEqual(sum(m=='POST' for m,_ in state['calls']),1)
   receipt.unlink();state['groups']={};state['post_status']=409;p=run();self.assertNotEqual(p.returncode,0);self.assertEqual(json.loads(receipt.read_text())['stage'],'pending')
   receipt.unlink();state['post_status']=201;token.chmod(0o644);p=run();self.assertNotEqual(p.returncode,0);self.assertEqual(state['calls'],[]);token.chmod(0o600)
   outside=d/'outside';outside.write_text('{}');receipt.symlink_to(outside);p=run();self.assertNotEqual(p.returncode,0);self.assertEqual(state['calls'],[]);self.assertEqual(outside.read_text(),'{}')
if __name__=='__main__':unittest.main()
