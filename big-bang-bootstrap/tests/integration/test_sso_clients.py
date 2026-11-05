"""Execute shared client adapter against isolated stateful Keycloak-shaped HTTPS."""
import copy,json,os,shutil,ssl,subprocess,tempfile,threading,unittest
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit,parse_qs
ROOT=Path(__file__).resolve().parents[2];PLAY=ROOT/'configuration/authorization/sso/reconcile-client.yaml'
@unittest.skipUnless(os.environ.get('RUN_PLATFORM_SSO_TESTS'), 'enable isolated SSO job explicitly')
class Defaults(unittest.TestCase):
 def test_default_and_check_need_no_credentials(self):
  with tempfile.TemporaryDirectory() as d:
   for extra,check in (({},False),({'sso_client_run':True},True)):
    r=subprocess.run(['ansible-playbook',str(PLAY),'-e',json.dumps(extra)]+(['--check'] if check else []),env={**os.environ,'ANSIBLE_LOCAL_TEMP':d+'/local'},capture_output=True,text=True,timeout=30)
    self.assertEqual(r.returncode,0,r.stdout+r.stderr);self.assertIn('changed=0',r.stdout)
@unittest.skipUnless(os.environ.get('RUN_PLATFORM_CONFIG_TESTS') and os.environ.get('RUN_PLATFORM_SSO_TESTS') and shutil.which('ansible-playbook'),'enable isolated HTTPS fixture explicitly')
class ClientAPI(unittest.TestCase):
 def setUp(self):
  t=tempfile.TemporaryDirectory();self.addCleanup(t.cleanup);self.d=Path(t.name)
  subprocess.run(['openssl','req','-x509','-newkey','rsa:2048','-nodes','-days','1','-subj','/CN=localhost','-addext','subjectAltName=DNS:localhost','-keyout',str(self.d/'key'),'-out',str(self.d/'ca')],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
  self.s={'clients':{},'roles':{},'scopes':{},'mapped':{},'writes':[],'calls':[],'defaultGroups':[],'children':[],'parentMappings':{},'failEnable':False,'failRole':False,'foreign':{'realmMappings':[],'clientMappings':{'realm-management':{'id':'management-id','client':'realm-management','mappings':[{'id':'realm-admin','name':'realm-admin'}]}}}}
  flags={'introspection.token.claim':'true','userinfo.token.claim':'true','id.token.claim':'true','access.token.claim':'true'}
  def mapper(name,kind,config):return {'name':name,'protocol':'openid-connect','protocolMapper':kind,'config':config}
  # Independent fixture of the nonsecret actual 26.8.1 scope shapes (no real UUIDs).
  profiles=[('zoneinfo','zoneinfo','zoneinfo','String'),('nickname','nickname','nickname','String'),('profile','profile','profile','String'),('middle name','middleName','middle_name','String'),('website','website','website','String'),('username','username','preferred_username','String'),('locale','locale','locale','String'),('picture','picture','picture','String'),('updated at','updatedAt','updated_at','long'),('birthdate','birthdate','birthdate','String'),('gender','gender','gender','String'),('family name','lastName','family_name','String'),('given name','firstName','given_name','String')]
  self.s['scopeMaps']={'scope-profile':[mapper(n,'oidc-usermodel-attribute-mapper',{**flags,'user.attribute':a,'claim.name':c,'jsonType.label':t}) for n,a,c,t in profiles]+[mapper('full name','oidc-full-name-mapper',copy.deepcopy(flags))], 'scope-email':[mapper('email verified','oidc-usermodel-property-mapper',{**flags,'user.attribute':'emailVerified','claim.name':'email_verified','jsonType.label':'boolean'}),mapper('email','oidc-usermodel-attribute-mapper',{**flags,'user.attribute':'email','claim.name':'email','jsonType.label':'String'})], 'scope-basic':[mapper('auth_time','oidc-usersessionmodel-note-mapper',{**flags,'user.session.note':'AUTH_TIME','claim.name':'auth_time','jsonType.label':'long'}),mapper('sub','oidc-sub-mapper',{'introspection.token.claim':'true','access.token.claim':'true'})]}
  self.s['scopeCatalog']=[{'name':n,'id':'scope-'+n,'protocol':'openid-connect'} for n in ('profile','email','basic','roles')]
  s=self.s;api='/auth/admin/realms/perkforge'
  class H(BaseHTTPRequestHandler):
   def log_message(self,*a):pass
   def respond(self,status,value=None):
    self.send_response(status);self.send_header('Content-Type','application/json');self.end_headers()
    if value is not None:self.wfile.write(json.dumps(value).encode())
   def do_GET(self):
    path=urlsplit(self.path).path;q=parse_qs(urlsplit(self.path).query);s['calls'].append(('GET',path))
    if self.headers.get('Authorization')!='Bearer fixture-access-token':return self.respond(403,{})
    if path==api:return self.respond(200,{'realm':'perkforge','enabled':True,'attributes':{'perkforge-managed':'true','perkforge-purpose':'realm-foundation-v1'}})
    if path==api+'/group-by-path/platform/admins':return self.respond(200,{'id':'admin-id','path':'/platform/admins','attributes':{'perkforge-managed':['true'],'perkforge-foundation':['v1'],'perkforge-role':['platform-admin']}})
    if path==api+'/group-by-path/platform':return self.respond(200,{'id':'parent-id','path':'/platform','attributes':{'perkforge-managed':['true'],'perkforge-foundation':['v1']}})
    if path==api+'/groups/parent-id/role-mappings':return self.respond(200,s['parentMappings'])
    if path==api+'/default-groups':return self.respond(200,s['defaultGroups'])
    if path==api+'/groups/admin-id/children':return self.respond(200,s['children'])
    if path==api+'/client-scopes':return self.respond(200,s['scopeCatalog'])
    if path.startswith(api+'/client-scopes/'):
     sid=path.split('/client-scopes/')[1].split('/')[0];return self.respond(200,s['scopeMaps'][sid])
    if path==api+'/clients':
     # Deliberately brief lookup; canonical fields must be fetched by ID.
     return self.respond(200,[{'id':c['id'],'clientId':c['clientId']} for c in s['clients'].values() if c['clientId']==q['clientId'][0]])
    if path==api+'/groups/admin-id/role-mappings':
     value=copy.deepcopy(s['foreign'])
     for cid,roles in s['mapped'].items():
      if roles:value['clientMappings'][s['clients'][cid]['clientId']]={'id':cid,'client':s['clients'][cid]['clientId'],'mappings':roles}
     return self.respond(200,value)
    if path.startswith(api+'/roles-by-id/') and path.endswith('/composites'):return self.respond(200,[])
    if path.startswith(api+'/clients/'):
     rest=path[len(api+'/clients/'):].split('/');cid=rest[0];c=s['clients'][cid]
     if len(rest)==1:return self.respond(200,{k:v for k,v in {**c,'secret':'**********'}.items() if k not in ('defaultClientScopes','optionalClientScopes')})
     if rest[1]=='default-client-scopes':return self.respond(200,[x for x in s['scopeCatalog'] if x['name'] in c['defaultClientScopes']])
     if rest[1]=='optional-client-scopes':return self.respond(200,[])
     if rest[1]=='client-secret':return self.respond(200,{'type':'secret','value':self.server.secrets[cid]})
     if rest[1]=='protocol-mappers':return self.respond(200,[dict(m,id='mapper-'+str(i)) for i,m in enumerate(c['protocolMappers'])])
     if rest[1]=='roles':return self.respond(200,s['roles'].get(cid,[]))
     if rest[1]=='scope-mappings':
      if len(rest)==2:return self.respond(200,{'clientMappings':{c['clientId']:{'id':cid,'client':c['clientId'],'mappings':s['scopes'][cid]}}} if s['scopes'].get(cid) else {})
      return self.respond(200,s['scopes'].get(cid,[]))
    if path.startswith(api+'/groups/admin-id/role-mappings/clients/'):
     cid=path.split('/clients/')[1].split('/')[0];return self.respond(200,s['mapped'].get(cid,[]))
    return self.respond(404,{})
   def write(self,method):
    path=urlsplit(self.path).path;body=json.loads(self.rfile.read(int(self.headers.get('Content-Length',0))) or b'{}')
    if method=='POST' and path.endswith('/realms/master/protocol/openid-connect/token'):
     # Form encoding is not JSON; token handler is separate below.
     raise AssertionError('unexpected')
    if self.headers.get('Authorization')!='Bearer fixture-access-token':return self.respond(403,{})
    if path==api+'/clients':
     cid='client-'+body['clientId'];assert cid not in s['clients'];self.server.secrets[cid]=body.pop('secret');body['id']=cid;
     for m in body['protocolMappers']:
      if m['protocolMapper']=='oidc-usermodel-client-role-mapper' and m['config'].get('usermodel.clientRoleMapping.rolePrefix')=='':m['config'].pop('usermodel.clientRoleMapping.rolePrefix')
      if 'userinfo.token.claim' not in m['config'] and 'id.token.claim' in m['config']:m['config']['userinfo.token.claim']=m['config']['id.token.claim']
     body['attributes'].update({'oauth2.device.authorization.grant.enabled':'false','oidc.ciba.grant.enabled':'false'});s['clients'][cid]=body;s['scopes'][cid]=[];s['mapped'][cid]=[]
    elif path.startswith(api+'/clients/'):
     rest=path[len(api+'/clients/'):].split('/');cid=rest[0]
     if len(rest)==1:
      assert set(body)=={'clientId','enabled'}
      s['clients'][cid].update(body)
      if s['failEnable'] and body.get('enabled'):
       s['writes'].append((method,path));return self.respond(503,{})
     elif rest[1]=='roles':
      if s['failRole']:return self.respond(403,{})
      s['roles'][cid]=[{**body,'id':'role-'+cid,'clientRole':True,'containerId':cid,'attributes':{}}]
     elif rest[1]=='scope-mappings':s['scopes'][cid]=body
     else:return self.respond(404,{})
    elif path.startswith(api+'/groups/admin-id/role-mappings/clients/'):
     cid=path.split('/clients/')[1];s['mapped'][cid]=body if method=='POST' else []
    else:return self.respond(404,{})
    s['writes'].append((method,path));return self.respond(201 if path==api+'/clients' or path.endswith('/roles') else 204)
   def do_POST(self):
    if self.path=='/auth/realms/master/protocol/openid-connect/token':
     self.rfile.read(int(self.headers.get('Content-Length',0)));return self.respond(200,{'access_token':'fixture-access-token'})
    return self.write('POST')
   def do_PUT(self):return self.write('PUT')
   def do_DELETE(self):return self.write('DELETE')
  self.server=ThreadingHTTPServer(('127.0.0.1',0),H);self.server.secrets={};ctx=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER);ctx.load_cert_chain(str(self.d/'ca'),str(self.d/'key'));self.server.socket=ctx.wrap_socket(self.server.socket,server_side=True)
  threading.Thread(target=self.server.serve_forever,daemon=True).start();self.addCleanup(self.server.server_close);self.addCleanup(self.server.shutdown)
  for key,value in (('username','fixture-recovery'),('password','fixture-recovery-password'),('secret','fixture-app-client-secret')):
   p=self.d/key;p.write_text(value);p.chmod(0o600)
  self.v={'sso_client_run':True,'sso_client_stage':'headlamp','sso_client_recovery_verified':True,'sso_client_native_ready':True,'sso_client_group_id':'admin-id','sso_client_parent_id':'parent-id','sso_client_username_file':str(self.d/'username'),'sso_client_password_file':str(self.d/'password'),'sso_client_secret_file':str(self.d/'secret'),'sso_public_ca_file':str(self.d/'ca'),'sso_keycloak_origin':'https://localhost:'+str(self.server.server_port),'sso_environment':'fixture'}
 def run_play(self,op='prepare',stage='headlamp',extra=None):
  r=subprocess.run(['ansible-playbook',str(PLAY),'-e',json.dumps({**self.v,'sso_client_stage':stage,'sso_client_operation':op,'sso_client_reviewed_scope':stage+'-client-'+op+'-v1',**(extra or {})})],env={**os.environ,'ANSIBLE_LOCAL_TEMP':str(self.d/'local'),'ANSIBLE_REMOTE_TEMP':str(self.d/'remote')},capture_output=True,text=True,timeout=90)
  for secret in ('fixture-access-token','fixture-recovery-password','fixture-app-client-secret'):self.assertNotIn(secret,r.stdout+r.stderr)
  return r
 def ok(self,*a,**kw):
  r=self.run_play(*a,**kw);self.assertEqual(r.returncode,0,r.stdout+r.stderr);return r
 def test_three_clients_prepare_activate_repeat_and_independent_rollback(self):
  foreign=copy.deepcopy(self.s['foreign'])
  for stage in ('headlamp','rancher','openbao'):
   self.ok(stage=stage);self.assertFalse(self.s['clients']['client-'+('headlamp-local' if stage=='headlamp' else stage)]['enabled'])
   self.assertIn('changed=0',self.ok(stage=stage).stdout)
   self.ok('activate',stage);self.assertIn('changed=0',self.ok('activate',stage).stdout)
  before=copy.deepcopy(self.s['clients']);self.ok('rollback','rancher')
  self.assertFalse(self.s['clients']['client-rancher']['enabled']);self.assertTrue(self.s['clients']['client-headlamp-local']['enabled']);self.assertTrue(self.s['clients']['client-openbao']['enabled'])
  self.assertEqual(self.s['clients']['client-openbao'],before['client-openbao']);self.assertEqual(self.s['foreign'],foreign);self.assertIn('changed=0',self.ok('rollback','rancher').stdout)
 def test_partial_prepare_and_activation_resume_without_duplicates(self):
  self.s['failRole']=True;r=self.run_play();self.assertNotEqual(r.returncode,0);self.assertEqual(len(self.s['clients']),1)
  self.s['failRole']=False;self.ok();self.s['failEnable']=True;r=self.run_play('activate');self.assertNotEqual(r.returncode,0)
  self.s['failEnable']=False;self.ok('activate');self.assertEqual(len(self.s['clients']),1);self.assertEqual(sum(p.endswith('/clients') for _,p in self.s['writes']),1)
 def test_canonical_absent_or_empty_prefix_only_and_other_mapper_config_stays_exact(self):
  # Observed 26.8.1 response omits the empty prefix. Existing client and secret
  # must be reused, and both absent and explicit empty must repeat without writes.
  self.ok();cid='client-headlamp-local';client=self.s['clients'][cid]
  groups=next(m for m in client['protocolMappers'] if m['name']=='app-groups')
  audience=next(m for m in client['protocolMappers'] if m['name']=='app-audience')
  key='usermodel.clientRoleMapping.rolePrefix';self.assertNotIn(key,groups['config'])
  before=len(self.s['writes']);self.assertIn('changed=0',self.ok().stdout)
  groups['config'][key]='';self.assertIn('changed=0',self.ok().stdout)
  for value in ('foreign:',None):
   groups['config'][key]=value;r=self.run_play();self.assertNotEqual(r.returncode,0);self.assertEqual(len(self.s['writes']),before)
  groups['config'].pop(key)
  for config,key,value in ((groups['config'],'unexpected','true'),(groups['config'],'claim.name','foreign'),(audience['config'],'usermodel.clientRoleMapping.rolePrefix','')):
   original=copy.deepcopy(config);config[key]=value
   r=self.run_play();self.assertNotEqual(r.returncode,0);self.assertEqual(len(self.s['writes']),before)
   config.clear();config.update(original)
  self.assertEqual(len(self.s['clients']),1);self.assertEqual(self.server.secrets[cid],'fixture-app-client-secret')
 def test_parent_privilege_or_replaced_parent_refuses_before_client_creation(self):
  self.s['parentMappings']={'clientMappings':{'foreign-client':{'mappings':[{'name':'admin'}]}}}
  r=self.run_play();self.assertNotEqual(r.returncode,0);self.assertEqual(self.s['writes'],[])
  self.s['parentMappings']={}
  r=self.run_play(extra={'sso_client_parent_id':'wrong-parent'});self.assertNotEqual(r.returncode,0);self.assertEqual(self.s['writes'],[])
 def test_shared_scope_group_leak_and_missing_basic_refuse_before_client_creation(self):
  initial=copy.deepcopy(self.s['scopeMaps']);self.s['scopeMaps']['scope-profile'].append({'name':'foreign-groups','protocol':'openid-connect','protocolMapper':'oidc-group-membership-mapper','config':{'claim.name':'groups','full.path':'true'}})
  r=self.run_play();self.assertNotEqual(r.returncode,0);self.assertEqual(self.s['writes'],[])
  self.s['scopeMaps']=initial;catalog=self.s['scopeCatalog'];self.s['scopeCatalog']=[x for x in catalog if x['name']!='basic']
  r=self.run_play();self.assertNotEqual(r.returncode,0);self.assertEqual(self.s['writes'],[])
 def test_unowned_client_extra_roles_wrong_secret_and_readiness_refuse(self):
  self.ok();cid='client-headlamp-local';before=len(self.s['writes'])
  self.s['clients'][cid]['attributes']['perkforge-purpose']='foreign';r=self.run_play('activate');self.assertNotEqual(r.returncode,0);self.assertEqual(len(self.s['writes']),before)
  self.s['clients'][cid]['attributes']['perkforge-purpose']='coordinated-sso-v1';r=self.run_play('activate',extra={'sso_client_native_ready':False});self.assertNotEqual(r.returncode,0)
  (self.d/'secret').write_text('wrong-private-fixture-key');r=self.run_play('activate');self.assertNotEqual(r.returncode,0);self.assertEqual(len(self.s['writes']),before)
  (self.d/'secret').write_text('fixture-app-client-secret');self.s['roles'][cid].append({'name':'foreign'});r=self.run_play('activate');self.assertNotEqual(r.returncode,0);self.assertEqual(len(self.s['writes']),before)
if __name__=='__main__':unittest.main()
