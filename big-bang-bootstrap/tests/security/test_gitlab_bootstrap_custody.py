"""Host transaction/TLS custody fixtures; no Rails or native token creation."""
import copy,datetime as dt,importlib.util,json,os,ssl,subprocess,tempfile,threading,unittest
from pathlib import Path
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
ROOT=Path(__file__).resolve().parents[2];SETUP=ROOT/'configuration/packages/gitlab/enrollment/setup'
spec=importlib.util.spec_from_file_location('bootstrap_fixture',SETUP/'bootstrap-gitlab.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
class Custody(unittest.TestCase):
 def test_exact_authority_cas_uncertainty_and_redaction(self):
  with tempfile.TemporaryDirectory(prefix='identity-custody-') as directory:
   root=Path(directory);subprocess.run(['openssl','req','-x509','-newkey','rsa:2048','-nodes','-days','1','-subj','/CN=localhost','-addext','subjectAltName=DNS:localhost','-keyout',str(root/'key'),'-out',str(root/'ca')],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL);(root/'ca').chmod(0o644)
   state={'policies':[mod.POLICY],'policy':(SETUP/'gitlab-custody-policy.hcl').read_text(),'ttl':1800,'records':{},'writes':0,'fail_write':0,'readback_bad':False}
   class H(BaseHTTPRequestHandler):
    def log_message(self,*a):pass
    def reply(self,code,value):self.send_response(code);self.send_header('Content-Type','application/json');self.end_headers();self.wfile.write(json.dumps(value).encode())
    def do_GET(self):
     if self.headers.get('X-Vault-Token')!='OFFLINE-BAO-OPERATOR':return self.reply(403,{})
     if self.path=='/v1/auth/token/lookup-self':return self.reply(200,{'data':{'policies':state['policies'],'identity_policies':[],'renewable':False,'ttl':state['ttl']}})
     if self.path=='/v1/sys/policies/acl/'+mod.POLICY:return self.reply(200,{'data':{'policy':state['policy']}})
     for path in mod.RECORDS.values():
      if self.path=='/v1/platform/metadata/'+path:return self.reply(200,{'data':{'current_version':1}}) if path in state['records'] else self.reply(404,{})
      if self.path=='/v1/platform/data/'+path:
       return self.reply(200,{'data':{'metadata':{'version':1},'data':{} if state['readback_bad'] else state['records'][path]}}) if path in state['records'] else self.reply(404,{})
     return self.reply(403,{})
    def do_POST(self):
     if self.headers.get('X-Vault-Token')!='OFFLINE-BAO-OPERATOR':return self.reply(403,{})
     path=self.path.removeprefix('/v1/platform/data/');body=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
     if path not in mod.RECORDS.values() or body.get('options')!={'cas':0} or path in state['records']:return self.reply(400,{})
     state['writes']+=1;state['records'][path]=body['data'];self.reply(503 if state['writes']==state['fail_write'] else 200,{'data':{'version':1}})
   server=ThreadingHTTPServer(('127.0.0.1',0),H);tls=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER);tls.load_cert_chain(root/'ca',root/'key');server.socket=tls.wrap_socket(server.socket,server_side=True);threading.Thread(target=server.serve_forever,daemon=True).start();self.addCleanup(server.server_close);self.addCleanup(server.shutdown)
   token=root/'operator';token.write_text('OFFLINE-BAO-OPERATOR');token.chmod(0o600);d={'setup_id':'a'*64,'bao_origin':'https://localhost:'+str(server.server_port),'ca_file':str(root/'ca'),'expires_at':str(dt.datetime.now(dt.timezone.utc).date()+dt.timedelta(days=2))};minted={'stage':'Minted','parent_id':30,'writer_token_id':40,'reader_token_id':41,'writer_token':'OFFLINE-WRITER-SECRET','reader_token':'OFFLINE-READER-SECRET'};native=[];serial=0
   def run(native_error=False,revoke_error=False):
    nonlocal serial
    serial+=1;r=root/('receipt-'+str(serial));native.clear()
    def call(data,mode='mint',owned=None):
     native.append(mode)
     if mode=='mint':
      if native_error:raise mod.Blocked('NativeExecutionUncertain')
      return dict(minted)
     self.assertEqual({k:owned[k] for k in ('parent_id','writer_token_id','reader_token_id')},{'parent_id':30,'writer_token_id':40,'reader_token_id':41})
     if revoke_error:raise mod.Blocked('NativeExecutionUncertain')
     return {'stage':'Revoked'}
    result=mod.execute(d,str(token),str(r),native_call=call);public=json.dumps(result)+(r.read_text() if r.exists() else '')
    for secret in ('OFFLINE-BAO-OPERATOR','OFFLINE-WRITER-SECRET','OFFLINE-READER-SECRET'):self.assertNotIn(secret,public)
    return result,r
   for key,bad in [('policies',['root']),('policies',[mod.POLICY,'default']),('ttl',7200),('policy','path "*" { capabilities=["sudo"] }')]:
    prior=state[key];state[key]=bad;result,r=run();self.assertEqual(result['stage'],'BlockedBeforeNative');self.assertFalse(r.exists());self.assertEqual(native,[]);state[key]=prior
   state['records'][mod.RECORDS['reader']]={'foreign':True};result,r=run();self.assertEqual(result['stage'],'BlockedBeforeNative');self.assertEqual(native,[]);state['records'].clear()
   result,r=run(native_error=True);self.assertEqual(result['stage'],'ManualRecovery');self.assertEqual(native,['mint']);self.assertEqual(result['revocation'],'NotVerified')
   for failure in (1,2):
    state.update(records={},writes=0,fail_write=failure);result,r=run();self.assertEqual(result['stage'],'ManualRecovery');self.assertEqual(native,['mint','revoke']);self.assertEqual(result['revocation'],'Revoked');self.assertEqual(len(state['records']),failure)
   state.update(records={},writes=0,fail_write=1);result,r=run(revoke_error=True);self.assertEqual(result['revocation'],'Unverified');self.assertEqual(result['stage'],'ManualRecovery')
   state.update(records={},writes=0,fail_write=0,readback_bad=True);result,r=run();self.assertEqual(result['category'],'CustodyReadbackFailed');self.assertEqual(native,['mint','revoke'])
   state.update(records={},writes=0,fail_write=0,readback_bad=False);result,r=run();self.assertEqual(result['stage'],'GitLabCustodyVerified');self.assertFalse(result['runtime_deployed']);self.assertFalse(result['keycloak_activation']);self.assertEqual(native,['mint']);self.assertEqual(len(state['records']),2)

 def test_native_pipe_never_uses_tokens_in_arguments_or_reports_raw_failure(self):
  from unittest.mock import patch
  d={'run':True,'allow_parent_create':True,'setup_id':'a'*64,'actor_native_id':3,'actor_subject':'11111111-1111-4111-8111-111111111111','gitlab_origin':'https://gitlab.invalid','expires_at':'2099-01-01','toolbox_pod':'gitlab-toolbox-test','toolbox_uid':'pod','gitlab_namespace_uid':'namespace'}
  calls=[]
  def fake(argv,input=None):
   calls.append((argv,input))
   if 'namespace' in argv:return b'{"metadata":{"uid":"namespace"}}'
   if 'get' in argv:return b'{"metadata":{"uid":"pod"}}'
   self.assertNotIn('OFFLINE-SECRET',' '.join(argv));return b'boot output\nPERKFORGE_RESULT:{"stage":"ManualRecovery"}\n'
  with patch.object(mod,'command',side_effect=fake):self.assertEqual(mod.native(d)['stage'],'ManualRecovery')
  self.assertEqual(calls[-1][0][-3:],['gitlab-rails','runner','-']);self.assertIn(b'Base64.strict_decode64',calls[-1][1])
  with patch.object(mod.subprocess,'run',return_value=subprocess.CompletedProcess([],1,b'OFFLINE-SECRET',b'OFFLINE-SECRET')):
   with self.assertRaisesRegex(mod.Blocked,'^NativeExecutionUncertain$'):mod.command(['fixed-command'])
