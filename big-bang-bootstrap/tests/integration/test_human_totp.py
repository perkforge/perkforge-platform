"""Real Ansible, synthetic HTTPS API only. Structural MFA tests are not real logins."""
import copy,json,os,shutil,ssl,subprocess,tempfile,threading,unittest
from pathlib import Path
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from urllib.parse import urlsplit,parse_qs
ROOT=Path(__file__).resolve().parents[2];PLAY=ROOT/'configuration/authorization/enroll-human.yaml';INV=ROOT/'configuration/ansible/inventory.yaml'
class HumanDefaults(unittest.TestCase):
 def test_new_and_legacy_default_check_and_wrong_profile_never_enroll(self):
  with tempfile.TemporaryDirectory() as d:
   env={**os.environ,'ANSIBLE_LOCAL_TEMP':d+'/local','ANSIBLE_REMOTE_TEMP':d+'/remote'}
   for play,extra,check,ok in [(PLAY,{},False,True),(PLAY,{'human_apply':True},True,True),(PLAY,{'human_apply':True,'impact_profile':'il5'},False,False),(ROOT/'configuration/ansible/platform-config/enroll-platform-admin.yaml',{},False,True)]:
    p=subprocess.run(['ansible-playbook','-i',str(INV) if play==PLAY else 'localhost,',str(play),'-e',json.dumps(extra)]+(['--check'] if check else []),env=env,capture_output=True,text=True,timeout=30)
    self.assertEqual(p.returncode==0,ok,p.stdout+p.stderr)
    if ok:self.assertIn('changed=0',p.stdout)
