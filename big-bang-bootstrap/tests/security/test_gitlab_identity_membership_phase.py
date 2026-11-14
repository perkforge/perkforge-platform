"""Actual Ansible/writer over local TLS; projection stand-in is not runtime issuer proof."""
import datetime as dt,hashlib,json,os,shutil,ssl,subprocess,tempfile,threading,time,unittest
from pathlib import Path
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from urllib.parse import urlsplit,parse_qs
ROOT=Path(__file__).resolve().parents[2]
class MembershipPhase(unittest.TestCase):
 def test_empty_pending_three_subject_repeat_and_revocation(self):
  with tempfile.TemporaryDirectory(prefix='membership-phase-') as directory:
   root=Path(directory);repo=root/'gitlab';shutil.copytree(ROOT/'configuration/packages/gitlab',repo);phase=repo/'enrollment/phases'
   helper=root/'refresh';helper.write_text('#!/usr/bin/env python3\nimport shutil,sys,json\nfrom pathlib import Path\nw=Path(sys.argv[2]);counter=w/"refresh-count";n=int(counter.read_text())+1 if counter.exists() else 1;counter.write_text(str(n))\nif (w/"mutate").exists() and n==3:\n e=json.loads((w/"projection.json").read_text());e["snapshot"]["members"].pop();e["identities"].pop();(w/"projection.json").write_text(json.dumps(e))\nshutil.copyfile(w/"projection.json",w/"envelope.json")\n');helper.chmod(0o700)
   for name in ('member-one.yaml','memberships.yaml'):
    p=phase/name;p.write_text(p.read_text().replace('/opt/perkforge/bin/refresh-identity-evidence',str(helper)))
   subprocess.run(['openssl','req','-x509','-newkey','rsa:2048','-nodes','-days','1','-subj','/CN=localhost','-addext','subjectAltName=DNS:localhost','-keyout',str(root/'key'),'-out',str(root/'ca')],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
   state={'members':{},'writes':[],'calls':0,'fail':False}
   class H(BaseHTTPRequestHandler):
    def log_message(self,*a):pass
    def response(self,code,value=None):
     self.send_response(code);self.send_header('Content-Type','application/json');self.end_headers()
     if value is not None:self.wfile.write(json.dumps(value).encode())
    def do_GET(self):
     state['calls']+=1
     if self.headers.get('PRIVATE-TOKEN')!='OFFLINE-WRITER':return self.response(403,{})
     p=urlsplit(self.path).path
     fixed={'/api/v4/user':{'id':90,'bot':True,'state':'active'},'/api/v4/personal_access_tokens/self':{'id':80,'user_id':90,'active':True,'revoked':False,'scopes':['api']},'/api/v4/groups/30/members/90':{'id':90,'access_level':50},'/api/v4/groups/30/access_tokens/80':{'id':80,'user_id':90,'access_level':50},'/api/v4/version':{'version':'19.4.2-ee'},'/api/v4/groups/30':{'id':30,'full_path':'tenants','visibility':'private','parent_id':None},'/api/v4/groups/31':{'id':31,'full_path':'tenants/portal','visibility':'private','parent_id':30}}
     if p in fixed:return self.response(200,fixed[p])
     if p.startswith('/api/v4/users/'):return self.response(200,{'id':int(p.rsplit('/',1)[1]),'state':'active'})
     if p.startswith('/api/v4/groups/31/members/'):
      ident=int(p.rsplit('/',1)[1]);return self.response(200,{'id':ident,'access_level':state['members'][ident]}) if ident in state['members'] else self.response(404,{})
     return self.response(404,{})
    def do_POST(self):
     if self.headers.get('PRIVATE-TOKEN')!='OFFLINE-WRITER' or self.path!='/api/v4/groups/31/members':return self.response(403,{})
     b=json.loads(self.rfile.read(int(self.headers['Content-Length'])));state['members'][b['user_id']]=b['access_level'];state['writes'].append(['grant',b['user_id']]);return self.response(503 if state['fail'] else 201,{'id':b['user_id'],'access_level':b['access_level']})
    def do_DELETE(self):
     if self.headers.get('PRIVATE-TOKEN')!='OFFLINE-WRITER':return self.response(403,{})
     assert parse_qs(urlsplit(self.path).query)=={'skip_subresources':['true'],'unassign_issuables':['false']}
     ident=int(urlsplit(self.path).path.rsplit('/',1)[1]);state['members'].pop(ident,None);state['writes'].append(['revoke',ident]);return self.response(204)
   server=ThreadingHTTPServer(('127.0.0.1',0),H);tls=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER);tls.load_cert_chain(root/'ca',root/'key');server.socket=tls.wrap_socket(server.socket,server_side=True);threading.Thread(target=server.serve_forever,daemon=True).start();self.addCleanup(server.server_close);self.addCleanup(server.shutdown)
   origin='https://localhost:'+str(server.server_port);roles={'tenant-admin':'admins','tenant-developer':'developers','tenant-viewer':'viewers'};groups={r:f'00000000-0000-4000-8000-{i:012d}' for i,r in enumerate(roles,1)};subjects=[f'11111111-1111-4111-8111-{i:012d}' for i in range(1,4)]
   receipt_dir=root/'portal';receipt_dir.mkdir(mode=0o700);group=receipt_dir/'gitlab-group.json';group.write_text(json.dumps({'schema':1,'context':'portal','origin':origin,'source_revision':'a'*40,'parent_id':30,'group_id':31,'stage':'group-ready','previous_revisions':[]}));group.chmod(0o600)
   serial=0;last=''
   def run(members,stages=None,roles_override=None,recovery=True,repeat=False,mutate=False):
    nonlocal serial,last
    serial+=1;work=root/str(serial);work.mkdir(mode=0o700)
    d={'identity_run':True,'identity_membership_recovery_verified':recovery,'identity_scope':'gitlab-identity-memberships-v1','identity_context':'portal','identity_source_revision':'a'*40,'identity_platform_revision':'b'*40,'identity_contract_sha256':'c'*64,'identity_invocation':'','identity_previous_invocation':last,'identity_retry_generation':serial-1,'identity_gitlab_origin':origin,'identity_keycloak_origin':origin+'/auth','identity_keycloak_realm':'perkforge','identity_kubernetes_origin':origin,'identity_receipt_uid':'22222222-2222-4222-8222-222222222222','identity_receipt_namespace':'tenant-identity-writer','identity_receipt_name':'portal-identity-evidence','identity_group_ids':groups}
    if serial==1:d['identity_retry_generation']=0
    if repeat:d.update(previous_d)
    else:d['identity_invocation']=hashlib.sha256(json.dumps({k:v for k,v in d.items() if k not in ('identity_invocation','identity_scope','identity_run')},sort_keys=True,separators=(',',':')).encode()).hexdigest()
    now=dt.datetime.now(dt.timezone.utc).isoformat();foundation=receipt_dir/'foundation-result.json';foundation.write_text(json.dumps({'schema':1,'phase':'GroupReady','context':'portal','invocation':d['identity_invocation'],'source_revision':'a'*40,'platform_revision':'b'*40,'parent_id':30,'group_id':31,'captured_at':now}));foundation.chmod(0o600)
    selected=[{'subject':subjects[i],'role':(roles_override or {}).get(i,'tenant-developer'),'enabled':True} for i in members]
    snap={'schema':1,'stage':'SnapshotVerified','context':'portal','source_revision':'a'*40,'contract_sha256':'c'*64,'origin':origin+'/auth','realm':'perkforge','captured_at':now,'groups':[{'role':r,'id':groups[r],'path':'/tenants/portal/'+roles[r]} for r in sorted(roles)],'members':selected}
    identities=[]
    for i in members:
     stage=(stages or {}).get(i,'IdentityVerified');identities.append({'schema':1,'context':'portal','source_revision':'a'*40,'origin':origin,'subject':subjects[i],'captured_at':now,'stage':stage,**({'native_user_id':21+i} if stage=='IdentityVerified' else {})})
    env={'schema':1,'context':'portal','source_revision':'a'*40,'platform_revision':'b'*40,'contract_sha256':'c'*64,'invocation':d['identity_invocation'],'previous_invocation':d['identity_previous_invocation'],'retry_generation':d['identity_retry_generation'],'receipt_uid':d['identity_receipt_uid'],'captured_at':now,'snapshot':snap,'identities':identities}
    for name,value in {'phase-inputs.json':json.dumps(d),'envelope.json':json.dumps(env),'projection.json':json.dumps(env),'group-writer':'OFFLINE-WRITER','lab-ca.crt':(root/'ca').read_text()}.items():(work/name).write_text(value);(work/name).chmod(0o600)
    if mutate:(work/'mutate').touch()
    start=time.monotonic();p=subprocess.run(['bash',str(phase/'run-memberships.sh'),'--apply',str(work/'phase-inputs.json'),str(work),str(group)],capture_output=True,text=True,timeout=180,env={**os.environ,'ANSIBLE_LOCAL_TEMP':str(work/'local'),'ANSIBLE_REMOTE_TEMP':str(work/'remote')});elapsed=time.monotonic()-start
    self.assertNotIn('OFFLINE-WRITER',p.stdout+p.stderr);last=d['identity_invocation']
    return p,work,d,elapsed
   def ok(*args,**kwargs):
    p,w,d,t=run(*args,**kwargs);self.assertEqual(p.returncode,0,p.stdout+p.stderr+(w/'run.log').read_text() if (w/'run.log').exists() else p.stderr);return json.loads(p.stdout),d,t
   r,previous_d,_=ok([]);self.assertEqual(r['phase'],'NoDesiredMembers');self.assertEqual(state['calls'],0)
   r,previous_d,_=ok([0],{0:'PendingFirstLogin'});self.assertEqual(r['phase'],'MembershipPending');self.assertEqual(state['writes'],[])
   r,previous_d,t=ok([0,1,2]);self.assertEqual(r['phase'],'MembershipReady');self.assertEqual(len(state['writes']),3);self.assertLess(t,180)
   r,previous_d,t=ok([0,1,2],repeat=True);self.assertEqual(r['phase'],'MembershipReady');self.assertEqual(len(state['writes']),3)
   r,previous_d,_=ok([0,1,2],roles_override={0:'tenant-admin'});self.assertEqual(r['phase'],'MembershipPending');self.assertEqual(len(state['writes']),3)
   r,previous_d,_=ok([0],{0:'PendingAccountApproval'});self.assertEqual(r['phase'],'MembershipPending');self.assertEqual(state['members'],{});self.assertEqual(len(state['writes']),6)
   before=state['calls'];p,w,_,_=run([],recovery=False);self.assertNotEqual(p.returncode,0);self.assertEqual(state['calls'],before)

   before=len(state['writes']);p,w,_,_=run([0,1,2],mutate=True);self.assertNotEqual(p.returncode,0);self.assertEqual(json.loads(p.stdout)['phase'],'PartialFailure');self.assertEqual(len(state['writes']),before+1)
