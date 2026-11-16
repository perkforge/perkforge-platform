"""Real local Ansible against synthetic HTTPS only; no native Bao/root access."""
import importlib.util,json,os,ssl,subprocess,tempfile,threading,time,unittest
from pathlib import Path
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
ROOT=Path(__file__).resolve().parents[2];S=ROOT/'configuration/packages/gitlab/enrollment/setup';POLICY='tenant-identity-writer-rotation-v1'
class Issuer(unittest.TestCase):
 def test_native_ansible_synthetic_tls(self):
  with tempfile.TemporaryDirectory(prefix='writer-issuer-') as directory:
   r=Path(directory);subprocess.run(['openssl','req','-x509','-newkey','rsa:2048','-nodes','-days','1','-subj','/CN=localhost','-addext','subjectAltName=DNS:localhost','-keyout',str(r/'key'),'-out',str(r/'ca')],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,check=True);(r/'ca').chmod(0o644)
   state={};cluster='11111111-1111-4111-8111-111111111111';setup='a'*64
   class H(BaseHTTPRequestHandler):
    def log_message(self,*args):pass
    def reply(self,status,data=None):
     self.send_response(status);self.send_header('Content-Type','application/json');self.end_headers()
     if data is not None:self.wfile.write(json.dumps(data).encode())
    def auth(self):
     if self.headers.get('X-Vault-Token')!='FAKE-ROOT':self.reply(403,{});return False
     state['root_calls']+=1;return True
    def do_GET(self):
     state['paths'].append(self.path)
     if self.path=='/v1/sys/health':return self.reply(200,{'cluster_id':cluster if state['mode']!='cluster' else 'wrong','initialized':True,'sealed':False,'version':'2.7.2'})
     if self.path=='/v1/auth/token/lookup-self':
      t=self.headers.get('X-Vault-Token')
      if t=='FAKE-ROOT':state['root_calls']+=1;return self.reply(200,{'data':{'policies':['default'] if state['mode']=='nonroot' else ['root'],'accessor':'ROOT-ACCESSOR'}})
      v=next((x for x in state['tokens'].values() if x['id']==t),None)
      return self.reply(200,{'data':v}) if v else self.reply(403,{})
     if not self.auth():return
     if self.path=='/v1/sys/policies/acl/'+POLICY:return self.reply(404) if state['policy'] is None else self.reply(200,{'data':{'policy':state['policy']}})
     raise AssertionError('unexpected GET '+self.path)
    def do_PUT(self):
     if not self.auth():return
     assert self.path=='/v1/sys/policies/acl/'+POLICY and state['policy'] is None
     body=json.loads(self.rfile.read(int(self.headers['Content-Length'])));state['policy']=body['policy'];state['writes'].append('policy')
     return self.reply(503,{}) if state['mode']=='policy-lost' else self.reply(204)
    def do_POST(self):
     if not self.auth():return
     state['paths'].append(self.path);body=json.loads(self.rfile.read(int(self.headers['Content-Length'])));p=self.path
     if p=='/v1/auth/token/create':
      assert body=={'policies':[POLICY],'no_default_policy':True,'display_name':'identity-writer-rotation-'+setup,'ttl':3600,'explicit_max_ttl':3600,'renewable':False,'type':'service'}
      state['mint']+=1;state['writes'].append('mint');accessor='CHILD-ACCESSOR';token='FAKE.CHILD-TOKEN'
      v={'id':token,'accessor':accessor,'policies':[POLICY],'identity_policies':[],'renewable':False,'period':0,'ttl':3500,'creation_ttl':3600,'creation_time':int(time.time()),'explicit_max_ttl':3600,'display_name':'token-'+body['display_name'],'type':'service','orphan':False}
      if state['mode']=='lowttl':v['ttl']=800
      if state['mode']=='foreign-child':v['display_name']='token-foreign'
      state['tokens'][accessor]=v
      if state['mode']=='lost':return self.reply(503,{})
      return self.reply(200,{'auth':{'client_token':token,'accessor':'ROOT-ACCESSOR' if state['mode']=='root-accessor' else accessor,'policies':[POLICY]+(['default'] if state['mode']=='extra' else []),'identity_policies':[],'renewable':False,'lease_duration':3600,'token_type':'service'}})
     if p=='/v1/auth/token/lookup-accessor':
      assert body['accessor']!='ROOT-ACCESSOR';v=state['tokens'].get(body['accessor'])
      return self.reply(200,{'data':v}) if v else self.reply(400,{'errors':['bad request' if state['mode']=='bad400' else 'invalid accessor']})
     if p=='/v1/auth/token/revoke-accessor':
      assert body['accessor']=='CHILD-ACCESSOR';state['tokens'].pop(body['accessor'],None);state['writes'].append('revoke');return self.reply(204)
     raise AssertionError('unexpected POST '+p)
   server=ThreadingHTTPServer(('127.0.0.1',0),H);tls=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER);tls.load_cert_chain(r/'ca',r/'key');server.socket=tls.wrap_socket(server.socket,server_side=True);threading.Thread(target=server.serve_forever,daemon=True).start();self.addCleanup(server.server_close);self.addCleanup(server.shutdown)
   root=r/'root';root.write_text('FAKE-ROOT');root.chmod(0o600);inputs=r/'inputs.json';inputs.write_text(json.dumps({'run':True,'scope':'writer-rotation-issuer-v1','setup_id':setup,'bao_origin':'https://localhost:'+str(server.server_port),'ca_file':str(r/'ca'),'cluster_id':cluster}));inputs.chmod(0o600);receipt=r/'receipt';output=r/'writer-rotation-setup-token'
   def reset(mode='',policy=None):
    for p in (receipt,output):
     if p.exists():p.unlink()
    state.clear();state.update(mode=mode,policy=policy,tokens={},writes=[],paths=[],root_calls=0,mint=0)
   def run(mode):
    p=subprocess.run(['bash',str(S/'run-writer-issuer.sh'),mode,str(root),str(receipt),str(inputs)],capture_output=True,text=True,timeout=120,env={**os.environ,'ANSIBLE_LOCAL_TEMP':str(r/'local'),'ANSIBLE_REMOTE_TEMP':str(r/'remote'),'PYTHONDONTWRITEBYTECODE':'1'})
    for secret in ('FAKE-ROOT','FAKE.CHILD-TOKEN','CHILD-ACCESSOR','ROOT-ACCESSOR'):self.assertNotIn(secret,p.stdout+p.stderr)
    return p
   reset();self.assertEqual(run('--validate').returncode,0);self.assertEqual(run('inert').returncode,0)
   p=subprocess.run(['ansible-playbook','-i','localhost,',str(S/'writer-issuer.yaml'),'--check'],capture_output=True,text=True,timeout=30);self.assertEqual(p.returncode,0,p.stdout+p.stderr);self.assertEqual(state['paths'],[])
   # Bare apply cannot borrow a lock or reach even public health.
   p=subprocess.run(['ansible-playbook','-i','localhost,',str(S/'writer-issuer.yaml'),'-e','@'+str(inputs),'-e','issuer_mode=apply','-e','issuer_root_file='+str(root),'-e','issuer_receipt_file='+str(receipt),'-e','issuer_inputs_file='+str(inputs)],capture_output=True,text=True,timeout=30,env={**os.environ,'PERKFORGE_GROUP_LOCK_OWNER':'0'})
   self.assertNotEqual(p.returncode,0);self.assertEqual(state['paths'],[]);self.assertFalse(receipt.exists())
   for mode,policy in [('cluster',None),('nonroot',None),('', 'foreign'),('policy-lost',None)]:
    reset(mode,policy);self.assertNotEqual(run('--apply').returncode,0);self.assertEqual(state['mint'],0);self.assertFalse(output.exists())
    if mode=='cluster':self.assertEqual(state['root_calls'],0)
    before=receipt.read_bytes();self.assertNotEqual(run('--apply').returncode,0);self.assertEqual(receipt.read_bytes(),before)
   reset();p=run('--apply');self.assertEqual(p.returncode,0,p.stdout+p.stderr);self.assertEqual(state['writes'],['policy','mint']);self.assertEqual(output.read_text(),'FAKE.CHILD-TOKEN');self.assertEqual(json.loads(receipt.read_text())['stage'],'Issued');before=receipt.read_bytes();self.assertNotEqual(run('--apply').returncode,0);self.assertEqual(before,receipt.read_bytes())
   # A foreign artifact is never unlinked, even after the exact owned child is revoked.
   output.write_text('FOREIGN-TOKEN');self.assertNotEqual(run('--cleanup').returncode,0);self.assertTrue(output.exists());self.assertFalse(state['tokens']);output.write_text('FAKE.CHILD-TOKEN')
   state['mode']='bad400';self.assertNotEqual(run('--cleanup').returncode,0);self.assertTrue(output.exists());state['mode']='';p=run('--cleanup');self.assertEqual(p.returncode,0,p.stdout+p.stderr);self.assertFalse(output.exists());self.assertIsNotNone(state['policy']);self.assertEqual(json.loads(receipt.read_text())['stage'],'Cleaned')
   for mode in ('extra','lowttl','lost','root-accessor','foreign-child'):
    reset(mode,(S/'writer-rotation-policy.hcl').read_text());p=run('--apply');self.assertNotEqual(p.returncode,0,mode);self.assertFalse(output.exists());self.assertEqual(json.loads(receipt.read_text())['stage'],'ManualRecovery');self.assertEqual(state['mint'],1)
    self.assertEqual(len(state['tokens']),0 if mode in ('extra','lowttl') else 1)
    before=receipt.read_bytes();self.assertNotEqual(run('--apply').returncode,0);self.assertEqual(receipt.read_bytes(),before);self.assertEqual(state['mint'],1)
    self.assertFalse(any('/platform/' in p or '/sys/auth' in p or '/kubernetes' in p for p in state['paths']))
 def test_literal_private_selection(self):
  spec=importlib.util.spec_from_file_location('wi',S/'writer-issuer-state.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
  with tempfile.TemporaryDirectory(prefix='writer-issuer-input-') as x:
   r=Path(x);root=r/'root';root.write_text('FAKE-ROOT');root.chmod(0o600);ca=r/'ca';ca.write_text('fakeCA');ca.chmod(0o600);p=r/'input';receipt=r/'receipt'
   d={'run':True,'scope':'writer-rotation-issuer-v1','setup_id':'a'*64,'bao_origin':'https://localhost','ca_file':str(ca),'cluster_id':'11111111-1111-4111-8111-111111111111'}
   def put(v):p.write_text(json.dumps(v));p.chmod(0o600)
   put(d);m.select(str(root),str(receipt),str(p))
   for bad in [dict(d,run='true'),dict(d,setup_id='{{ lookup("pipe","false") }}'),dict(d,issuer_headers={}),dict(d,ca_file=str(root))]:
    put(bad)
    with self.assertRaises(Exception):m.select(str(root),str(receipt),str(p))
   p.write_text(json.dumps(d)[:-1]+',"run":true}');p.chmod(0o600)
   with self.assertRaises(Exception):m.select(str(root),str(receipt),str(p))
   put(d);os.link(root,r/'alias')
   with self.assertRaises(Exception):m.select(str(root),str(receipt),str(p))
 def test_returned_accessor_durability_failure_retains_manual_recovery(self):
  from unittest.mock import patch
  import io
  spec=importlib.util.spec_from_file_location('wid',S/'writer-issuer-state.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
  with tempfile.TemporaryDirectory(prefix='writer-issuer-durable-') as directory:
   p=Path(directory)/'receipt';d={'setup_id':'a'*64};r={'schema':1,'setup_id':d['setup_id'],'selection_sha256':m.digest(d),'stage':'Requesting','requested_at':int(time.time())};m.b.save(str(p),r,first=True);original=p.read_bytes()
   # Isolated custody transition, not a provider call. Persist failure cannot authorize cleanup or remint.
   with patch.object(m,'select',return_value=d),patch.object(m.g,'verify'),patch.object(m,'stdin',return_value={'auth':{'accessor':'CHILD-ACCESSOR'},'root_accessor':'ROOT-ACCESSOR'}),patch.object(m.b,'save',side_effect=OSError('synthetic durability error')),patch('sys.argv',['state','received','root',str(p),'inputs']):
    with self.assertRaises(OSError):m.main()
   self.assertEqual(p.read_bytes(),original);self.assertFalse(Path(m.output(str(p))).exists());self.assertNotIn('accessor',m.read(str(p)))
   with patch.object(m,'select',return_value=d),patch.object(m.g,'verify'),patch('sys.argv',['state','start','root',str(p),'inputs']):
    with self.assertRaises(ValueError):m.main()
   with patch.object(m,'select',return_value=d),patch.object(m.g,'verify'),patch('sys.argv',['state','cleanup-contract','root',str(p),'inputs']):
    with self.assertRaises(ValueError):m.main()
