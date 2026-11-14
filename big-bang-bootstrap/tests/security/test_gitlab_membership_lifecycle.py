"""Native membership API state machine over loopback HTTPS; no actual accounts."""
import json,os,ssl,subprocess,tempfile,threading,unittest,datetime as dt
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit,parse_qs
ROOT=Path(__file__).resolve().parents[2]
class MembershipAPI(unittest.TestCase):
 def test_grant_repeat_partial_response_revoke_and_inherited_refusal(self):
  with tempfile.TemporaryDirectory(prefix='gitlab-membership-api-') as directory:
   d=Path(directory);subprocess.run(['openssl','req','-x509','-newkey','rsa:2048','-nodes','-days','1','-subj','/CN=localhost','-addext','subjectAltName=DNS:localhost','-keyout',str(d/'key'),'-out',str(d/'ca')],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
   (d/'ca').chmod(0o644)
   state={'reader_scope':['api'],'writer_admin':False,'writer_bot':True,'child_parent':30,'parent_path':'tenants','parent_visibility':'private','direct':None,'inherited':False,'writes':[],'failCreate':False,'subject':'11111111-1111-4111-8111-111111111111','foreignProject':{'id':99,'access_level':30}}
   class H(BaseHTTPRequestHandler):
    def log_message(self,*a):pass
    def respond(self,code,value=None):
     self.send_response(code);self.send_header('Content-Type','application/json');self.end_headers()
     if value is not None:self.wfile.write(json.dumps(value).encode())
    def do_GET(self):
     path=urlsplit(self.path).path
     expected='OFFLINE-NATIVE-TOKEN'
     if self.headers.get('PRIVATE-TOKEN')!=expected:return self.respond(403,{})
     if path=='/api/v4/user':return self.respond(200,{'id':90,'bot':state['writer_bot'],'is_admin':state['writer_admin'],'state':'active'})
     if path=='/api/v4/personal_access_tokens/self':return self.respond(200,{'id':80,'user_id':90,'active':True,'revoked':False,'scopes':state['reader_scope']})
     if path=='/api/v4/groups/30/members/90':return self.respond(200,{'id':90,'access_level':50})
     if path=='/api/v4/groups/30/access_tokens/80':return self.respond(200,{'id':80,'user_id':90,'access_level':50})
     if path=='/api/v4/version':return self.respond(200,{'version':'19.4.2-ee'})
     if path=='/api/v4/users/21':return self.respond(200,{'id':21,'is_admin':False,'state':'active','identities':[{'provider':'openid_connect','extern_uid':state['subject']}]})
     if path=='/api/v4/groups/31':return self.respond(200,{'id':31,'full_path':'tenants/example','visibility':'private','parent_id':state['child_parent']})
     if path=='/api/v4/groups/30':return self.respond(200,{'id':30,'full_path':state['parent_path'],'visibility':state['parent_visibility'],'parent_id':None})
     if path in ('/api/v4/groups/31/members/21','/api/v4/groups/31/members/all/21'):
      value=state['direct'] or ({'id':21,'access_level':30} if '/all/' in path and state['inherited'] else None)
      return self.respond(200,value) if value else self.respond(404,{'message':'404 Member Not Found'})
     return self.respond(404,{})
    def do_POST(self):
     if self.headers.get('PRIVATE-TOKEN')!='OFFLINE-NATIVE-TOKEN':return self.respond(403,{})
     if self.path!='/api/v4/groups/31/members':return self.respond(404,{})
     body=json.loads(self.rfile.read(int(self.headers['Content-Length'])));assert body=={'user_id':21,'access_level':30}
     state['direct']={'id':21,'access_level':30};state['writes'].append('create')
     return self.respond(503,{}) if state['failCreate'] else self.respond(201,state['direct'])
    def do_DELETE(self):
     if self.headers.get('PRIVATE-TOKEN')!='OFFLINE-NATIVE-TOKEN':return self.respond(403,{})
     assert urlsplit(self.path).path=='/api/v4/groups/31/members/21'
     assert parse_qs(urlsplit(self.path).query)=={'skip_subresources':['true'],'unassign_issuables':['false']}
     state['direct']=None;state['writes'].append('delete');return self.respond(204)
   server=ThreadingHTTPServer(('127.0.0.1',0),H);ctx=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER);ctx.load_cert_chain(d/'ca',d/'key');server.socket=ctx.wrap_socket(server.socket,server_side=True);threading.Thread(target=server.serve_forever,daemon=True).start()
   self.addCleanup(server.server_close);self.addCleanup(server.shutdown)
   token=d/'token';token.write_text('OFFLINE-NATIVE-TOKEN');token.chmod(0o600)
   evidence=d/'attestation.json';grant=d/'gitlab-member-11111111-1111-4111-8111-111111111111.json'
   receipt=d/'group-receipt.json';receipt.write_text(json.dumps({'schema':1,'context':'example','origin':'https://localhost:'+str(server.server_port),'source_revision':'a'*40,'parent_id':30,'group_id':31,'stage':'group-ready'}));receipt.chmod(0o600)
   variables={'gitlab_membership_context':'example','gitlab_membership_source_revision':'a'*40,'gitlab_native_role':'tenant-developer','gitlab_membership_run':True,'gitlab_membership_recovery_verified':True,'gitlab_native_origin':'https://localhost:'+str(server.server_port),'gitlab_native_ca_file':str(d/'ca'),'gitlab_native_user_id':21,'gitlab_native_subject':'11111111-1111-4111-8111-111111111111','gitlab_native_group_id':31,'gitlab_native_group_path':'tenants/example','gitlab_native_access_level':30}
   attestation={'schema':1,'context':'example','origin':'https://localhost:'+str(server.server_port),'subject':state['subject'],'source_revision':'a'*40,'native_user_id':21,'stage':'IdentityVerified','captured_at':dt.datetime.now(dt.timezone.utc).isoformat()}
   def run(operation='grant',check=False):
    evidence.write_text(json.dumps(attestation));evidence.chmod(0o600)
    vf=d/'vars.json';vf.write_text(json.dumps({**variables,'gitlab_membership_operation':operation,'gitlab_membership_scope':'gitlab-membership-'+operation+'-v1'}));vf.chmod(0o600)
    command=['bash',str(ROOT/'configuration/packages/gitlab/run-membership.sh'),'--apply',str(token),str(evidence),str(receipt),str(vf),str(grant)]
    if check: command=['ansible-playbook','-i','localhost,',str(ROOT/'configuration/packages/gitlab/reconcile-membership.yaml'),'-e','@'+str(vf),'--check']
    r=subprocess.run(command,env={**os.environ,'ANSIBLE_LOCAL_TEMP':str(d/'local'),'ANSIBLE_REMOTE_TEMP':str(d/'remote')},capture_output=True,text=True,timeout=60);self.assertNotIn('OFFLINE-NATIVE-TOKEN',r.stdout+r.stderr);self.assertNotIn('OFFLINE-READER-TOKEN',r.stdout+r.stderr);return r
   def ok(*args,**kwargs):
    r=run(*args,**kwargs);self.assertEqual(r.returncode,0,r.stdout+r.stderr);return r
   ok(check=True);self.assertFalse(state['writes']);state['failCreate']=True;first=run();self.assertNotEqual(first.returncode,0);self.assertEqual(state['writes'],['create'],first.stdout+first.stderr)
   pending=json.loads(grant.read_text())
   for offset in (-360,60):
    stale={**pending,'attempted_at':(dt.datetime.now(dt.timezone.utc)+dt.timedelta(seconds=offset)).isoformat()};grant.write_text(json.dumps(stale));before=list(state['writes']);self.assertNotEqual(run().returncode,0);self.assertEqual(state['writes'],before)
   grant.write_text(json.dumps(pending))
   state['failCreate']=False;ok();self.assertEqual(json.loads(grant.read_text())['stage'],'Granted');self.assertIn('changed=0',ok().stdout);self.assertEqual(state['writes'],['create'])
   ok('revoke');self.assertEqual(state['writes'],['create','delete']);self.assertIn('changed=0',ok('revoke').stdout)
   state['inherited']=True;before=list(state['writes']);self.assertNotEqual(run().returncode,0);self.assertEqual(state['writes'],before)
   state['inherited']=False;ok();state['inherited']=True;self.assertNotEqual(run('revoke').returncode,0);self.assertIsNone(state['direct']);self.assertTrue(state['inherited'])
   state['inherited']=False;attestation['subject']='another-subject';before=list(state['writes']);self.assertNotEqual(run().returncode,0);self.assertEqual(state['writes'],before);self.assertEqual(state['foreignProject'],{'id':99,'access_level':30})

   attestation['subject']='11111111-1111-4111-8111-111111111111'
   for changes in [{'stage':'PendingAccountApproval'},{'captured_at':(dt.datetime.now(dt.timezone.utc)-dt.timedelta(minutes=6)).isoformat()},{'captured_at':(dt.datetime.now(dt.timezone.utc)+dt.timedelta(minutes=1)).isoformat()},{'native_user_id':22},{'context':'foreign'}]:
    old=dict(attestation);attestation.update(changes);before=list(state['writes']);self.assertNotEqual(run().returncode,0);self.assertEqual(state['writes'],before);attestation.clear();attestation.update(old)
   # Revocation remains possible with blocked/missing fresh identity evidence.
   attestation['stage']='PendingAccountApproval';ok('revoke');self.assertEqual(json.loads(grant.read_text())['stage'],'Revoked')
   for key,value in [('writer_admin',True),('writer_bot',False),('reader_scope',['api','sudo']),('child_parent',99),('parent_path','foreign'),('parent_visibility','public')]:
    old=state[key];state[key]=value;attestation['stage']='IdentityVerified';before=list(state['writes']);self.assertNotEqual(run().returncode,0);self.assertEqual(state['writes'],before);state[key]=old
   state['direct']={'id':21,'access_level':30};attestation['stage']='IdentityVerified'
   for op in ('grant','revoke'):
    before=list(state['writes']);self.assertNotEqual(run(op).returncode,0);self.assertEqual(state['writes'],before)
   grant.unlink();before=list(state['writes']);self.assertNotEqual(run('revoke').returncode,0);self.assertEqual(state['writes'],before)
