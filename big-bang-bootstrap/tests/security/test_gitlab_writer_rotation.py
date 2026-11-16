"""Synthetic coordinator only; no credentials/native calls."""
import importlib.util,json,os,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[2]
P=ROOT/'configuration/packages/gitlab/enrollment/setup/rotate-writer.py'
spec=importlib.util.spec_from_file_location('rotation',P);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class Rotation(unittest.TestCase):
 def test_custody_and_uncertain_effects(self):
  for failure in (None,'preflight','native-lost','cas','readback','revoke','foreign','persist'):
   with self.subTest(failure=failure),tempfile.TemporaryDirectory(prefix='rotate-fixture-') as tmp:
    root=Path(tmp);root.chmod(0o700);receipt=str(root/'receipt.json');calls=[]
    d={'attempt_id':'a'*64,'original_setup_id':'b'*64,'expected_bot_id':8,'expires_at':'2099-01-01'}
    new={'stage':'Rotated','parent_id':7,'old_token_id':2,'bot_id':8,'attempt_id':d['attempt_id'],'original_setup_id':d['original_setup_id'],'expires_at':d['expires_at'],'successor_id':22,'successor_token':'FAKE_ONLY_NEVER_NATIVE'}
    class Bao:
     def __init__(self,*args):pass
     def preflight(self,d):
      calls.append('preflight')
      if failure=='preflight':raise m.Blocked('CustodyVersionChanged')
     def store(self,d,v):
      calls.append('cas1')
      if failure in ('cas','readback','revoke'):raise m.Blocked('CustodyWriteUncertain')
    def native(d,mode='rotate',successor=None):
     calls.append(mode)
     if mode=='revoke-successor':
      if failure=='revoke':raise m.Blocked('CleanupUnverified')
      return {**new,'stage':'Revoked'}
     if failure=='native-lost':raise m.Blocked('NativeExecutionUncertain')
     return {**new,'bot_id':99} if failure=='foreign' else new.copy()
    save=m.base.save
    def persist(path,state,first=False):
     if failure=='persist' and state['stage']=='NativeRotated':raise OSError('synthetic fsync failure')
     save(path,state,first)
    with patch.object(m.base,'save',side_effect=persist):r=m.execute(d,'never-read',receipt,Bao,native)
    self.assertNotIn(new['successor_token'],json.dumps(r))
    if Path(receipt).exists():self.assertNotIn(new['successor_token'],Path(receipt).read_text())
    if failure is None:self.assertEqual(r['stage'],'WriterCustodyVerified');self.assertEqual(calls,['preflight','rotate','cas1'])
    elif failure=='preflight':self.assertEqual(calls,['preflight']);self.assertFalse(Path(receipt).exists())
    elif failure in ('native-lost','foreign'):self.assertEqual(calls,['preflight','rotate']);self.assertEqual(r['stage'],'ManualRecovery')
    else:self.assertEqual(calls[-1],'revoke-successor');self.assertEqual(r['successor_revocation'],'Unverified' if failure=='revoke' else 'Verified')
    if Path(receipt).exists():
     before=Path(receipt).read_bytes();n=len(calls);m.execute(d,'never-read',receipt,Bao,native);self.assertEqual(len(calls),n);self.assertEqual(Path(receipt).read_bytes(),before)
 def test_exact_bao_record_and_cas(self):
  b=object.__new__(m.Bao);calls=[];written=[];d={'original_setup_id':'b'*64,'attempt_id':'a'*64,'expires_at':'2099-01-01'}
  old={'token':'FAKE_OLD','setup_id':d['original_setup_id'],'native_token_id':2,'expires_at':'2026-11-16'}
  def call(path,method='GET',body=None,**kw):
   calls.append(path)
   if path=='auth/token/lookup-self':return {'data':{'policies':[m.POLICY],'identity_policies':[],'renewable':False,'period':0,'ttl':1800,'explicit_max_ttl':3600}}
   if path=='sys/policies/acl/'+m.POLICY:return {'data':{'policy':(m.HERE/'writer-rotation-policy.hcl').read_text()}}
   if path=='platform/metadata/'+m.RECORD:return {'data':{'current_version':1}}
   self.assertEqual(path,'platform/data/'+m.RECORD)
   if method=='POST':self.assertEqual(body['options'],{'cas':1});written.append(body['data']);return {'data':{'version':2}}
   return {'data':{'metadata':{'version':2 if written else 1},'data':written[-1] if written else old}}
  b.call=call;b.preflight(d);b.store(d,{'successor_token':'FAKE_NEW','successor_id':22})
  self.assertTrue(all('tenant-reader' not in x and '/auth/token/create' not in x for x in calls));self.assertEqual(written[0]['previous_native_token_id'],2)
  old['native_token_id']=99;written.clear()
  with self.assertRaises(m.Blocked):b.preflight(d)
 def test_literal_selection_and_actual_expiry(self):
  import datetime as dt
  with tempfile.TemporaryDirectory(prefix='rotate-inputs-') as tmp:
   root=Path(tmp);root.chmod(0o700)
   def save(name,v):
    p=root/name;p.write_text(v if isinstance(v,str) else json.dumps(v));p.chmod(0o600);return str(p)
   token=save('operator','FAKE-ONLY');ca=save('ca','FAKE PUBLIC CA')
   old=save('original.json',{'stage':'GitLabCustodyVerified','parent_id':7,'writer_token_id':2,'setup_id':'b'*64,'stored':['reader','writer']})
   d={'scope':'gitlab-tenants-writer-rotation-v1','attempt_id':'a'*64,'actor_subject':m.SUBJECT,'gitlab_origin':'https://gitlab.example.test','bao_origin':'https://bao.example.test','ca_file':ca,'toolbox_pod':'gitlab-toolbox-abc','toolbox_uid':'a'*8+'-'+('a'*4+'-')*3+'a'*12,'gitlab_namespace_uid':'b'*8+'-'+('b'*4+'-')*3+'b'*12,'expires_at':str(dt.datetime.now(dt.timezone.utc).date()+dt.timedelta(days=2)),'original_receipt_file':old,'actor_native_id':3,'parent_id':7,'old_token_id':2,'expected_record_version':1,'run':True,'expected_bot_id':8}
   receipt=str(root/'new.json');inputs=save('inputs.json',d)
   self.assertEqual(m.validate(token,receipt,inputs)['original_setup_id'],'b'*64)
   for change in ({'expires_at':str(dt.datetime.now(dt.timezone.utc).date())},{'expected_record_version':2},{'old_token_id':3},{'actor_native_id':1},{'expected_bot_id':True},{'gitlab_origin':'{{ lookup("pipe","false") }}'},{'extra':'override'}):
    inputs=save('inputs.json',{**d,**change})
    with self.assertRaises((m.Blocked,ValueError)):m.validate(token,receipt,inputs)
 def test_real_tls_custody_roundtrip(self):
  import ssl,subprocess,threading
  from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
  with tempfile.TemporaryDirectory(prefix='rotate-tls-') as tmp:
   p=Path(tmp);p.chmod(0o700)
   subprocess.run(['openssl','req','-x509','-newkey','rsa:2048','-nodes','-days','1','-subj','/CN=localhost','-addext','subjectAltName=DNS:localhost','-keyout',str(p/'key'),'-out',str(p/'ca')],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL);(p/'ca').chmod(0o644)
   token=p/'operator';token.write_text('FAKE_OPERATOR');token.chmod(0o600)
   old={'token':'FAKE_EXPIRED','setup_id':'b'*64,'native_token_id':2,'expires_at':'2026-11-16'};state={'data':old,'version':1,'posts':0}
   class H(BaseHTTPRequestHandler):
    def log_message(self,*a):pass
    def reply(self,v):self.send_response(200);self.send_header('Content-Type','application/json');self.end_headers();self.wfile.write(json.dumps(v).encode())
    def do_GET(self):
     assert self.headers.get('X-Vault-Token')=='FAKE_OPERATOR'
     if self.path=='/v1/auth/token/lookup-self':return self.reply({'data':{'policies':[m.POLICY],'identity_policies':[],'renewable':False,'period':0,'ttl':1800,'explicit_max_ttl':3600}})
     if self.path=='/v1/sys/policies/acl/'+m.POLICY:return self.reply({'data':{'policy':(m.HERE/'writer-rotation-policy.hcl').read_text()}})
     if self.path=='/v1/platform/metadata/'+m.RECORD:return self.reply({'data':{'current_version':state['version']}})
     assert self.path=='/v1/platform/data/'+m.RECORD
     return self.reply({'data':{'metadata':{'version':state['version']},'data':state['data']}})
    def do_POST(self):
     assert self.headers.get('X-Vault-Token')=='FAKE_OPERATOR' and self.path=='/v1/platform/data/'+m.RECORD
     body=json.loads(self.rfile.read(int(self.headers['Content-Length'])));assert body['options']=={'cas':1} and state['version']==1
     state.update(data=body['data'],version=2,posts=state['posts']+1);self.reply({'data':{'version':2}})
   server=ThreadingHTTPServer(('127.0.0.1',0),H);ctx=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER);ctx.load_cert_chain(p/'ca',p/'key');server.socket=ctx.wrap_socket(server.socket,server_side=True);threading.Thread(target=server.serve_forever,daemon=True).start();self.addCleanup(server.server_close);self.addCleanup(server.shutdown)
   d={'attempt_id':'a'*64,'original_setup_id':'b'*64,'expected_bot_id':8,'expires_at':'2099-01-01','bao_origin':'https://localhost:'+str(server.server_port),'ca_file':str(p/'ca')}
   def native(d,*a):return {'stage':'Rotated','parent_id':7,'old_token_id':2,'bot_id':8,'attempt_id':d['attempt_id'],'original_setup_id':d['original_setup_id'],'expires_at':d['expires_at'],'successor_id':22,'successor_token':'FAKE_SUCCESSOR'}
   result=m.execute(d,str(token),str(p/'receipt.json'),native_call=native)
   self.assertEqual(result['stage'],'WriterCustodyVerified');self.assertEqual(state['posts'],1);self.assertNotIn('FAKE_SUCCESSOR',(p/'receipt.json').read_text())
 def test_default_inert(self):
  import subprocess
  r=subprocess.run(['python3',str(P)],capture_output=True,text=True);self.assertEqual(r.returncode,0);self.assertEqual(r.stdout.strip(),'INERT')
if __name__=='__main__':unittest.main()
