import datetime as dt,hashlib,json,os,ssl,subprocess,tempfile,threading,unittest
from pathlib import Path
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from urllib.parse import urlsplit
ROOT=Path(__file__).resolve().parents[2]
SCRIPT=ROOT/'configuration/packages/gitlab/enrollment/read-keycloak-context.py'
class Snapshot(unittest.TestCase):
 def test_exact_native_reads_and_fail_closed_receipts(self):
  with tempfile.TemporaryDirectory(prefix='kc-snapshot-') as directory:
   d=Path(directory);subprocess.run(['openssl','req','-x509','-newkey','rsa:2048','-nodes','-days','1','-subj','/CN=localhost','-addext','subjectAltName=DNS:localhost','-keyout',str(d/'key'),'-out',str(d/'ca')],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL);(d/'ca').chmod(0o644)
   roles={'tenant-admin':'admins','tenant-developer':'developers','tenant-viewer':'viewers'};ids={r:f'00000000-0000-4000-8000-{i:012d}' for i,r in enumerate(roles,1)};subjects={r:f'10000000-0000-4000-8000-{i:012d}' for i,r in enumerate(roles,1)}
   state={'calls':0,'members':0,'mode':'good','writes':0}
   class Handler(BaseHTTPRequestHandler):
    def log_message(self,*args):pass
    def respond(self,code,data):self.send_response(code);self.send_header('Content-Type','application/json');self.end_headers();self.wfile.write(json.dumps(data).encode())
    def do_POST(self):state['writes']+=1;self.respond(405,{})
    def do_GET(self):
     state['calls']+=1
     if self.headers.get('Authorization')!='Bearer OFFLINE-DUMMY-TOKEN':return self.respond(403,{})
     path=urlsplit(self.path).path
     role=next((r for r,g in ids.items() if '/groups/'+g in path),None)
     if not role:return self.respond(403,{})
     if state['mode']=='denied':return self.respond(403,{})
     if path.endswith('/members'):
      state['members']+=1
      if state['mode']=='failure':return self.respond(500,{})
      sub=subjects['tenant-admin'] if state['mode']=='conflict' else subjects[role]
      enabled=not(state['mode']=='drift' and state['members']>3)
      return self.respond(200,[{'id':sub,'enabled':enabled,'email':'PRIVATE-EMAIL-MUST-NOT-ESCAPE','username':'PRIVATE-NAME'}])
     return self.respond(200,{'id':ids[role],'path':('/foreign' if state['mode']=='foreign' else '/tenants/portal/'+roles[role]),'subGroupCount':1 if state['mode']=='nested' else 0})
   server=ThreadingHTTPServer(('127.0.0.1',0),Handler);ctx=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER);ctx.load_cert_chain(d/'ca',d/'key');server.socket=ctx.wrap_socket(server.socket,server_side=True);threading.Thread(target=server.serve_forever,daemon=True).start();self.addCleanup(server.server_close);self.addCleanup(server.shutdown)
   token=d/'token';token.write_text('OFFLINE-DUMMY-TOKEN');token.chmod(0o600);receipt=d/'receipt';inputs=d/'inputs.json'
   contract=ROOT/'configuration/authorization/contexts/portal.yaml'
   values={'context':'portal','source_revision':'a'*40,'origin':'https://localhost:'+str(server.server_port)+'/auth','ca_file':str(d/'ca'),'contract_sha256':hashlib.sha256(contract.read_bytes()).hexdigest(),'group_ids':ids}
   def run(mode='--read',extra=None):
    inputs.write_text(json.dumps({**values,**(extra or {})}));inputs.chmod(0o600)
    r=subprocess.run(['python3',str(SCRIPT),mode,str(token),str(receipt),str(inputs)],capture_output=True,text=True,timeout=20)
    self.assertNotIn('OFFLINE-DUMMY-TOKEN',r.stdout+r.stderr);self.assertNotIn('PRIVATE-',r.stdout+r.stderr);return r
   p=subprocess.run(['python3',str(SCRIPT)],capture_output=True,text=True,check=True);self.assertIn('INERT',p.stdout)
   self.assertEqual(run('--validate').returncode,0);self.assertEqual(state['calls'],0);self.assertFalse(receipt.exists())
   self.assertNotEqual(run(extra={'unexpected':'{{lookup("pipe","false")}}'}).returncode,0);self.assertEqual(state['calls'],0)
   self.assertNotEqual(run(extra={'contract_sha256':'0'*64}).returncode,0);self.assertEqual(state['calls'],0)
   r=run();self.assertEqual(r.returncode,0,r.stderr);data=json.loads(receipt.read_text());self.assertEqual(data['stage'],'SnapshotVerified');self.assertEqual(len(data['members']),3);self.assertNotIn('PRIVATE-',receipt.read_text());self.assertEqual(receipt.stat().st_mode&0o777,0o600);self.assertEqual(state['calls'],12)
   before=state['calls'];self.assertNotEqual(run().returncode,0);self.assertEqual(state['calls'],before);receipt.unlink()
   for mode in ['denied','failure','conflict','foreign','nested','drift']:
    state.update(mode=mode,members=0);self.assertNotEqual(run().returncode,0,mode);self.assertFalse(receipt.exists(),mode)
   self.assertEqual(state['writes'],0)
if __name__=='__main__':unittest.main()