@unittest.skipUnless(os.environ.get('RUN_PLATFORM_CONFIG_TESTS') and shutil.which('ansible-playbook'),'enable isolated HTTPS fixture explicitly')
class HumanAPI(unittest.TestCase):
 def setUp(self):
  t=tempfile.TemporaryDirectory();self.addCleanup(t.cleanup);self.d=Path(t.name)
  subprocess.run(['openssl','req','-x509','-newkey','rsa:2048','-nodes','-days','1','-subj','/CN=localhost','-addext','subjectAltName=DNS:localhost','-keyout',str(self.d/'key'),'-out',str(self.d/'ca')],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
  self.s={'realm':{'realm':'perkforge','attributes':{'perkforge-managed':'true','perkforge-purpose':'realm-foundation-v1'},'registrationEmailAsUsername':False,'otpPolicyType':'totp','browserFlow':'browser','unrelated':'preserve'},'flows':{},'execs':{},'user':None,'members':[],'userRoles':{'realmMappings':[{'name':'default-roles-perkforge'}]},'groupRoles':{},'parentRoles':{},'writes':[],'calls':[]}
  state=self.s
  def executions(alias,level=0):
   out=[]
   for index,e in enumerate(state['execs'].get(alias,[])):
    out.append({**e,'level':level,'index':index})
    if e.get('authenticationFlow',False):out.extend(executions(e['displayName'],level+1))
   return out
  class Handler(BaseHTTPRequestHandler):
   def log_message(self,*a):pass
   def respond(self,code,obj=None):
    b=json.dumps(obj).encode() if obj is not None else b'';self.send_response(code);self.send_header('Content-Type','application/json');self.end_headers();self.wfile.write(b)
   def do_GET(self):
    parsed=urlsplit(self.path);p=parsed.path;state['calls'].append(('GET',p))
    if p=='/auth/admin/realms/perkforge':return self.respond(200,state['realm'])
    if p.endswith('/users/count'):return self.respond(200,1 if state['user'] else 0)
    if p.endswith('/users'):
     return self.respond(200,[state['user']] if state['user'] and parse_qs(parsed.query).get('username')==[state['user']['username']] else [])
    if p.endswith('/default-groups'):return self.respond(200,[])
    if p.endswith('/authentication/required-actions'):return self.respond(200,[{'alias':x,'enabled':True} for x in ['UPDATE_PASSWORD','CONFIGURE_TOTP','VERIFY_PROFILE']])
    if p.endswith('/group-by-path/platform/admins'):return self.respond(200,{'id':'admin-group','path':'/platform/admins','attributes':{'perkforge-managed':['true'],'perkforge-foundation':['v1'],'perkforge-role':['platform-admin']}})
    if p.endswith('/group-by-path/platform'):return self.respond(200,{'id':'parent-group','path':'/platform','attributes':{'perkforge-managed':['true'],'perkforge-foundation':['v1']}})
    if p.endswith('/groups/admin-group/role-mappings'):return self.respond(200,state['groupRoles'])
    if p.endswith('/groups/parent-group/role-mappings'):return self.respond(200,state['parentRoles'])
    if p.endswith('/clients'):return self.respond(200,[{'clientId':x,'id':x+'-id','authenticationFlowBindingOverrides':{}} for x in ['account','account-console','admin-cli','broker','realm-management','security-admin-console']])
    if p.endswith('/roles/default-roles-perkforge/composites'):return self.respond(200,[{'id':'self','name':'offline_access','clientRole':False,'composite':False},{'id':'account-manage','name':'manage-account','clientRole':True,'containerId':'account-id','composite':True}])
    if p.endswith('/roles-by-id/account-manage/composites'):return self.respond(200,[{'name':'manage-account-links','clientRole':True,'containerId':'account-id','composite':False}])
    if p.endswith('/authentication/flows'):return self.respond(200,list(state['flows'].values()))
    if '/authentication/flows/' in p and p.endswith('/executions'):return self.respond(200,executions(p.split('/')[-2]))
    if p.endswith('/users/owned-human/groups'):return self.respond(200,state['members'])
    if p.endswith('/users/owned-human/role-mappings'):return self.respond(200,state['userRoles'])
    return self.respond(404,{})
   def do_POST(self):self.mutate()
   def do_PUT(self):self.mutate()
   def mutate(self):
    p=urlsplit(self.path).path;raw=self.rfile.read(int(self.headers.get('Content-Length',0)));state['calls'].append((self.command,p))
    if p.endswith('/realms/master/protocol/openid-connect/token'):return self.respond(200,{'access_token':'synthetic-human-admin-session'})
    value=json.loads(raw) if raw else {};state['writes'].append((self.command,p,copy.deepcopy(value)))
    if p.endswith('/authentication/flows'):
     alias=value['alias'];state['flows'][alias]={**value,'id':'flow-'+str(len(state['flows']))};state['execs'][alias]=[];return self.respond(201)
    if '/authentication/flows/' in p:
     tail=p.split('/authentication/flows/',1)[1];alias=tail.split('/')[0]
     if p.endswith('/executions/execution'):
      e={'id':'exec-'+str(sum(len(v) for v in state['execs'].values())),'providerId':value['provider'],'requirement':'REQUIRED' if value['provider']=='auth-username-password-form' else 'DISABLED'};state['execs'][alias].append(e);return self.respond(201)
     if p.endswith('/executions/flow'):
      child=value['alias'];state['flows'][child]={'alias':child,'id':'flow-'+str(len(state['flows'])),'description':value['description'],'providerId':value['type'],'builtIn':False,'topLevel':False};state['execs'][child]=[]
      e={'id':'exec-'+str(sum(len(v) for v in state['execs'].values())),'authenticationFlow':True,'displayName':child,'flowId':state['flows'][child]['id'],'requirement':'DISABLED'};state['execs'][alias].append(e);return self.respond(201)
     if p.endswith('/executions'):
      e=next(e for e in state['execs'][alias] if e['id']==value['id']);e['requirement']=value['requirement'];return self.respond(204)
    if p=='/auth/admin/realms/perkforge':
     assert set(value)=={'browserFlow'};state['realm'].update(value);return self.respond(204)
    if p.endswith('/users'):
     state['user']={k:v for k,v in value.items() if k!='credentials'};state['user']['id']='owned-human';return self.respond(201)
    if p.endswith('/users/owned-human/groups/admin-group'):state['members']=[{'id':'admin-group','path':'/platform/admins'}];return self.respond(204)
    return self.respond(400,{})
  self.server=ThreadingHTTPServer(('127.0.0.1',0),Handler);ctx=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER);ctx.load_cert_chain(str(self.d/'ca'),str(self.d/'key'));self.server.socket=ctx.wrap_socket(self.server.socket,server_side=True);threading.Thread(target=self.server.serve_forever,daemon=True).start();self.addCleanup(self.server.server_close);self.addCleanup(self.server.shutdown)
  for n in ['admin-username','admin-password','initial-password']:(self.d/n).write_text('synthetic-human-private-'+n+'-12345678901234567890123456789012');(self.d/n).chmod(0o600)
  custody=self.d/'custody';custody.mkdir(mode=0o700);b=self.d/'bin';b.mkdir();f=b/'kubectl';f.write_text('#!/bin/sh\nprintf synthetic-target\n');f.chmod(0o700)
  self.v={'human_apply':True,'human_username':'person@lab.example.invalid','human_mfa_scope':'perkforge-browser','human_recovery_preserved':True,'human_url':f'https://localhost:{self.server.server_port}/auth','human_ca_file':str(self.d/'ca'),'human_admin_username_file':str(self.d/'admin-username'),'human_admin_password_file':str(self.d/'admin-password'),'human_initial_password_file':str(self.d/'initial-password'),'human_record_file':str(custody/'user.json'),'target_context':'fixture','target_kubeconfig':str(self.d/'fake-kubeconfig'),'expected_cluster_uid':'synthetic-target'}
 def run_play(self,**extra):
  p=subprocess.run(['ansible-playbook','-i',str(INV),str(PLAY),'-e',json.dumps({**self.v,**extra})],env={**os.environ,'PATH':str(self.d/'bin')+':'+os.environ['PATH'],'ANSIBLE_LOCAL_TEMP':str(self.d/'local'),'ANSIBLE_REMOTE_TEMP':str(self.d/'remote'),'ANSIBLE_NOCOLOR':'1'},capture_output=True,text=True,timeout=180)
  for marker in ['synthetic-human-private','synthetic-human-admin-session']:self.assertNotIn(marker,p.stdout+p.stderr)
  return p
 def test_browser_enforcement_is_distinct_from_enrollment_and_repeat_preserves_user(self):
  p=self.run_play();self.assertEqual(p.returncode,0,p.stdout+p.stderr)
  created=next(body for method,path,body in self.s['writes'] if method=='POST' and path.endswith('/users'))
  self.assertNotIn('email',created);self.assertNotIn('emailVerified',created);self.assertTrue(created['credentials'][0]['temporary']);self.assertEqual(created['requiredActions'],['UPDATE_PASSWORD','CONFIGURE_TOTP'])
  alias=self.v.get('human_forms_alias','perkforge-browser-password-totp-forms-v1');execs=self.s['execs'][alias];self.assertEqual([e['providerId'] for e in execs],['auth-username-password-form','auth-otp-form']);self.assertEqual([e['requirement'] for e in execs],['REQUIRED','REQUIRED'])
  self.assertEqual(self.s['realm']['unrelated'],'preserve');self.assertEqual(self.s['members'],[{'id':'admin-group','path':'/platform/admins'}]);self.assertIn('human_browser_enrollment_and_negative_login_acceptance',p.stdout);self.assertIn('pending',p.stdout)
  record=Path(self.v['human_record_file']);self.assertEqual(record.stat().st_mode&0o777,0o600)
  # Human later changes password/profile/TOTP privately; rerun must not undo it or reread the retired initial password.
  self.s['user']['requiredActions']=[];self.s['user']['totp']=True;self.s['user']['firstName']='Human';(self.d/'initial-password').unlink();before=copy.deepcopy(self.s['writes'])
  p=self.run_play();self.assertEqual(p.returncode,0,p.stdout+p.stderr);self.assertEqual(self.s['writes'],before);self.assertIn('changed=0',p.stdout);self.assertEqual(self.s['user']['requiredActions'],[]);self.assertTrue(self.s['user']['totp'])
  # A configured credential/enrollment flag must not let a conditional/disabled browser policy pass.
  execs[1]['requirement']='CONDITIONAL';p=self.run_play();self.assertNotEqual(p.returncode,0);self.assertEqual(self.s['writes'],before)
 def test_collision_or_privilege_inheritance_fails_before_policy_or_user_writes(self):
  self.s['user']={'id':'foreign','username':self.v['human_username'],'enabled':True};p=self.run_play();self.assertNotEqual(p.returncode,0);self.assertEqual(self.s['writes'],[])
  self.s['user']=None;self.s['parentRoles']={'realmMappings':[{'name':'realm-admin'}]};p=self.run_play();self.assertNotEqual(p.returncode,0);self.assertEqual(self.s['writes'],[])
  self.s['parentRoles']={};p=self.run_play(expected_cluster_uid='other');self.assertNotEqual(p.returncode,0);self.assertEqual(self.s['writes'],[])
  calls=copy.deepcopy(self.s['calls']);p=self.run_play(impact_profile='il5');self.assertNotEqual(p.returncode,0);self.assertEqual(self.s['calls'],calls)
  p=self.run_play(human_mfa_scope='UNDECIDED');self.assertNotEqual(p.returncode,0);self.assertEqual(self.s['calls'],calls)
  wrong=self.d/'wrong-ca';subprocess.run(['openssl','req','-x509','-newkey','rsa:2048','-nodes','-days','1','-subj','/CN=wrong','-keyout',str(self.d/'wrong-key'),'-out',str(wrong)],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
  p=self.run_play(human_ca_file=str(wrong));self.assertNotEqual(p.returncode,0);self.assertEqual(self.s['calls'],calls);self.assertEqual(self.s['writes'],[])
