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
   state={'calls':0,'writes':[],'enabled':False,'client':None,'policy':None,'permission':None,'bad_group':False,'bad_role':False,'bad_resource':False,'uncertain':False,'uncertain_enable':False,'uncertain_policy':False,'secret_reads':0,'token_requests':0};origin=''
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
     if not self.permitted():return
     p=urlsplit(self.path).path;q=parse_qs(urlsplit(self.path).query)
     if 'client-secret' in p:state['secret_reads']+=1;return self.reply(403,{})
     base='/auth/admin/realms/perkforge'
     if p=='/auth/admin/serverinfo':return self.reply(200,{'systemInfo':{'version':'26.8.1'}})
     if p==base:return self.reply(200,{'realm':'perkforge','adminPermissionsEnabled':state['enabled'],'adminPermissionsClient':ids['permissions'] if state['enabled'] else None})
     if p.startswith(base+'/groups/'):
      role=next(r for r,g in groups.items() if p.endswith('/'+g));return self.reply(200,{'id':groups[role],'path':'/tenants/'+('foreign' if state['bad_group'] else 'portal')+'/'+roles[role],'subGroupCount':0})
     if p==base+'/clients':
      name=q['clientId'][0]
      if name=='admin-permissions':return self.reply(200,[{'id':ids['permissions'],'clientId':name}] if state['enabled'] else [])
      if name=='realm-management':return self.reply(200,[{'id':ids['management'],'clientId':name}])
      return self.reply(200,[state['client']] if state['client'] else [])
     if p==base+'/clients/'+ids['reader']:return self.reply(200,state['client'])
     if p==base+'/clients/'+ids['reader']+'/service-account-user':return self.reply(200,{'id':ids['service'],'serviceAccountClientId':'perkforge-portal-identity-reader'})
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
     if not self.permitted():return
     body=json.loads(self.rfile.read(int(self.headers['Content-Length'])));assert self.path=='/auth/admin/realms/perkforge' and body=={'adminPermissionsEnabled':True};state['enabled']=True;state['writes'].append('enable-fgap');self.reply(503 if state['uncertain_enable'] else 204)
    def do_POST(self):
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
   state['bad_role']=True;p=run();self.assertNotEqual(p.returncode,0,p.stdout);self.assertEqual(state['writes'],['enable-fgap','disabled-client']);self.assertEqual(json.loads(receipt.read_text())['stage'],'ClientCreated');state['bad_role']=False
   p=run();self.assertEqual(p.returncode,0,p.stdout+p.stderr);self.assertEqual(json.loads(receipt.read_text())['stage'],'PendingCustody');self.assertFalse(state['client']['enabled']);before=list(state['writes']);p=run();self.assertEqual(p.returncode,0,p.stdout+p.stderr);self.assertEqual(state['writes'],before)
   state['bad_resource']=True;self.assertNotEqual(run().returncode,0);self.assertEqual(state['writes'],before);state['bad_resource']=False
   saved=receipt.read_bytes();receipt.unlink();self.assertNotEqual(run().returncode,0);self.assertEqual(state['writes'],before);receipt.write_bytes(saved);receipt.chmod(0o600)
   self.assertEqual(state['secret_reads'],0);self.assertEqual(state['token_requests'],0)
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
