"""Real Ansible against synthetic HTTPS only; not live Keycloak authorization proof."""
import copy,json,os,shutil,ssl,subprocess,tempfile,threading,unittest
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit
import yaml
ROOT=Path(__file__).resolve().parents[2]
PLAY=ROOT/'configuration/authorization/foundation.yaml'
INV=ROOT/'configuration/ansible/inventory.yaml'
class FoundationDefaults(unittest.TestCase):
 def test_default_check_invalid_tenants_and_explicit_apply_gate(self):
  with tempfile.TemporaryDirectory() as d:
   env={**os.environ,'ANSIBLE_LOCAL_TEMP':d+'/local','ANSIBLE_REMOTE_TEMP':d+'/remote'}
   for extra,check,ok in [({},False,True),({'realm_foundation_apply':True},True,True),({'authorization_tenants':['a/b']},False,False),({'authorization_tenants':['a','a']},False,False),({'realm_foundation_apply':True},False,False)]:
    cmd=['ansible-playbook','-i',str(INV),str(PLAY),'-e',json.dumps(extra)]+(['--check'] if check else [])
    p=subprocess.run(cmd,env=env,capture_output=True,text=True,timeout=30);self.assertEqual(p.returncode==0,ok,p.stdout+p.stderr)
    if ok:self.assertIn('changed=0',p.stdout)
