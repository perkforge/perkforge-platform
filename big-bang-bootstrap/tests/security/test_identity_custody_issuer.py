"""Actual local Ansible/synthetic TLS issuer; never real root or native tokens."""
import json,os,ssl,subprocess,tempfile,threading,unittest
from pathlib import Path
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
ROOT=Path(__file__).resolve().parents[2];S=ROOT/'configuration/packages/gitlab/enrollment/setup'
class Issuer(unittest.TestCase):
 def test_fixed_scope_and_uncertainty(self):
  with tempfile.TemporaryDirectory(prefix='issuer-fixture-') as directory:
   r=Path(directory);subprocess.run(['openssl','req','-x509','-newkey','rsa:2048','-nodes','-days','1','-subj','/CN=localhost','-addext','subjectAltName=DNS:localhost','-keyout',str(r/'key'),'-out',str(r/'ca')],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,check=True);(r/'ca').chmod(0o644)
   state={'policies':{},'roles':{},'tokens':{},'writes':[],'mode':'','root_calls':0,'mint':0};cluster='11111111-1111-4111-8111-111111111111';setup='a'*64
   class H(BaseHTTPRequestHandler):
    def log_message(self,*a):pass
    def reply(self,status,data=None):
     self.send_response(status);self.send_header('Content-Type','application/json');self.end_headers()
     if data is not None:self.wfile.write(json.dumps(data).encode())
    def auth(self):
     token=self.headers.get('X-Vault-Token');state['root_calls']+=token=='FAKE-ROOT'
     if token!='FAKE-ROOT':self.reply(403,{});return False
     return True
    def do_GET(self):
     p=self.path
     if p=='/v1/sys/health':return self.reply(200,{'cluster_id':cluster if state['mode']!='cluster' else 'wrong','initialized':True,'sealed':False,'version':'2.7.2'})
     if p=='/v1/auth/token/lookup-self':
      t=self.headers.get('X-Vault-Token')
      if t=='FAKE-ROOT':state['root_calls']+=1;return self.reply(200,{'data':{'policies':['default'] if state['mode']=='nonroot' else ['root'],'accessor':'ROOT-ACCESSOR'}})
      native=next((v for v in state['tokens'].values() if v['token']==t),None)
      return self.reply(200,{'data':native}) if native else self.reply(403,{})
     if not self.auth():return
     if p=='/v1/sys/auth':return self.reply(200,{'data':{'kubernetes-eso/':{'type':'kubernetes','description':'PerkForge eso-machine-v1','config':{'default_lease_ttl':300,'max_lease_ttl':900}}}})
     if p=='/v1/auth/kubernetes-eso/config':return self.reply(200,{'data':{'kubernetes_host':'https://kubernetes.default.svc:443','disable_local_ca_jwt':False}})
     if p.startswith('/v1/sys/policies/acl/'):
      v=state['policies'].get(p.rsplit('/',1)[-1]);return self.reply(404) if v is None else self.reply(200,{'data':{'policy':v}})
     if p.startswith('/v1/auth/kubernetes-eso/role/'):
      v=state['roles'].get(p.rsplit('/',1)[-1]);return self.reply(404) if v is None else self.reply(200,{'data':v})
     self.reply(404,{})
    def do_PUT(self):
     if not self.auth():return
     assert self.path.startswith('/v1/sys/policies/acl/');name=self.path.rsplit('/',1)[-1];body=json.loads(self.rfile.read(int(self.headers['Content-Length'])));assert name not in state['policies'];state['policies'][name]=body['policy'];state['writes'].append('policy:'+name);self.reply(204)
    def do_POST(self):
     if not self.auth():return
     body=json.loads(self.rfile.read(int(self.headers['Content-Length'])));p=self.path
     if p.startswith('/v1/auth/kubernetes-eso/role/'):
      name=p.rsplit('/',1)[-1];assert name not in state['roles'];state['roles'][name]=body;state['writes'].append('role:'+name);return self.reply(204)
     if p=='/v1/auth/token/create':
      assert set(body)=={'policies','no_default_policy','display_name','ttl','explicit_max_ttl','renewable'} and body['ttl']==body['explicit_max_ttl']==3600 and body['renewable'] is False and body['no_default_policy'] is True
      state['mint']+=1;n=str(state['mint']);accessor='ACCESSOR-'+n;token='FAKE-CHILD-'+n
      policy=body['policies'];native={'token':token,'accessor':accessor,'policies':policy,'identity_policies':[],'renewable':False,'ttl':3500,'explicit_max_ttl':3600,'display_name':'token-'+body['display_name']};state['tokens'][accessor]=native;state['writes'].append('mint:'+n)
      if state['mode']=='lost' and state['mint']==2:return self.reply(503,{})
      return self.reply(200,{'auth':{'client_token':token,'accessor':accessor,'policies':policy+(['default'] if state['mode']=='extra' else []),'identity_policies':[],'renewable':False,'lease_duration':3600}})
     if p=='/v1/auth/token/lookup-accessor':
      v=state['tokens'].get(body['accessor']);return self.reply(200,{'data':v}) if v else self.reply(400,{})
     if p=='/v1/auth/token/revoke-accessor':
      assert body['accessor']!='ROOT-ACCESSOR';state['tokens'].pop(body['accessor'],None);state['writes'].append('revoke');return self.reply(204)
     raise AssertionError('unexpected write '+p)
   server=ThreadingHTTPServer(('127.0.0.1',0),H);tls=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER);tls.load_cert_chain(r/'ca',r/'key');server.socket=tls.wrap_socket(server.socket,server_side=True);threading.Thread(target=server.serve_forever,daemon=True).start();self.addCleanup(server.server_close);self.addCleanup(server.shutdown)
   origin='https://localhost:'+str(server.server_port);token=r/'root';token.write_text('FAKE-ROOT');token.chmod(0o600);inputs=r/'inputs';inputs.write_text(json.dumps({'run':True,'scope':'identity-custody-issuer-v1','setup_id':setup,'bao_origin':origin,'ca_file':str(r/'ca'),'cluster_id':cluster}));inputs.chmod(0o600);receipt=r/'receipt'
   def run(mode):
    p=subprocess.run(['bash',str(S/'run-issuer.sh'),mode,str(token),str(receipt),str(inputs)],capture_output=True,text=True,timeout=120,env={**os.environ,'ANSIBLE_LOCAL_TEMP':str(r/'local'),'ANSIBLE_REMOTE_TEMP':str(r/'remote')})
    for secret in ('FAKE-ROOT','FAKE-CHILD','ACCESSOR-'):self.assertNotIn(secret,p.stdout+p.stderr)
    return p
   self.assertEqual(run('--validate').returncode,0);self.assertEqual(run('inert').returncode,0);self.assertEqual(state['writes'],[]);self.assertFalse(receipt.exists())
   state['mode']='cluster';self.assertNotEqual(run('--apply').returncode,0);self.assertEqual(state['root_calls'],0);self.assertEqual(state['writes'],[]);receipt.unlink()
   state['mode']='nonroot';self.assertNotEqual(run('--apply').returncode,0);self.assertEqual(state['writes'],[]);receipt.unlink()
   state['mode']='';state['policies']['eso-identity-reader']='foreign';self.assertNotEqual(run('--apply').returncode,0);self.assertEqual(state['writes'],[]);receipt.unlink();state['policies']={}
   p=run('--apply');self.assertEqual(p.returncode,0,p.stdout+p.stderr);self.assertEqual(len(state['policies']),5);self.assertEqual(len(state['roles']),3);self.assertEqual(state['mint'],2);self.assertEqual(json.loads(receipt.read_text())['stage'],'Issued');before=receipt.read_bytes();self.assertNotEqual(run('--apply').returncode,0);self.assertEqual(receipt.read_bytes(),before)
   p=run('--cleanup');self.assertEqual(p.returncode,0,p.stdout+p.stderr);self.assertFalse(state['tokens']);self.assertEqual(json.loads(receipt.read_text())['stage'],'Cleaned');self.assertEqual(len(state['policies']),5)
   for mode in ('extra','lost'):
    receipt.unlink()
    for name in ('gitlab-setup-token','keycloak-setup-token'):
     if (r/name).exists():(r/name).unlink()
    state.update(mode=mode,tokens={},mint=0,writes=[])
    self.assertNotEqual(run('--apply').returncode,0);self.assertEqual(json.loads(receipt.read_text())['stage'],'ManualRecovery');self.assertNotEqual(run('--apply').returncode,0)
    self.assertEqual(len(state['tokens']),1 if mode=='lost' else 0)
    self.assertTrue(all(x.startswith(('mint:','revoke')) for x in state['writes']))
