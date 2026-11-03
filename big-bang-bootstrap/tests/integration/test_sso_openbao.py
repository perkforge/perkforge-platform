"""Actual Ansible against isolated stateful HTTPS. No live identity acceptance."""
import copy
import json
import os
from pathlib import Path
import shutil
import ssl
import subprocess
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit

ROOT=Path(__file__).resolve().parents[2]
PLAY=ROOT/'configuration/authorization/sso/reconcile-openbao.yaml'

@unittest.skipUnless(os.environ.get('RUN_PLATFORM_SSO_TESTS'), 'enable isolated SSO job explicitly')
class Defaults(unittest.TestCase):
 def test_default_and_check_do_not_read_credentials(self):
  with tempfile.TemporaryDirectory() as d:
   for extra,check in (({},False),({'sso_openbao_run':True},True),({'sso_openbao_run':True,'sso_openbao_operation':'prepare-data'},True)):
    r=subprocess.run(['ansible-playbook',str(PLAY),'-e',json.dumps(extra)]+(['--check'] if check else []),env={**os.environ,'ANSIBLE_LOCAL_TEMP':d+'/local'},capture_output=True,text=True,timeout=30)
    self.assertEqual(r.returncode,0,r.stdout+r.stderr);self.assertIn('changed=0',r.stdout)

