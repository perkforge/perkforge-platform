"""Native libpq TLS on loopback, not GitLab/CNG or a real database acceptance."""
import ctypes,ctypes.util,os,shutil,socket,ssl,struct,subprocess,tempfile,threading,unittest
from pathlib import Path
class LibpqTLS(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  library=os.environ.get('GITLAB_LIBPQ_TEST_LIBRARY') or ctypes.util.find_library('pq')
  if not library or not shutil.which('openssl'):raise unittest.SkipTest('native libpq/OpenSSL unavailable; run explicit TLS fixture before activation')
  cls.lib=ctypes.CDLL(library);cls.lib.PQconnectdb.argtypes=[ctypes.c_char_p];cls.lib.PQconnectdb.restype=ctypes.c_void_p;cls.lib.PQerrorMessage.argtypes=[ctypes.c_void_p];cls.lib.PQerrorMessage.restype=ctypes.c_char_p;cls.lib.PQfinish.argtypes=[ctypes.c_void_p]
  cls.tmp=tempfile.TemporaryDirectory(prefix='gitlab-libpq-tls-');cls.root=Path(cls.tmp.name)
  def openssl(*args):subprocess.run(['openssl',*args],cwd=cls.root,check=True,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,timeout=15)
  for name in ('ca','other'):
   openssl('req','-x509','-newkey','rsa:2048','-nodes','-keyout',name+'.key','-out',name+'.crt','-days','1','-subj','/CN=Offline '+name)
  openssl('req','-newkey','rsa:2048','-nodes','-keyout','server.key','-out','server.csr','-subj','/CN=postgres.fixture.invalid')
  (cls.root/'extensions').write_text('subjectAltName=DNS:postgres.fixture.invalid\nextendedKeyUsage=serverAuth\n')
  openssl('x509','-req','-in','server.csr','-CA','ca.crt','-CAkey','ca.key','-CAcreateserial','-out','server.crt','-days','1','-extfile','extensions')
 @classmethod
 def tearDownClass(cls):cls.tmp.cleanup()
 def connect(self,host='postgres.fixture.invalid',root='ca.crt',explicit=None,server_tls=True):
  context=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER);context.load_cert_chain(self.root/'server.crt',self.root/'server.key')
  server=socket.socket();server.bind(('127.0.0.1',0));server.listen(1);server.settimeout(5);port=server.getsockname()[1]
  def serve():
   try:
    with server:
     raw,_=server.accept();raw.settimeout(5)
     with raw:
      self.assertEqual(raw.recv(8),struct.pack('!II',8,80877103));raw.sendall(b'S' if server_tls else b'N')
      if not server_tls:return
      with context.wrap_socket(raw,server_side=True) as peer:
       peer.recv(8192);body=b'SFATAL\x00C28000\x00Moffline fixture TLS reached\x00\x00';peer.sendall(b'E'+struct.pack('!I',len(body)+4)+body)
   except (ssl.SSLError,OSError):pass
  thread=threading.Thread(target=serve,daemon=True);thread.start()
  old={k:os.environ.get(k) for k in ('PGSSLMODE','PGSSLROOTCERT')}
  try:
   os.environ['PGSSLMODE']='verify-full';os.environ['PGSSLROOTCERT']=str(self.root/root)
   args=f'host={host} hostaddr=127.0.0.1 port={port} dbname=fixture user=fixture password=fixture connect_timeout=3 gssencmode=disable'
   if explicit:args+=' sslmode='+explicit
   conn=self.lib.PQconnectdb(args.encode())
   try:return self.lib.PQerrorMessage(conn).decode()
   finally:self.lib.PQfinish(conn)
  finally:
   for key,value in old.items():
    if value is None:os.environ.pop(key,None)
    else:os.environ[key]=value
   thread.join(6)
   self.assertFalse(thread.is_alive(),'loopback fixture did not terminate')
 def test_environment_mode_accepts_matching_hostname_and_ca(self):self.assertIn('offline fixture TLS reached',self.connect())
 def test_environment_mode_rejects_wrong_hostname_same_ca(self):
  error=self.connect(host='other.fixture.invalid');self.assertNotIn('offline fixture TLS reached',error);self.assertIn('does not match host name',error)
 def test_environment_mode_rejects_wrong_or_missing_ca(self):
  for root in ('other.crt','missing.crt'):
   error=self.connect(root=root);self.assertNotIn('offline fixture TLS reached',error);self.assertTrue('certificate verify failed' in error or 'does not exist' in error,error)
 def test_environment_mode_refuses_plaintext_fallback(self):
  error=self.connect(server_tls=False);self.assertNotIn('offline fixture TLS reached',error);self.assertIn('does not support SSL',error)
 def test_explicit_ca_only_overrides_environment_demonstrating_guard_need(self):
  self.assertIn('offline fixture TLS reached',self.connect(host='other.fixture.invalid',explicit='verify-ca'))
