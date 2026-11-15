"""Default-off setup against a pinned-shape synthetic TLS API, never real permissions."""
import copy,json,os,ssl,subprocess,tempfile,threading,unittest
from pathlib import Path
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from urllib.parse import urlsplit,parse_qs
ROOT=Path(__file__).resolve().parents[2];SETUP=ROOT/'configuration/packages/gitlab/enrollment/setup'
class ReaderSetup(unittest.TestCase):
 def test_disabled_setup_idempotency_partial_and_foreign_denials(self):
  with tempfile.TemporaryDirectory(prefix='kc-reader-setup-') as directory:
   root=Path(directory);subprocess.run(['openssl','req','-x509','-newkey','rsa:2048','-nodes','-days','1','-subj','/CN=localhost','-addext','subjectAltName=DNS:localhost','-keyout',str(root/'key'),'-out',str(root/'ca')],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL);(root/'ca').chmod(0o644)
   ids={k:f'00000000-0000-4000-8000-{i:012d}' for i,k in enumerate(['permissions','reader','service','management','policy','permission'],10)};roles={'tenant-admin':'admins','tenant-developer':'developers','tenant-viewer':'viewers'};groups={r:f'11111111-1111-4111-8111-{i:012d}' for i,r in enumerate(roles,1)}
   state={'permissions_rep':None,'custody_mode':False,'record':None,'fail_mode':'','reader_ttl':300,'calls':0,'writes':[],'enabled':False,'client':None,'policy':None,'permission':None,'bad_group':False,'bad_role':False,'bad_resource':False,'uncertain':False,'uncertain_enable':False,'uncertain_policy':False,'secret_reads':0,'token_requests':0};origin='';foreign='99999999-9999-4999-8999-999999999999'
   class H(BaseHTTPRequestHandler):
    def log_message(self,*a):pass
    def reply(self,code,value=None,location=None):
     self.send_response(code);self.send_header('Content-Type','application/json')
     if location:self.send_header('Location',location)
     self.end_headers()
     if value is not None:self.wfile.write(json.dumps(value).encode())
    def permitted(self):
     state['calls']+=1
     if self.headers.get('Authorization')!='Bearer OFFLINE-OPERATOR':self.reply(403,{});return False
     return True
    def do_GET(self):
     if self.path.startswith('/v1/'):
      assert self.headers.get('X-Vault-Token')=='OFFLINE-BAO'
      if self.path=='/v1/auth/token/lookup-self':return self.reply(200,{'data':{'policies':['root'] if state['fail_mode']=='root' else ['tenant-identity-bootstrap-keycloak-v1'],'identity_policies':[],'renewable':False,'ttl':1800}})
      if '/sys/policies/' in self.path:return self.reply(200,{'data':{'policy':(SETUP/'keycloak-custody-policy.hcl').read_text()}})
      if '/metadata/' in self.path:return self.reply(404) if state['record'] is None else self.reply(200,{'data':{}})
      return self.reply(200,{'data':{'metadata':{'version':1},'data':state['record']}})
     if self.headers.get('Authorization')=='Bearer OFFLINE-READER':
      if self.path.endswith('/'+foreign):return self.reply(200,{'id':foreign}) if state['fail_mode']=='foreign' else self.reply(403,{})
      if '/members?' in self.path:return self.reply(200,[])
      return self.reply(200,{'id':self.path.rsplit('/',1)[-1]})
     if not self.permitted():return
     p=urlsplit(self.path).path;q=parse_qs(urlsplit(self.path).query)
     if 'client-secret' in p:state['secret_reads']+=1;return self.reply(200,{'type':'secret','value':'OFFLINE-CLIENT-SECRET'}) if state['custody_mode'] else self.reply(403,{})
     base='/auth/admin/realms/perkforge'
     if p=='/auth/admin/serverinfo':return self.reply(200,{'systemInfo':{'version':'26.8.1'}})
     if p==base:return self.reply(200,{'realm':'perkforge','adminPermissionsEnabled':state['enabled'],'adminPermissionsClient':(state['permissions_rep'] if state['permissions_rep'] is not None else {'id':ids['permissions'],'clientId':'admin-permissions'}) if state['enabled'] else None})
     if p==base+'/groups/'+foreign:return self.reply(200,{'id':foreign})
     if p.startswith(base+'/groups/'):
      role=next(r for r,g in groups.items() if p.endswith('/'+g));return self.reply(200,{'id':groups[role],'path':'/tenants/'+('foreign' if state['bad_group'] else 'portal')+'/'+roles[role],'subGroupCount':0})
     if p==base+'/clients':
      name=q['clientId'][0]
      if name=='admin-permissions':return self.reply(200,[{'id':ids['permissions'],'clientId':name}] if state['enabled'] else [])
      if name=='realm-management':return self.reply(200,[{'id':ids['management'],'clientId':name}])
      return self.reply(200,[state['client']] if state['client'] else [])
     if p==base+'/clients/'+ids['reader']:return self.reply(200,state['client'])
     if p==base+'/clients/'+ids['reader']+'/service-account-user':return self.reply(200,{'id':ids['service'],'username':'service-account-perkforge-portal-identity-reader'})
     if p==base+'/users/'+ids['service']+'/groups':return self.reply(200,[])
     if p==base+'/users/'+ids['service']+'/role-mappings/clients/'+ids['management']+'/composite':return self.reply(200,[{'name':'view-users'}] if state['bad_role'] else [])
     authz=base+'/clients/'+ids['permissions']+'/authz/resource-server'
     if p in (authz+'/policy/search',authz+'/permission/scope/search'):
      key='policy' if p.endswith('/policy/search') else 'permission';value=state[key];return self.reply(200,value) if value else self.reply(204)
     if p==authz+'/policy/'+ids['policy']:return self.reply(200,state['policy'])
     if p==authz+'/policy/'+ids['permission']:return self.reply(200,state['permission'])
     if p==authz+'/policy/'+ids['permission']+'/resources':return self.reply(200,[{'_id':'authz-'+str(i),'name':('Groups' if state['bad_resource'] and i==0 else g)} for i,g in enumerate(groups.values())])
     if p==authz+'/policy/'+ids['permission']+'/scopes':return self.reply(200,[{'id':'scope-'+n,'name':n} for n in ['view','view-members']])
     if p==authz+'/policy/'+ids['permission']+'/associatedPolicies':return self.reply(200,[{k:state['policy'][k] for k in ['id','name','type']}])
     return self.reply(404,{})
    def do_PUT(self):
     if self.headers.get('Authorization')=='Bearer OFFLINE-READER':
      body=json.loads(self.rfile.read(int(self.headers['Content-Length'])));assert body=={};return self.reply(400 if state['fail_mode']=='manage' else 403,{})
     if state['custody_mode'] and self.path.endswith('/clients/'+ids['reader']):
      assert self.headers.get('Authorization')=='Bearer OFFLINE-OPERATOR'
      body=json.loads(self.rfile.read(int(self.headers['Content-Length'])));assert set(body)=={'enabled'}
      if body['enabled'] is False and state['fail_mode']=='disable':return self.reply(503,{})
      state['client']['enabled']=body['enabled'];return self.reply(204)
     if not self.permitted():return
     body=json.loads(self.rfile.read(int(self.headers['Content-Length'])));assert self.path=='/auth/admin/realms/perkforge' and body=={'adminPermissionsEnabled':True};state['enabled']=True;state['writes'].append('enable-fgap');self.reply(503 if state['uncertain_enable'] else 204)
    def do_POST(self):
     if self.path.startswith('/v1/'):
      assert self.headers.get('X-Vault-Token')=='OFFLINE-BAO'
      body=json.loads(self.rfile.read(int(self.headers['Content-Length'])));assert body['options']=={'cas':0}
      if state['record'] is not None:return self.reply(400,{})
      state['record']=body['data'];return self.reply(503,{}) if state['fail_mode']=='cas' else self.reply(200,{'data':{'version':1}})
     if state['custody_mode'] and self.path.endswith('/token'):
      body=parse_qs(self.rfile.read(int(self.headers['Content-Length'])).decode());assert body['client_secret']==['OFFLINE-CLIENT-SECRET']
      return self.reply(200,{'token_type':'Bearer','access_token':'OFFLINE-READER','expires_in':state['reader_ttl']})
     if not self.permitted():return
     if self.path.endswith('/token'):state['token_requests']+=1;return self.reply(403,{})
     body=json.loads(self.rfile.read(int(self.headers['Content-Length'])));base='/auth/admin/realms/perkforge'
     if self.path==base+'/clients':
      assert body['enabled'] is False and body['serviceAccountsEnabled'] is True and all(body[k] is False for k in ['publicClient','standardFlowEnabled','directAccessGrantsEnabled','implicitFlowEnabled','fullScopeAllowed']);state['client']={**body,'id':ids['reader']};state['writes'].append('disabled-client');return self.reply(503 if state['uncertain'] else 201,location=origin+base+'/clients/'+ids['reader'])
     authz=base+'/clients/'+ids['permissions']+'/authz/resource-server'
     if self.path==authz+'/policy/user':
      assert body=={'name':'perkforge-portal-reader-actor','type':'user','logic':'POSITIVE','users':[ids['service']]};state['policy']={'id':ids['policy'],'name':body['name'],'type':'user','logic':'POSITIVE','config':{'users':json.dumps(body['users'])}};state['writes'].append('policy');return self.reply(503 if state['uncertain_policy'] else 201,{'id':ids['policy']})
     if self.path==authz+'/permission/scope':
      assert body['resourceType']=='Groups' and set(body['resources'])==set(groups.values()) and body['scopes']==['view','view-members'] and body['policies']==['perkforge-portal-reader-actor'] and body['decisionStrategy']=='UNANIMOUS';state['permission']={'id':ids['permission'],'name':body['name'],'type':'scope','logic':'POSITIVE','decisionStrategy':'UNANIMOUS','config':{'defaultResourceType':'Groups'}};state['writes'].append('permission');return self.reply(201,{'id':ids['permission']})
     self.reply(404,{})
   server=ThreadingHTTPServer(('127.0.0.1',0),H);tls=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER);tls.load_cert_chain(root/'ca',root/'key');server.socket=tls.wrap_socket(server.socket,server_side=True);threading.Thread(target=server.serve_forever,daemon=True).start();self.addCleanup(server.server_close);self.addCleanup(server.shutdown);origin='https://localhost:'+str(server.server_port)
   token=root/'operator';token.write_text('OFFLINE-OPERATOR');token.chmod(0o600);receipt=root/'reader.json';inputs=root/'inputs.json';base={'kc_reader_run':True,'kc_reader_scope':'canonical-group-reader-setup-v1','kc_reader_context':'portal','kc_reader_source_revision':'a'*40,'kc_reader_origin':origin+'/auth','kc_reader_realm':'perkforge','kc_reader_group_ids':groups,'kc_reader_allow_enable_permissions':True,'kc_reader_ca_file':str(root/'ca')}
   def run(mode='--apply',changes=None,check=False):
    inputs.write_text(json.dumps({**base,**(changes or {})}));inputs.chmod(0o600);command=['bash',str(SETUP/'run-kc-reader.sh'),mode,str(token),str(receipt),str(inputs)]
    if check:command=['ansible-playbook','-i','localhost,',str(SETUP/'keycloak-reader.yaml'),'--check','-e','@'+str(inputs)]
    p=subprocess.run(command,capture_output=True,text=True,timeout=90,env={**os.environ,'ANSIBLE_LOCAL_TEMP':str(root/'local'),'ANSIBLE_REMOTE_TEMP':str(root/'remote')});self.assertNotIn('OFFLINE-OPERATOR',p.stdout+p.stderr);return p
   self.assertEqual(run(mode='--validate').returncode,0);self.assertEqual(run(check=True).returncode,0);self.assertEqual(run(mode='noop').returncode,0);self.assertEqual(state['calls'],0);self.assertFalse(receipt.exists())
   for changes in ({'unexpected':'override'},{'kc_reader_context':'{{lookup("pipe","false")}}'},{'kc_reader_group_ids':{}},{'kc_reader_run':False}):self.assertNotEqual(run(changes=changes).returncode,0)
   self.assertEqual(state['calls'],0)
   self.assertNotEqual(run(changes={'kc_reader_allow_enable_permissions':False}).returncode,0);self.assertEqual(state['writes'],[])
   state['bad_group']=True;self.assertNotEqual(run().returncode,0);self.assertEqual(state['writes'],[]);state['bad_group']=False
   for wrong in ('legacy-string',{'id':ids['reader'],'clientId':'admin-permissions'},{'id':ids['permissions'],'clientId':'foreign'}):
    state['permissions_rep']=wrong;self.assertNotEqual(run().returncode,0);self.assertEqual(state['writes'],['enable-fgap']);self.assertEqual(json.loads(receipt.read_text())['stage'],'PermissionsEnablePending')
   state['permissions_rep']=None
   state['bad_role']=True;p=run();self.assertNotEqual(p.returncode,0,p.stdout);self.assertEqual(state['writes'],['enable-fgap','disabled-client']);self.assertEqual(json.loads(receipt.read_text())['stage'],'ClientCreated');state['bad_role']=False
   p=run();self.assertEqual(p.returncode,0,p.stdout+p.stderr);self.assertEqual(json.loads(receipt.read_text())['stage'],'PendingCustody');self.assertFalse(state['client']['enabled']);before=list(state['writes']);p=run();self.assertEqual(p.returncode,0,p.stdout+p.stderr);self.assertEqual(state['writes'],before)
   state['bad_resource']=True;self.assertNotEqual(run().returncode,0);self.assertEqual(state['writes'],before);state['bad_resource']=False
   saved=receipt.read_bytes();receipt.unlink();self.assertNotEqual(run().returncode,0);self.assertEqual(state['writes'],before);receipt.write_bytes(saved);receipt.chmod(0o600)
   self.assertEqual(state['secret_reads'],0);self.assertEqual(state['token_requests'],0)
   # Actual Ansible activation against the same synthetic native shape.
   state['custody_mode']=True;bao=root/'bao';bao.write_text('OFFLINE-BAO');bao.chmod(0o600)
   activation=root/'activation.json';attempt=root/'attempt.json'
   inputs.write_text(json.dumps({**base,'kc_reader_allow_enable_permissions':False}));inputs.chmod(0o600)
   activation.write_text(json.dumps({'run':True,'scope':'keycloak-reader-custody-v1','setup_id':'b'*64,'bao_origin':origin,'ca_file':str(root/'ca'),'reader_inputs':str(inputs),'foreign_group_id':foreign}));activation.chmod(0o600)
   def activate(mode='apply'):
    p=subprocess.run(['python3',str(SETUP/'activate-keycloak.py'),mode,str(token),str(bao),str(receipt),str(attempt),str(activation)],capture_output=True,text=True,timeout=180,env={**os.environ,'ANSIBLE_LOCAL_TEMP':str(root/'local'),'ANSIBLE_REMOTE_TEMP':str(root/'remote')})
    for secret in ('OFFLINE-OPERATOR','OFFLINE-BAO','OFFLINE-CLIENT-SECRET','OFFLINE-READER'):self.assertNotIn(secret,p.stdout+p.stderr)
    return p
   self.assertEqual(activate('validate').returncode,0);self.assertFalse(attempt.exists());self.assertIsNone(state['record'])
   state['fail_mode']='root';self.assertNotEqual(activate().returncode,0);self.assertFalse(attempt.exists());self.assertIsNone(state['record']);self.assertFalse(state['client']['enabled'])
   state['fail_mode']=''
   for failure,ttl in [('',300),('cas',300),('foreign',300),('manage',300),('',301),('disable',301)]:
    state.update(fail_mode=failure,reader_ttl=ttl,record=None);state['client']['enabled']=False
    if attempt.exists():attempt.unlink()
    p=activate();r=json.loads(attempt.read_text())
    if not failure and ttl==300:
     self.assertEqual(p.returncode,0,p.stdout+p.stderr);self.assertEqual(r['stage'],'ReaderAccessVerified');self.assertTrue(state['client']['enabled'])
    else:
     self.assertNotEqual(p.returncode,0);self.assertEqual(r['stage'],'ManualRecovery')
     if failure=='disable':self.assertEqual(r['disable_result'],'unverified')
     else:self.assertFalse(state['client']['enabled'])
    self.assertIsNotNone(state['record'])
    self.assertNotEqual(activate().returncode,0) # never silent repeat/secret rotation
   state.update(custody_mode=False,record=None,fail_mode='');state['client']['enabled']=False
   # A successful native create whose response is lost is not adopted on retry.
   receipt.unlink();state.update(enabled=False,client=None,policy=None,permission=None,uncertain=True,writes=[]);self.assertNotEqual(run().returncode,0);before=list(state['writes']);self.assertNotEqual(run().returncode,0);self.assertEqual(state['writes'],before)

   # Enablement loss is retained as requested/observed state, never rolled back.
   receipt.unlink();state.update(enabled=False,client=None,policy=None,permission=None,uncertain=False,uncertain_enable=True,writes=[]);self.assertNotEqual(run().returncode,0);r=json.loads(receipt.read_text());self.assertEqual(r['stage'],'PermissionsEnablePending');self.assertTrue(r['permissions_enable_requested']);self.assertFalse(r['permissions_observed_enabled']);self.assertTrue(state['enabled'])
   state['uncertain_enable']=False;p=run();self.assertEqual(p.returncode,0,p.stdout+p.stderr);self.assertEqual(state['writes'].count('enable-fgap'),1);self.assertTrue(json.loads(receipt.read_text())['permissions_observed_enabled'])
   # Foreign policy is never adopted after an uncertain creation response.
   receipt.unlink();state.update(enabled=False,client=None,policy=None,permission=None,uncertain_policy=True,writes=[]);self.assertNotEqual(run().returncode,0);before=list(state['writes']);self.assertEqual(json.loads(receipt.read_text())['stage'],'ClientCreated');self.assertNotEqual(run().returncode,0);self.assertEqual(state['writes'],before);self.assertTrue(state['enabled']);self.assertFalse(state['client']['enabled'])

 def test_reopened_descriptor_replacement_is_refused(self):
  import importlib.util
  from unittest.mock import patch
  spec=importlib.util.spec_from_file_location('kc_setup_validator',SETUP/'validate-kc-reader.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
  with tempfile.TemporaryDirectory(prefix='kc-setup-fd-') as directory:
   a=Path(directory)/'input.json';b=Path(directory)/'replacement.json'
   for p in (a,b):p.write_text('{}');p.chmod(0o600)
   self.assertEqual(module.read(str(a)),{})
   original=os.open;calls=0
   def replacement(path,flags,*args,**kwargs):
    nonlocal calls
    calls+=1
    return original(str(b) if calls==2 else path,flags,*args,**kwargs)
   with patch.object(module.os,'open',side_effect=replacement):
    with self.assertRaises(ValueError):module.read(str(a))
