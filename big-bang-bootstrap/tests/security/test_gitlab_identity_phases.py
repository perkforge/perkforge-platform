import copy,importlib.util,datetime as dt,hashlib,json,os,ssl,subprocess,tempfile,threading,unittest
from pathlib import Path
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from urllib.parse import urlsplit,parse_qs
ROOT=Path(__file__).resolve().parents[2]
PHASE=ROOT/'configuration/packages/gitlab/enrollment/phases'
spec=importlib.util.spec_from_file_location('context_contract',PHASE.parent/'identity_context.py');context_contract=importlib.util.module_from_spec(spec);spec.loader.exec_module(context_contract)
class IdentityPhases(unittest.TestCase):
 def test_native_attestor_cas_pending_and_retry_fences(self):
  with tempfile.TemporaryDirectory(prefix='identity-phases-') as directory:
   root=Path(directory);subprocess.run(['openssl','req','-x509','-newkey','rsa:2048','-nodes','-days','1','-subj','/CN=localhost','-addext','subjectAltName=DNS:localhost','-keyout',str(root/'key'),'-out',str(root/'ca')],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
   roles={'tenant-admin':'admins','tenant-developer':'developers','tenant-viewer':'viewers'};groups={r:f'00000000-0000-4000-8000-{i:012d}' for i,r in enumerate(roles,1)};subject='11111111-1111-4111-8111-111111111111';uid='22222222-2222-4222-8222-222222222222'
   state={'calls':0,'patches':0,'native_writes':0,'pending':False,'member':False,'data':{},'rv':1,'desired':'','race':False,'foreign':False}
   class Handler(BaseHTTPRequestHandler):
    def log_message(self,*args):pass
    def respond(self,code,value):self.send_response(code);self.send_header('Content-Type','application/json');self.end_headers();self.wfile.write(json.dumps(value).encode())
    def cm(self):return {'metadata':{'uid':uid if not state['foreign'] else '33333333-3333-4333-8333-333333333333','name':'portal-identity-evidence','namespace':'tenant-identity-writer','resourceVersion':str(state['rv']),'labels':{'app.kubernetes.io/managed-by':'perkforge-identity','perkforge.dev/context':'portal'},'annotations':{'perkforge.dev/desired-invocation':state['desired']}},'data':state['data']}
    def do_POST(self):
     state['calls']+=1
     if self.path!='/auth/realms/perkforge/protocol/openid-connect/token':state['native_writes']+=1;return self.respond(405,{})
     body=parse_qs(self.rfile.read(int(self.headers['Content-Length'])).decode())
     if body!={'grant_type':['client_credentials'],'client_id':['snapshot-reader'],'client_secret':['OFFLINE-KC-SECRET']}:return self.respond(403,{})
     self.respond(200,{'token_type':'Bearer','access_token':'OFFLINE-KC-ACCESS'})
    def do_GET(self):
     state['calls']+=1;p=urlsplit(self.path).path
     if p.startswith('/auth/admin/'):
      if self.headers.get('Authorization')!='Bearer OFFLINE-KC-ACCESS':return self.respond(403,{})
      role=next((r for r,g in groups.items() if '/groups/'+g in p),None)
      if not role:return self.respond(403,{})
      if p.endswith('/members'):return self.respond(200,[{'id':subject,'enabled':True}] if state['member'] and role=='tenant-developer' else [])
      return self.respond(200,{'id':groups[role],'path':'/tenants/portal/'+roles[role],'subGroupCount':0})
     if p.startswith('/api/v4/'):
      if self.headers.get('PRIVATE-TOKEN')!='OFFLINE-READER':return self.respond(403,{})
      if p.endswith('/personal_access_tokens/self'):return self.respond(200,{'active':True,'revoked':False,'scopes':['read_api'],'expires_at':'2099-01-01'})
      if p.endswith('/users'):return self.respond(200,[] if state['pending'] else [{'id':21,'is_admin':False,'state':'active','identities':[{'provider':'openid_connect','extern_uid':subject}]}])
     if p=='/api/v1/namespaces/tenant-identity-writer/configmaps/portal-identity-evidence':
      if self.headers.get('Authorization')!='Bearer OFFLINE-API':return self.respond(403,{})
      response=self.cm()
      if state['race']:state['rv']+=1
      return self.respond(200,response)
     self.respond(404,{})
    def do_PATCH(self):
     state['calls']+=1
     if self.path!='/api/v1/namespaces/tenant-identity-writer/configmaps/portal-identity-evidence' or self.headers.get('Authorization')!='Bearer OFFLINE-API':return self.respond(403,{})
     ops=json.loads(self.rfile.read(int(self.headers['Content-Length'])));expected=[{'op':'test','path':'/metadata/uid','value':uid},{'op':'test','path':'/metadata/resourceVersion','value':str(state['rv'])},{'op':'test','path':'/metadata/annotations/perkforge.dev~1desired-invocation','value':state['desired']}]
     if ops[:3]!=expected:return self.respond(409,{})
     if len(ops)!=4 or ops[3]['op']!='add' or ops[3]['path']!='/data' or set(ops[3]['value'])!={'receipt.json'}:return self.respond(400,{})
     state['patches']+=1;state['rv']+=1;state['data']=ops[3]['value'];self.respond(200,self.cm())
   server=ThreadingHTTPServer(('127.0.0.1',0),Handler);ctx=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER);ctx.load_cert_chain(root/'ca',root/'key');server.socket=ctx.wrap_socket(server.socket,server_side=True);threading.Thread(target=server.serve_forever,daemon=True).start();self.addCleanup(server.server_close);self.addCleanup(server.shutdown)
   origin='https://localhost:'+str(server.server_port);base={'identity_membership_recovery_verified':True,'identity_run':True,'identity_scope':'gitlab-identity-attest-v1','identity_context':'portal','identity_source_revision':'a'*40,'identity_platform_revision':'b'*40,'identity_contract_sha256':hashlib.sha256((ROOT/'configuration/authorization/contexts/portal.yaml').read_bytes()).hexdigest(),'identity_previous_invocation':'','identity_retry_generation':0,'identity_gitlab_origin':origin,'identity_keycloak_origin':origin+'/auth','identity_keycloak_realm':'perkforge','identity_kubernetes_origin':origin,'identity_receipt_uid':uid,'identity_receipt_namespace':'tenant-identity-writer','identity_receipt_name':'portal-identity-evidence','identity_group_ids':groups}
   serial=0
   def run(extra=None,mode='--apply',desired=True):
    nonlocal serial
    serial+=1;w=root/str(serial);w.mkdir(mode=0o700);d={**base,**(extra or {})};material={k:v for k,v in d.items() if k not in ('identity_invocation','identity_scope','identity_run')};d['identity_invocation']=hashlib.sha256(json.dumps(material,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    if desired:state['desired']=d['identity_invocation']
    files={'phase-inputs.json':json.dumps(d),'gitlab-reader':'OFFLINE-READER','kc-client-id':'snapshot-reader','kc-client-secret':'OFFLINE-KC-SECRET','api-token':'OFFLINE-API','lab-ca.crt':(root/'ca').read_text(),'api-ca.crt':(root/'ca').read_text()}
    for name,value in files.items():(w/name).write_text(value);(w/name).chmod(0o600)
    r=subprocess.run(['bash',str(PHASE/'run-attestor.sh'),mode,str(w/'phase-inputs.json'),str(w)],capture_output=True,text=True,timeout=90,env={**os.environ,'ANSIBLE_LOCAL_TEMP':str(w/'local'),'ANSIBLE_REMOTE_TEMP':str(w/'remote')})
    self.assertNotIn('OFFLINE-',r.stdout+r.stderr)
    return r,w,d
   r,_,_=run(mode='--validate');self.assertEqual(r.returncode,0,r.stderr);self.assertEqual(state['calls'],0)
   r,w,d=run();self.assertEqual(r.returncode,0,(w/'run.log').read_text() if (w/'run.log').exists() else r.stderr);self.assertEqual(state['patches'],1);self.assertFalse(json.loads(r.stdout)['membership_ready']);first=d['identity_invocation']
   # Same attempt is not silently overwritten with a fresh observation.
   r,_,_=run();self.assertNotEqual(r.returncode,0);self.assertEqual(state['patches'],1)
   state.update(member=True,pending=True);r,w,d=run({'identity_context_digest':context_contract.derive('portal')['digest'],'identity_retry_generation':1,'identity_previous_invocation':first});self.assertEqual(r.returncode,0,(w/'run.log').read_text());self.assertEqual(json.loads(r.stdout)['pending_identity_count'],1);self.assertEqual(state['patches'],2);second=d['identity_invocation']
   # A new authorized retry uses the same code SHA but a new invocation, and notices approval.
   state['pending']=False;r,w,d=run({'identity_context_digest':context_contract.derive('portal')['digest'],'identity_retry_generation':2,'identity_previous_invocation':second});self.assertEqual(r.returncode,0,(w/'run.log').read_text());self.assertEqual(json.loads(r.stdout)['pending_identity_count'],0);third=d['identity_invocation'];self.assertEqual(state['patches'],3)
   for flags in [{'race':True},{'foreign':True}]:
    state.update(flags);r,_,_=run({'identity_retry_generation':3,'identity_previous_invocation':third});self.assertNotEqual(r.returncode,0);self.assertEqual(state['patches'],3);state.update({k:False for k in flags})
   r,_,_=run({'identity_retry_generation':4,'identity_previous_invocation':third},desired=False);self.assertNotEqual(r.returncode,0);self.assertEqual(state['patches'],3)
   self.assertEqual(state['native_writes'],0)
if __name__=='__main__':unittest.main()