@unittest.skipUnless(os.environ.get('RUN_PLATFORM_CONFIG_TESTS') and shutil.which('ansible-playbook'),'enable isolated HTTPS fixture explicitly')
class FoundationAPI(unittest.TestCase):
 def setUp(self):
  t=tempfile.TemporaryDirectory();self.addCleanup(t.cleanup);self.d=Path(t.name)
  subprocess.run(['openssl','req','-x509','-newkey','rsa:2048','-nodes','-days','1','-subj','/CN=localhost','-addext','subjectAltName=DNS:localhost','-keyout',str(self.d/'key'),'-out',str(self.d/'ca')],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
  self.s={'realm':None,'groups':{},'mappings':{},'defaults':[],'writes':[],'calls':[],'fail_path':None,'deny':False,'shared_memberships':{'shared-user':['/tenants/a/admins','/tenants/b/viewers']}}
  state=self.s
  class Handler(BaseHTTPRequestHandler):
   def log_message(self,*a):pass
   def respond(self,code,obj=None):
    b=json.dumps(obj).encode() if obj is not None else b'';self.send_response(code);self.send_header('Content-Type','application/json');self.end_headers();self.wfile.write(b)
   def do_GET(self):
    p=urlsplit(self.path).path;state['calls'].append(('GET',p))
    if state['deny']:return self.respond(403,{})
    if p=='/auth/admin/realms/perkforge':return self.respond(200,state['realm']) if state['realm'] else self.respond(404,{})
    if p.endswith('/default-groups'):return self.respond(200,state['defaults'])
    if '/group-by-path/' in p:
     path=p.split('/group-by-path',1)[1];return self.respond(200,state['groups'][path]) if path in state['groups'] else self.respond(404,{})
    if p.endswith('/role-mappings'):return self.respond(200,state['mappings'].get(p.split('/')[-2],{}))
    return self.respond(404,{})
   def do_POST(self):
    p=urlsplit(self.path).path;raw=self.rfile.read(int(self.headers.get('Content-Length',0)));state['calls'].append(('POST',p))
    if p=='/auth/realms/master/protocol/openid-connect/token':return self.respond(200,{'access_token':'synthetic-foundation-session'})
    if state['deny']:return self.respond(403,{})
    value=json.loads(raw);state['writes'].append((p,copy.deepcopy(value)))
    if p=='/auth/admin/realms':
     state['realm']=copy.deepcopy(value);state['realm']['attributes']['server-default']='preserved';return self.respond(201)
    if p.endswith('/groups'):path='/'+value['name']
    elif p.endswith('/children'):
     parent=next(x for x in state['groups'].values() if x['id']==p.split('/')[-2]);path=parent['path']+'/'+value['name']
    else:return self.respond(400,{})
    if path==state['fail_path']:return self.respond(500,{})
    if path in state['groups']:return self.respond(409,{})
    assert set(value)=={'name','attributes'}
    state['groups'][path]={**value,'path':path,'id':'g-'+str(len(state['groups']))};return self.respond(201)
   def do_PUT(self):return self.respond(400,{})
   def do_DELETE(self):return self.respond(400,{})
  self.server=ThreadingHTTPServer(('127.0.0.1',0),Handler);ctx=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER);ctx.load_cert_chain(str(self.d/'ca'),str(self.d/'key'));self.server.socket=ctx.wrap_socket(self.server.socket,server_side=True);threading.Thread(target=self.server.serve_forever,daemon=True).start();self.addCleanup(self.server.server_close);self.addCleanup(self.server.shutdown)
  for n in ['username','password']:(self.d/n).write_text('synthetic-foundation-'+n);(self.d/n).chmod(0o600)
  bin=self.d/'bin';bin.mkdir();fake=bin/'kubectl';fake.write_text('#!/bin/sh\nprintf synthetic-physical-uid\n');fake.chmod(0o700)
  self.v={'realm_foundation_apply':True,'realm_foundation_recovery_preserved':True,'realm_foundation_url':f'https://localhost:{self.server.server_port}/auth','realm_foundation_ca':str(self.d/'ca'),'realm_foundation_username_file':str(self.d/'username'),'realm_foundation_password_file':str(self.d/'password'),'expected_cluster_uid':'synthetic-physical-uid','target_context':'fixture','target_kubeconfig':str(self.d/'not-a-real-kubeconfig'),'authorization_tenants':['a','b']}
 def run_play(self,**extra):
  p=subprocess.run(['ansible-playbook','-i',str(INV),str(PLAY),'-e',json.dumps({**self.v,**extra})],env={**os.environ,'PATH':str(self.d/'bin')+':'+os.environ['PATH'],'ANSIBLE_LOCAL_TEMP':str(self.d/'local'),'ANSIBLE_REMOTE_TEMP':str(self.d/'remote'),'ANSIBLE_NOCOLOR':'1'},capture_output=True,text=True,timeout=150)
  for marker in ['synthetic-foundation-username','synthetic-foundation-password','synthetic-foundation-session']:self.assertNotIn(marker,p.stdout+p.stderr)
  return p
 def test_create_idempotent_inspect_partial_resume_and_no_authority_assignments(self):
  self.s['fail_path']='/platform/viewers';p=self.run_play();self.assertNotEqual(p.returncode,0);self.assertIn('/platform/admins',self.s['groups']);self.assertNotIn('/platform/viewers',self.s['groups'])
  before=copy.deepcopy(self.s['writes']);self.s['fail_path']=None;p=self.run_play();self.assertEqual(p.returncode,0,p.stdout+p.stderr)
  self.assertEqual(len(self.s['groups']),13);self.assertEqual(self.s['shared_memberships'],{'shared-user':['/tenants/a/admins','/tenants/b/viewers']})
  for g in self.s['groups'].values():self.assertNotIn('realmRoles',g);self.assertNotIn('clientRoles',g)
  realm=self.s['realm'];self.assertFalse(realm['registrationAllowed']);self.assertNotIn('users',realm);self.assertNotIn('clients',realm);self.assertNotIn('roles',realm)
  before=copy.deepcopy(self.s['writes']);p=self.run_play();self.assertEqual(p.returncode,0,p.stdout+p.stderr);self.assertEqual(self.s['writes'],before);self.assertIn('changed=0',p.stdout)
  p=self.run_play(realm_foundation_apply=False,realm_foundation_inspect=True);self.assertEqual(p.returncode,0,p.stdout+p.stderr);self.assertEqual(self.s['writes'],before)
  self.assertFalse(any('/users' in path or '/clients' in path for _,path in self.s['calls']))
  # Existing role mappings are a conflict, never deleted or expanded by foundation.
  admin=self.s['groups']['/platform/admins'];self.s['mappings'][admin['id']]={'realmMappings':[{'name':'realm-admin'}]};p=self.run_play();self.assertNotEqual(p.returncode,0);self.assertEqual(self.s['writes'],before)
  self.s['mappings']={};self.s['defaults']=[{'path':'/platform/admins'}];p=self.run_play();self.assertNotEqual(p.returncode,0);self.assertEqual(self.s['writes'],before)
  self.s['defaults']=[];self.s['groups']['/tenants/b/viewers']['attributes']={};p=self.run_play();self.assertNotEqual(p.returncode,0);self.assertEqual(self.s['writes'],before)
 def test_refuse_unowned_realm_tls_auth_and_target_mismatch_before_mutation(self):
  self.s['realm']={'realm':'perkforge','attributes':{'perkforge-managed':'false'}};p=self.run_play();self.assertNotEqual(p.returncode,0);self.assertEqual(self.s['writes'],[])
  self.s['realm']=None;self.s['deny']=True;p=self.run_play();self.assertNotEqual(p.returncode,0);self.assertEqual(self.s['writes'],[])
  self.s['deny']=False;p=self.run_play(expected_cluster_uid='other-cluster');self.assertNotEqual(p.returncode,0);self.assertEqual(self.s['writes'],[])
  wrong=self.d/'wrong-ca';subprocess.run(['openssl','req','-x509','-newkey','rsa:2048','-nodes','-days','1','-subj','/CN=wrong','-keyout',str(self.d/'wrong-key'),'-out',str(wrong)],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
  p=self.run_play(realm_foundation_ca=str(wrong));self.assertNotEqual(p.returncode,0);self.assertEqual(self.s['writes'],[])