@unittest.skipUnless(os.environ.get('RUN_PLATFORM_CONFIG_TESTS') and os.environ.get('RUN_PLATFORM_SSO_TESTS') and shutil.which('ansible-playbook'),'enable isolated HTTPS fixture explicitly')
class OpenBaoAPI(unittest.TestCase):
 def setUp(self):
  t=tempfile.TemporaryDirectory();self.addCleanup(t.cleanup);self.d=Path(t.name)
  subprocess.run(['openssl','req','-x509','-newkey','rsa:2048','-nodes','-days','1','-subj','/CN=localhost','-addext','subjectAltName=DNS:localhost','-keyout',str(self.d/'key'),'-out',str(self.d/'ca')],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
  self.s={'mount':True,'mountDescription':'','mountConfig':{'default_lease_ttl':900,'max_lease_ttl':3600},'foreignRoles':[],'dataMounts':{'platform/':{'type':'kv','options':{'version':'2'}},'tenants/':{'type':'kv','options':{'version':'2'}}},'config':None,'policy':None,'role':None,'writes':[],'calls':[],'aliases':{},'entities':{},'groupAliases':{},'denyRole':False,'denyToken':False,'cluster':'fixture-cluster','foreign':{'policy':'unchanged','kubernetesAuth':'unchanged','recovery':'unchanged'}}
  state=self.s
  class Handler(BaseHTTPRequestHandler):
   def log_message(self,*a):pass
   def respond(self,status,data=None):
    self.send_response(status);self.send_header('Content-Type','application/json');self.end_headers()
    if data is not None:self.wfile.write(json.dumps(data).encode())
   def authorized(self):return self.headers.get('X-Vault-Token')=='fixture-operator-token' and not state['denyToken']
   def do_GET(self):
    p=urlsplit(self.path).path;state['calls'].append(('GET',p))
    if p=='/v1/sys/health':return self.respond(200,{'cluster_id':state['cluster'],'initialized':True,'sealed':False,'standby':False,'version':'2.7.2'})
    if not self.authorized():return self.respond(403,{'errors':['permission denied']})
    if p=='/v1/sys/mounts':return self.respond(200,{'data':state['dataMounts']})
    if p=='/v1/sys/auth':return self.respond(200,{'data':{**({'oidc/':{'type':'oidc','accessor':'fixture-accessor','description':state['mountDescription'],'config':state['mountConfig']}} if state['mount'] else {}),'kubernetes/':{'type':'kubernetes','accessor':'machine-unchanged'}}})
    if p=='/v1/auth/oidc/role':
     names=state['foreignRoles']+(['perkforge-sso-v1-platform-admin'] if state['role'] is not None else [])
     return self.respond(200,{'data':{'keys':names}}) if names else self.respond(404,{'errors':[]})
    for kind,key in (('entity-alias','aliases'),('group-alias','groupAliases')):
     base='/v1/identity/'+kind+'/id'
     if p==base:return self.respond(200,{'data':{'keys':list(state[key])}}) if state[key] else self.respond(404,{'errors':[]})
     if p.startswith(base+'/'):return self.respond(200,{'data':state[key][p.rsplit('/',1)[1]]})
    if p.startswith('/v1/identity/entity/id/'):return self.respond(200,{'data':state['entities'][p.rsplit('/',1)[1]]})
    for path,key in (('/v1/auth/oidc/config','config'),('/v1/sys/policies/acl/perkforge-sso-v1-platform-admin','policy'),('/v1/auth/oidc/role/perkforge-sso-v1-platform-admin','role')):
     if p==path:return self.respond(200,{'data':state[key]}) if state[key] is not None else self.respond(404,{'errors':[]})
    return self.respond(404,{'errors':['unexpected fixture path']})
   def write(self,method):
    p=urlsplit(self.path).path
    if not self.authorized():return self.respond(403,{'errors':['permission denied']})
    body=json.loads(self.rfile.read(int(self.headers.get('Content-Length',0))) or b'{}')
    if p in ['/v1/sys/mounts/platform','/v1/sys/mounts/tenants']:
     name=p.rsplit('/',1)[-1]+'/'
     assert method=='POST' and name not in state['dataMounts'] and body=={'type':'kv','description':'PerkForge coordinated-sso-v1 data mount','options':{'version':'2'}}
     if state.get('denyTenantMount') and name=='tenants/':return self.respond(403,{'errors':['fixture interruption']})
     state['dataMounts'][name]=body;state['writes'].append((method,p));return self.respond(204)
    if p=='/v1/sys/auth/oidc':
     assert not state['mount'] and method=='POST' and body['type']=='oidc'
     state['mount']=True;state['mountDescription']=body['description'];state['mountConfig']=body['config'];state['writes'].append((method,p));return self.respond(204)
    mapping={'/v1/auth/oidc/config':'config','/v1/sys/policies/acl/perkforge-sso-v1-platform-admin':'policy','/v1/auth/oidc/role/perkforge-sso-v1-platform-admin':'role'}
    if p not in mapping:return self.respond(400,{'errors':['unexpected fixture write']})
    key=mapping[p]
    if key=='role' and state['denyRole']:return self.respond(403,{'errors':['fixture interruption']})
    state['writes'].append((method,p))
    if method=='DELETE':state[key]=None
    elif key=='config':
     self.server.secret=body.pop('oidc_client_secret');state[key]={**body,'jwks_url':'','bound_issuer':'','jwt_supported_algs':[],'provider_config':{}}
    else:state[key]=body
    return self.respond(204)
   def do_POST(self):return self.write('POST')
   def do_PUT(self):return self.write('PUT')
   def do_DELETE(self):return self.write('DELETE')
  self.server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
  ctx=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER);ctx.load_cert_chain(str(self.d/'ca'),str(self.d/'key'));self.server.socket=ctx.wrap_socket(self.server.socket,server_side=True)
  thread=threading.Thread(target=self.server.serve_forever,daemon=True);thread.start();self.addCleanup(self.server.server_close);self.addCleanup(self.server.shutdown)
  for name,value in (('token','fixture-operator-token'),('secret','fixture-confidential-client-secret')):
   p=self.d/name;p.write_text(value);p.chmod(0o600)
  self.v={'sso_openbao_run':True,'sso_openbao_operation':'apply','sso_openbao_reviewed_scope':'openbao-sso-v1','sso_openbao_recovery_verified':True,'sso_openbao_cluster_id':'fixture-cluster','sso_openbao_accessor':'fixture-accessor','sso_openbao_token_file':str(self.d/'token'),'sso_openbao_client_secret_file':str(self.d/'secret'),'sso_public_ca_file':str(self.d/'ca'),'sso_keycloak_origin':'https://identity.fixture.test','sso_apps':{'openbao':{'origin':'https://localhost:'+str(self.server.server_port),'client_id':'openbao','apply':False}}}
 def run_play(self,extra=None):
  r=subprocess.run(['ansible-playbook',str(PLAY),'-e',json.dumps({**self.v,**(extra or {})})],env={**os.environ,'ANSIBLE_LOCAL_TEMP':str(self.d/'local'),'ANSIBLE_REMOTE_TEMP':str(self.d/'remote')},capture_output=True,text=True,timeout=90)
  self.assertNotIn('fixture-operator-token',r.stdout+r.stderr);self.assertNotIn('fixture-confidential-client-secret',r.stdout+r.stderr)
  return r
 def test_prepare_data_creates_only_missing_owned_engines_and_repeats(self):
  self.s['dataMounts']={'unrelated/':{'type':'transit','options':{}}};self.s['mount']=False;(self.d/'secret').unlink()
  extra={'sso_openbao_operation':'prepare-data','sso_openbao_reviewed_scope':'openbao-data-v1','sso_openbao_accessor':'UNCONFIGURED'}
  r=self.run_play(extra);self.assertEqual(r.returncode,0,r.stdout+r.stderr)
  self.assertEqual(self.s['writes'],[('POST','/v1/sys/mounts/platform'),('POST','/v1/sys/mounts/tenants')])
  self.assertEqual(self.s['dataMounts']['unrelated/'],{'type':'transit','options':{}})
  self.assertFalse(self.s['mount']);self.assertIsNone(self.s['role']);self.assertIsNone(self.s['policy']);self.assertIsNone(self.s['config'])
  r=self.run_play(extra);self.assertEqual(r.returncode,0,r.stdout+r.stderr);self.assertIn('changed=0',r.stdout);self.assertEqual(len(self.s['writes']),2)
 def test_prepare_data_refuses_foreign_mount_or_wrong_scope_before_writes(self):
  extra={'sso_openbao_operation':'prepare-data','sso_openbao_reviewed_scope':'openbao-data-v1'}
  for existing in [{'platform/':{'type':'kv','options':{'version':'2'},'description':'foreign'}},{'tenants/':{'type':'transit','options':{}}}]:
   self.s['dataMounts']=existing;r=self.run_play(extra);self.assertNotEqual(r.returncode,0);self.assertEqual(self.s['writes'],[])
  self.s['dataMounts']={};r=self.run_play({**extra,'sso_openbao_reviewed_scope':'openbao-sso-v1'});self.assertNotEqual(r.returncode,0);self.assertEqual(self.s['writes'],[])
 def test_prepare_data_partial_create_resumes_without_replacing_first_engine(self):
  self.s['dataMounts']={};self.s['denyTenantMount']=True
  extra={'sso_openbao_operation':'prepare-data','sso_openbao_reviewed_scope':'openbao-data-v1'}
  r=self.run_play(extra);self.assertNotEqual(r.returncode,0);first=copy.deepcopy(self.s['dataMounts']['platform/']);self.assertEqual(len(self.s['writes']),1)
  self.s['denyTenantMount']=False;r=self.run_play(extra);self.assertEqual(r.returncode,0,r.stdout+r.stderr)
  self.assertEqual(self.s['dataMounts']['platform/'],first);self.assertEqual(len(self.s['writes']),2)

 def test_prepare_missing_mount_is_independent_idempotent_and_preserves_machine_auth(self):
  self.s['mount']=False;foreign=copy.deepcopy(self.s['foreign'])
  extra={'sso_openbao_operation':'prepare','sso_openbao_reviewed_scope':'openbao-sso-prepare-v1','sso_openbao_accessor':'UNCONFIGURED'}
  r=self.run_play(extra);self.assertEqual(r.returncode,0,r.stdout+r.stderr);self.assertEqual(len(self.s['writes']),1);self.assertIsNone(self.s['config']);self.assertIsNone(self.s['role']);self.assertEqual(self.s['foreign'],foreign)
  r=self.run_play(extra);self.assertEqual(r.returncode,0,r.stdout+r.stderr);self.assertIn('changed=0',r.stdout);self.assertEqual(len(self.s['writes']),1)
 def test_missing_or_wrong_data_engine_refuses_policy_activation(self):
  for data in ({},{'platform/':{'type':'transit','options':{}},'tenants/':{'type':'kv','options':{'version':'2'}}}):
   self.s['dataMounts']=data
   r=self.run_play();self.assertNotEqual(r.returncode,0);self.assertEqual(self.s['writes'],[])
 def test_legacy_login_roles_and_ambiguous_mount_preparation_refuse(self):
  self.s['foreignRoles']=['legacy-wide-platform-role']
  r=self.run_play();self.assertNotEqual(r.returncode,0);self.assertEqual(self.s['writes'],[])
  self.s['foreignRoles']=[]
  r=self.run_play({'sso_openbao_operation':'prepare','sso_openbao_reviewed_scope':'openbao-sso-prepare-v1'});self.assertNotEqual(r.returncode,0);self.assertEqual(self.s['writes'],[])
 def test_apply_repeat_inspect_rollback_preserve_other_state(self):
  foreign=copy.deepcopy(self.s['foreign'])
  r=self.run_play();self.assertEqual(r.returncode,0,r.stdout+r.stderr);self.assertEqual(len(self.s['writes']),3)
  self.assertNotIn('groups_claim',self.s['role']);self.assertEqual(self.s['role']['bound_claims'],{'groups':['/platform/admins']})
  self.assertEqual(self.s['role']['token_policies'],['perkforge-sso-v1-platform-admin']);self.assertTrue(self.s['role']['token_no_default_policy'])
  self.assertNotIn('tenants/data',self.s['policy']['policy'])
  for op in ('apply','inspect'):
   r=self.run_play({'sso_openbao_operation':op});self.assertEqual(r.returncode,0,r.stdout+r.stderr);self.assertIn('changed=0',r.stdout);self.assertEqual(len(self.s['writes']),3)
  r=self.run_play({'sso_openbao_operation':'rollback'});self.assertEqual(r.returncode,0,r.stdout+r.stderr)
  self.assertIsNone(self.s['role']);self.assertIsNone(self.s['policy']);self.assertIsNotNone(self.s['config']);self.assertEqual(foreign,self.s['foreign'])
  r=self.run_play({'sso_openbao_operation':'rollback'});self.assertEqual(r.returncode,0,r.stdout+r.stderr);self.assertIn('changed=0',r.stdout)
 def test_interruption_resumes_without_credential_rotation(self):
  self.s['denyRole']=True;r=self.run_play();self.assertNotEqual(r.returncode,0);self.assertEqual(len(self.s['writes']),2)
  self.s['denyRole']=False;r=self.run_play();self.assertEqual(r.returncode,0,r.stdout+r.stderr);self.assertEqual(len(self.s['writes']),3)
  self.assertEqual(sum(p.endswith('/config') for _,p in self.s['writes']),1)
 def test_wrong_target_authority_and_inherited_policy_refuse_before_writes(self):
  for extra in ({'sso_openbao_cluster_id':'wrong'},{'sso_openbao_accessor':'wrong'},{'sso_openbao_reviewed_scope':'wrong'}):
   r=self.run_play(extra);self.assertNotEqual(r.returncode,0);self.assertEqual(self.s['writes'],[])
  self.s['aliases']={'alias-id':{'mount_accessor':'fixture-accessor','canonical_id':'entity-id'}}
  self.s['entities']={'entity-id':{'policies':['broad-tenant-policy'],'group_ids':[]}}
  r=self.run_play();self.assertNotEqual(r.returncode,0);self.assertEqual(self.s['writes'],[])
  self.s['entities']['entity-id']={'policies':[],'group_ids':[],'inherited_group_ids':['foreign-policy-group']}
  r=self.run_play();self.assertNotEqual(r.returncode,0);self.assertEqual(self.s['writes'],[])
  self.s['aliases']={};self.s['groupAliases']={'group-id':{'mount_accessor':'fixture-accessor'}}
  r=self.run_play();self.assertNotEqual(r.returncode,0);self.assertEqual(self.s['writes'],[])
 def test_foreign_role_or_policy_refuses_adoption(self):
  self.s['policy']={'policy':'path "tenants/data/*" {capabilities=["read"]}'}
  r=self.run_play();self.assertNotEqual(r.returncode,0);self.assertEqual(self.s['writes'],[])
  self.s['policy']=None;self.s['role']={'token_policies':['root']}
  r=self.run_play();self.assertNotEqual(r.returncode,0);self.assertEqual(self.s['writes'],[])

if __name__=='__main__':unittest.main()
