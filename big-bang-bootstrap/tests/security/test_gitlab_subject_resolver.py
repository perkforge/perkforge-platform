"""Real TLS protocol fixture, no live GitLab or credentials."""
import copy,json,os,ssl,subprocess,tempfile,threading,unittest
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs,urlsplit
ROOT=Path(__file__).resolve().parents[2]
SCRIPT=ROOT/'configuration/packages/gitlab/enrollment/resolve-subject.py'
SUBJECT='01234567-0123-4567-89ab-0123456789ab'
TOKEN='SYNTHETIC-READER.example_01-02'
class Resolver(unittest.TestCase):
 def test_native_tls_and_fail_closed_receipts(self):
  with tempfile.TemporaryDirectory() as directory:
   d=Path(directory);d.chmod(0o700)
   subprocess.run(['openssl','req','-x509','-newkey','rsa:2048','-nodes','-days','1','-subj','/CN=localhost','-addext','subjectAltName=DNS:localhost','-keyout',str(d/'key'),'-out',str(d/'ca')],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
   (d/'ca').chmod(0o644)
   user={'id':41,'state':'active','is_admin':False,'identities':[{'provider':'openid_connect','extern_uid':SUBJECT}],'email':'must-not-copy@example.invalid'}
   authority={'active':True,'revoked':False,'scopes':['read_api'],'expires_at':'2099-01-01'}
   state={'users':[user],'authority':authority,'calls':[]}
   class Handler(BaseHTTPRequestHandler):
    def log_message(self,*args):pass
    def do_GET(self):
     state['calls'].append(self.path)
     assert self.headers['PRIVATE-TOKEN']==state.get('expected_token',TOKEN)
     if state.get('redirect'):
      self.send_response(302);self.send_header('Location','/forbidden');self.end_headers();return
     parsed=urlsplit(self.path)
     if parsed.path=='/api/v4/personal_access_tokens/self':body=state['authority']
     else:
      assert parsed.path=='/api/v4/users'
      assert parse_qs(parsed.query)=={'provider':['openid_connect'],'extern_uid':[SUBJECT],'per_page':['2']}
      body=state['users']
     self.send_response(200)
     if state.get('paginate'):self.send_header('X-Next-Page','2')
     self.end_headers();self.wfile.write(json.dumps(body).encode())
    def do_POST(self):raise AssertionError('No native writes')
    do_PUT=do_DELETE=do_PATCH=do_POST
   server=ThreadingHTTPServer(('127.0.0.1',0),Handler);ctx=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER);ctx.load_cert_chain(d/'ca',d/'key');server.socket=ctx.wrap_socket(server.socket,server_side=True)
   threading.Thread(target=server.serve_forever,daemon=True).start();self.addCleanup(server.server_close);self.addCleanup(server.shutdown)
   token=d/'token';token.write_text(TOKEN);token.chmod(0o600)
   receipt=d/'receipt';vf=d/'inputs.json'
   base={'context':'example','subject':SUBJECT,'source_revision':'a'*40,'origin':f'https://localhost:{server.server_port}','ca_file':str(d/'ca')}
   def run(values=None,mode='--verify',raw=None):
    state['calls']=[];vf.write_text(raw if raw is not None else json.dumps(base | (values or {})));vf.chmod(0o600)
    command=['python3',str(SCRIPT)]+([mode,str(token),str(receipt),str(vf)] if mode else [])
    p=subprocess.run(command,capture_output=True,text=True,timeout=20,env=os.environ|{'PYTHONDONTWRITEBYTECODE':'1','HTTPS_PROXY':'http://127.0.0.1:1'})
    self.assertNotIn('SYNTHETIC-READER',p.stdout+p.stderr);self.assertNotIn('must-not-copy',p.stdout+p.stderr)
    return p
   for mode in ['', '--validate']:
    p=run(mode=mode);self.assertEqual(p.returncode,0,p.stderr);self.assertEqual(state['calls'],[]);self.assertFalse(receipt.exists())
   # Both supported dot-bearing native encoding and legacy plain encoding traverse TLS.
   state['expected_token']='SYNTHETIC-READER';token.write_text(state['expected_token']);p=run();self.assertEqual(p.returncode,0,p.stderr);receipt.unlink();state.pop('expected_token');token.write_text(TOKEN)
   # Reject malformed/bounded inputs before authentication, preserving no successful receipt.
   for bad in ['short', 'x'*4097, 'SYNTHETIC READER', 'SYNTHETIC\nREADER', 'SYNTHETIC\rREADER', 'SYNTHETIC\tREADER', 'SYNTHETIC\x00READER', 'SYNTHETIC/READER', 'SYNTHETIC:READER', 'SYNTHETICéREADER']:
    token.write_text(bad);p=run();self.assertNotEqual(p.returncode,0);self.assertEqual(state['calls'],[]);self.assertFalse(receipt.exists())
   token.write_text(TOKEN)
   for users,expected in [([], 'PendingFirstLogin'),([user|{'state':'blocked'}],'PendingAccountApproval'),([user|{'state':'blocked_pending_approval'}],'PendingAccountApproval'),([user],'IdentityVerified')]:
    state['users']=users;p=run();self.assertEqual(p.returncode,0,p.stderr);result=json.loads(receipt.read_text());self.assertEqual(result['stage'],expected);self.assertEqual(result['subject'],SUBJECT);self.assertEqual(result.get('native_user_id'),41 if expected=='IdentityVerified' else None);self.assertNotIn('email',result)
    old=receipt.read_bytes();p=run();self.assertNotEqual(p.returncode,0);self.assertEqual(state['calls'],[]);self.assertEqual(receipt.read_bytes(),old);receipt.unlink()
   for users in [[user,user],[user|{'is_admin':True}],[user|{'identities':[]}],[user|{'identities':user['identities']*2}],[user|{'identities':[{'provider':'openid_connect','extern_uid':'foreign'}]}],[user|{'state':'deactivated'}],[user|{'id':True}]]:
    state['users']=users;p=run();self.assertNotEqual(p.returncode,0);self.assertFalse(receipt.exists())
   state['users']=[user]
   for extra in [{'scopes':['api']},{'scopes':['read_api','api']},{'active':False},{'revoked':True},{'expires_at':None},{'expires_at':'2000-01-01'}]:
    state['authority']=authority|extra;p=run();self.assertNotEqual(p.returncode,0);self.assertEqual(len(state['calls']),1);self.assertFalse(receipt.exists())
   state['authority']=authority|{'scopes':['read_api','self_rotate']};p=run();self.assertEqual(p.returncode,0,p.stderr);receipt.unlink();state['authority']=authority
   for flag in ['redirect','paginate']:
    state[flag]=True;p=run();self.assertNotEqual(p.returncode,0);self.assertEqual(len(state['calls']),1);self.assertFalse(receipt.exists());state.pop(flag)
   state['users']=['x'*70000];p=run();self.assertNotEqual(p.returncode,0);self.assertFalse(receipt.exists());state['users']=[user]
   marker=d/'must-not-execute'
   for key in base:
    p=run({key:"{{ lookup('pipe', 'touch "+str(marker)+"') }}"});self.assertNotEqual(p.returncode,0);self.assertEqual(state['calls'],[]);self.assertFalse(marker.exists())
   for extra in [{'extra':'forbidden'},{'subject':SUBJECT.upper()},{'context':'platform'},{'source_revision':True}]:
    p=run(extra);self.assertNotEqual(p.returncode,0);self.assertEqual(state['calls'],[])
   p=run(raw='{"context":"a","context":"b"}');self.assertNotEqual(p.returncode,0);self.assertEqual(state['calls'],[])
   token.chmod(0o644);p=run();self.assertNotEqual(p.returncode,0);self.assertEqual(state['calls'],[]);token.chmod(0o600)
   receipt.symlink_to(token);p=run();self.assertNotEqual(p.returncode,0);self.assertEqual(state['calls'],[]);self.assertTrue(receipt.is_symlink());receipt.unlink()
   os.mkfifo(receipt,0o600);p=run();self.assertNotEqual(p.returncode,0);self.assertEqual(state['calls'],[]);receipt.unlink()
