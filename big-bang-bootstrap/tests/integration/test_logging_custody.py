"""Offline exact-record custody rendering; never loads credentials or calls APIs."""
from pathlib import Path
import json,subprocess,tempfile,unittest,yaml
ROOT=Path(__file__).resolve().parents[2]
PLAY=ROOT/'configuration/observability/log-boundary/custody.yaml'
class LoggingCustody(unittest.TestCase):
 def test_exact_consumers_no_secret_creation_authority(self):
  with tempfile.TemporaryDirectory() as t:
   p=Path(t);out=p/'out';inputs=p/'inputs.yaml'
   inputs.write_text(yaml.safe_dump({'logging_custody_render':True,'logging_custody_output':str(out),'logging_bao_server':'https://bao.example.invalid','logging_public_ca':'-----BEGIN CERTIFICATE-----\nsynthetic-public-fixture\n-----END CERTIFICATE-----'}))
   r=subprocess.run(['ansible-playbook','-i','localhost,',str(PLAY),'-e','@'+str(inputs)],capture_output=True,text=True)
   self.assertEqual(r.returncode,0,r.stdout+r.stderr)
   pre=[x for x in yaml.safe_load_all((out/'prerequisites.yaml').read_text()) if x]
   consumers=[x for x in yaml.safe_load_all((out/'consumers.yaml').read_text()) if x]
   expected={('logging','loki-boundary-auth-v1'),('alloy','loki-boundary-collector-v1'),('monitoring','loki-boundary-query-platform-v1'),('monitoring','loki-boundary-query-portal-v1')}
   secrets=[x for x in pre if x['kind']=='Secret'];self.assertEqual({(x['metadata']['namespace'],x['metadata']['name']) for x in secrets},expected)
   self.assertTrue(all(x['data']=={} for x in secrets));self.assertFalse(any(x['kind'].startswith('Cluster') for x in pre))
   for role in [x for x in pre if x['kind']=='Role']:
    for rule in role['rules']:
     self.assertEqual(len(rule['resourceNames']),1)
     if rule['resources']==['secrets']:
      if role['metadata']['name']=='alloy-scoped-client-secret-reader':
       self.assertEqual(rule['verbs'],['get','watch']);self.assertEqual(rule['resourceNames'],['loki-boundary-collector-v1']);self.assertEqual(role['metadata']['namespace'],'alloy')
      else:self.assertEqual(rule['verbs'],['get','update','patch'])
   binding=next(x for x in pre if x['kind']=='RoleBinding' and x['metadata']['name']=='alloy-scoped-client-secret-reader');self.assertEqual(binding['subjects'],[{'kind':'ServiceAccount','name':'alloy-log-reader','namespace':'alloy'}])
   external=[x for x in consumers if x['kind']=='ExternalSecret'];self.assertEqual(len(external),4)
   for obj in external:
    self.assertEqual(obj['spec']['target']['creationPolicy'],'Merge');self.assertEqual(obj['spec']['target']['deletionPolicy'],'Retain')
    self.assertEqual(len({x['remoteRef']['key'] for x in obj['spec']['data']}),1)
   for role in out.glob('*.json'):
    value=json.loads(role.read_text());self.assertTrue(value['token_no_default_policy']);self.assertEqual(len(value['bound_service_account_names']),1);self.assertEqual(len(value['bound_service_account_namespaces']),1)
   for policy in out.glob('*.hcl'):
    text=policy.read_text();self.assertNotIn('*',text);self.assertNotIn('write',text);self.assertEqual(text.count('platform/data/logging/boundary/'),1)
 def test_default_and_check_mode_are_inert(self):
  for extra in [[],['--check','-e','logging_custody_render=true']]:
   result=subprocess.run(['ansible-playbook','-i','localhost,',str(PLAY)]+extra,capture_output=True,text=True)
   self.assertEqual(result.returncode,0,result.stdout+result.stderr)
 def test_seed_partial_retry_and_conflict_over_verified_tls(self):
  import ssl,threading
  from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
  class Bao(BaseHTTPRequestHandler):
   def log_message(self,*args):pass
   def reply(self,status,data):
    self.send_response(status);self.send_header('Content-Type','application/json');self.end_headers();self.wfile.write(json.dumps(data).encode())
   def do_GET(self):
    if self.path=='/v1/sys/health':return self.reply(200,{'cluster_id':'synthetic-cluster','sealed':False})
    if self.headers.get('X-Vault-Token')!='synthetic-only':return self.reply(403,{})
    self.server.reads+=1
    if self.path in self.server.records:return self.reply(200,{'data':{'data':self.server.records[self.path]}})
    self.reply(404,{})
   def do_POST(self):
    if self.headers.get('X-Vault-Token')!='synthetic-only':return self.reply(403,{})
    body=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
    if body['options']['cas']!=0 or self.path in self.server.records:return self.reply(400,{})
    self.server.records[self.path]=body['data'];self.server.writes+=1;self.reply(200,{'data':{'version':1}})
  with tempfile.TemporaryDirectory() as t:
   p=Path(t);cert=p/'ca.pem';key=p/'ca.key';token=p/'token';token.write_text('synthetic-only');token.chmod(0o600)
   subprocess.run(['openssl','req','-x509','-newkey','rsa:2048','-nodes','-keyout',str(key),'-out',str(cert),'-days','1','-subj','/CN=localhost','-addext','subjectAltName=DNS:localhost'],check=True,capture_output=True)
   server=ThreadingHTTPServer(('127.0.0.1',0),Bao);server.records={};server.writes=0;server.reads=0
   tls=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER);tls.load_cert_chain(cert,key);server.socket=tls.wrap_socket(server.socket,server_side=True)
   thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
   try:
    inputs=p/'inputs.yaml';inputs.write_text(yaml.safe_dump({'logging_seed_apply':True,'logging_private_dir':str(p/'private'),'logging_bao_server':f'https://localhost:{server.server_port}','logging_bao_ca_file':str(cert),'logging_bao_cluster_id':'synthetic-cluster','logging_bao_token_file':str(token)}))
    def run():return subprocess.run(['ansible-playbook','-i','localhost,',str(PLAY.parent/'seed.yaml'),'-e','@'+str(inputs)],capture_output=True,text=True)
    first=run();self.assertEqual(first.returncode,0,first.stdout+first.stderr);self.assertEqual(server.writes,4)
    before=json.loads(json.dumps(server.records));second=run();self.assertEqual(second.returncode,0,second.stdout+second.stderr);self.assertEqual(server.writes,4);self.assertEqual(server.records,before)
    # A partial remote write retry reuses the same local generated bundle.
    del server.records['/v1/platform/data/logging/boundary/query-portal-v1']
    third=run();self.assertEqual(third.returncode,0,third.stdout+third.stderr);self.assertEqual(server.records,before);self.assertEqual(server.writes,5)
    saved=json.loads((p/'private/records.json').read_text());baseline_reads=server.reads
    legacy=p/'legacy';legacy.write_text('platform-pilot:$6$synthetic$unchanged\n')
    settings=yaml.safe_load(inputs.read_text());settings['logging_legacy_htpasswd_file']=str(legacy);inputs.write_text(yaml.safe_dump(settings))
    mismatch=run();self.assertNotEqual(mismatch.returncode,0);self.assertEqual(server.reads,baseline_reads);self.assertEqual(server.writes,5)
    settings.pop('logging_legacy_htpasswd_file');inputs.write_text(yaml.safe_dump(settings))
    malformed=json.loads(json.dumps(saved));malformed['collector-v1']['tenantId']='foreign-scope';(p/'private/records.json').write_text(json.dumps(malformed))
    rejected=run();self.assertNotEqual(rejected.returncode,0);self.assertEqual(server.reads,baseline_reads)
    (p/'private/records.json').write_text(json.dumps(saved))
    server.records['/v1/platform/data/logging/boundary/collector-v1']['password']='foreign-conflict'
    conflict=run();self.assertNotEqual(conflict.returncode,0);self.assertEqual(server.writes,5)
    # A first-time bundle with a supplied legacy line preserves it byte-for-byte.
    server.records={};server.writes=0
    settings['logging_private_dir']=str(p/'private-with-legacy');settings['logging_legacy_htpasswd_file']=str(legacy);inputs.write_text(yaml.safe_dump(settings))
    with_legacy=run();self.assertEqual(with_legacy.returncode,0,with_legacy.stdout+with_legacy.stderr)
    self.assertTrue(server.records['/v1/platform/data/logging/boundary/gateway-v1']['.htpasswd'].endswith(legacy.read_text()))
   finally:server.shutdown();server.server_close();thread.join()
