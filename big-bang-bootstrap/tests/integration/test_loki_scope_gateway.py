"""Real nginx/TLS with synthetic recording backend; not live Loki isolation proof."""
import base64,copy,json,os,socket,ssl,subprocess,tempfile,threading,time,unittest
from pathlib import Path
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
import urllib.request,urllib.error
import yaml
ROOT=Path(__file__).resolve().parents[2]
SOURCE=ROOT/'configuration/observability/log-boundary'
def freeport():
 with socket.socket() as s:s.bind(('127.0.0.1',0));return s.getsockname()[1]
class Backend(BaseHTTPRequestHandler):
 def do_GET(self):self.reply()
 def do_POST(self):self.reply()
 def reply(self):
  body=self.rfile.read(int(self.headers.get('Content-Length',0))).decode()
  self.server.received.append({'path':self.path,'method':self.command,'tenant':self.headers.get('X-Scope-OrgID'),'auth':self.headers.get('Authorization'),'body':body})
  payload=json.dumps({'status':'success'}).encode();self.send_response(200);self.end_headers();self.wfile.write(payload)
 def log_message(self,*args):pass
class LokiScopeGateway(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.tmp=tempfile.TemporaryDirectory();cls.addClassCleanup(cls.tmp.cleanup);cls.folder=Path(cls.tmp.name)
  cls.cert=cls.folder/'cert.pem';key=cls.folder/'key.pem'
  subprocess.run(['openssl','req','-x509','-newkey','rsa:2048','-nodes','-keyout',str(key),'-out',str(cls.cert),'-days','1','-subj','/CN=localhost','-addext','subjectAltName=DNS:localhost'],check=True,capture_output=True)
  auth=cls.folder/'htpasswd';cls.password='synthetic-only'
  hashed=subprocess.run(['openssl','passwd','-6','-stdin'],input=cls.password,text=True,capture_output=True,check=True).stdout.strip()
  auth.write_text(''.join(u+':'+hashed+'\n' for u in ['writer','platform-reader','portal-reader','other-reader']));auth.chmod(0o600)
  cls.backend=ThreadingHTTPServer(('127.0.0.1',0),Backend);cls.backend.received=[]
  tls=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER);tls.load_cert_chain(cls.cert,key);cls.backend.socket=tls.wrap_socket(cls.backend.socket,server_side=True)
  cls.addClassCleanup(cls.backend.server_close);cls.addClassCleanup(cls.backend.shutdown);threading.Thread(target=cls.backend.serve_forever,daemon=True).start()
  cls.port=freeport();cls.inputs={'log_boundary_render':True,'log_output_dir':str(cls.folder/'out'),'log_runtime_dir':str(cls.folder),'log_listen':f'127.0.0.1:{cls.port}','log_upstream':f'https://127.0.0.1:{cls.backend.server_port}','log_upstream_tls_name':'localhost','log_server_name':'localhost','log_cert_path':str(cls.cert),'log_key_path':str(key),'log_ca_path':str(cls.cert),'log_htpasswd_path':str(auth),'log_writer':'writer','log_platform_reader':'platform-reader','log_fallback_scope':'platform-unassigned-v1','log_scopes':[{'namespace':'tenant-portal','scope_id':'portal-runtime-v1'},{'namespace':'tenant-other','scope_id':'other-runtime-v1'}],'log_readers':[{'username':'portal-reader','scope_ids':['portal-runtime-v1']},{'username':'other-reader','scope_ids':['other-runtime-v1']}],'log_legacy_scopes':['legacy-pilot'],'log_collection_namespaces':['tenant-portal','tenant-other']}
  cls.render(cls.inputs)
  config=cls.folder/'out/nginx.conf';binary=os.environ.get('NGINX_VALIDATE_BIN','/usr/sbin/nginx')
  check=subprocess.run([binary,'-t','-c',str(config)],capture_output=True,text=True)
  if check.returncode:raise AssertionError(check.stderr)
  cls.process=subprocess.Popen([binary,'-c',str(config),'-g','daemon off;'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL);cls.addClassCleanup(cls.stop)
  for _ in range(50):
   try:
    with socket.create_connection(('127.0.0.1',cls.port),timeout=.1):break
   except OSError:time.sleep(.1)
  else:raise AssertionError('nginx did not start')
 @classmethod
 def stop(cls):cls.process.terminate();cls.process.wait(timeout=10)
 @classmethod
 def render(cls,inputs,expected=0):
  inp=cls.folder/'inputs.yaml';inp.write_text(yaml.safe_dump(inputs));r=subprocess.run(['ansible-playbook','-i','localhost,',str(SOURCE/'render.yaml'),'-e','@'+str(inp)],capture_output=True,text=True)
  if expected==0 and r.returncode:raise AssertionError(r.stdout+r.stderr)
  if expected!=0 and not r.returncode:raise AssertionError('unsafe input unexpectedly accepted')
 def request(self,path,user='portal-reader',method='GET',scope=None,password=None,body=None):
  headers={}
  if user:headers['Authorization']='Basic '+base64.b64encode((user+':'+(password or self.password)).encode()).decode()
  if scope is not None:headers['X-Scope-OrgID']=scope
  req=urllib.request.Request(f'https://localhost:{self.port}'+path,data=body,headers=headers,method=method)
  try:
   with urllib.request.urlopen(req,context=ssl.create_default_context(cafile=str(self.cert)),timeout=5) as r:return r.status
  except urllib.error.HTTPError as e:return e.code
 def test_query_identity_overwrites_forged_tenant_header(self):
  for header in ['other-runtime-v1','portal-runtime-v1|other-runtime-v1','','platform-unassigned-v1']:
   self.assertEqual(self.request('/loki/api/v1/query_range?query=%7Bnamespace%3D%22tenant-other%22%7D',scope=header),200)
   self.assertEqual(self.backend.received[-1]['tenant'],'portal-runtime-v1');self.assertIsNone(self.backend.received[-1]['auth'])
 def test_platform_federation_is_fixed_and_includes_legacy_fallback(self):
  self.assertEqual(self.request('/loki/api/v1/query',user='platform-reader',scope='invented'),200)
  self.assertEqual(self.backend.received[-1]['tenant'],'legacy-pilot|other-runtime-v1|platform-unassigned-v1|portal-runtime-v1')
 def test_writer_push_only_registered_single_scope(self):
  self.assertEqual(self.request('/loki/api/v1/push',user='writer',method='POST',scope='portal-runtime-v1',body=b'{}'),200)
  self.assertEqual(self.backend.received[-1]['tenant'],'portal-runtime-v1')
  for scope in ['','unknown','legacy-pilot','portal-runtime-v1|other-runtime-v1']:
   self.assertEqual(self.request('/loki/api/v1/push',user='writer',method='POST',scope=scope),403)
  self.assertEqual(self.request('/loki/api/v1/query',user='writer'),403)
  self.assertEqual(self.request('/loki/api/v1/push',method='POST',scope='portal-runtime-v1'),403)
 def test_endpoints_methods_and_bad_auth_fail_closed(self):
  for path in ['/config','/flush','/loki/api/v1/delete','/loki/api/v1/tail','/loki/api/v1/rules','/api/prom/query','/ui']:
   self.assertEqual(self.request(path,user='platform-reader'),403)
  self.assertEqual(self.request('/loki/api/v1/%71uery'),400)
  self.assertEqual(self.request('/loki/api/v1/query',password='wrong'),401)
  self.assertIn(self.request('/loki/api/v1/query',user=None),[401,403])
  self.assertEqual(self.request('/loki/api/v1/query',method='DELETE'),405)
 def test_scoped_label_and_series_routes(self):
  for path in ['/loki/api/v1/labels','/loki/api/v1/label/namespace/values','/loki/api/v1/series']:
   self.assertEqual(self.request(path),200);self.assertEqual(self.backend.received[-1]['tenant'],'portal-runtime-v1')
 def test_render_rejects_unsafe_membership_and_duplicate_namespaces(self):
  for change in ['fallback','duplicate-namespace','unknown-scope','duplicate-identity','invalid-epoch']:
   x=copy.deepcopy(self.inputs)
   if change=='fallback':x['log_readers'][0]['scope_ids']=['platform-unassigned-v1']
   elif change=='duplicate-namespace':x['log_scopes'][1]['namespace']='tenant-portal'
   elif change=='unknown-scope':x['log_readers'][0]['scope_ids']=['unknown-v1']
   elif change=='duplicate-identity':x['log_readers'][0]['username']='writer'
   else:x['log_scopes'][0]['scope_id']='no-epoch'
   self.render(x,expected=1)
 def test_generated_stages_default_unknown_to_platform_then_exact_namespaces(self):
  s=(self.folder/'out/stages.alloy').read_text();self.assertLess(s.index('platform-unassigned-v1'),s.index('portal-runtime-v1'));self.assertIn('namespace=\\"tenant-portal\\"',s);self.assertNotIn('source =',s)
  v=yaml.safe_load((self.folder/'out/boundary-values.yaml').read_text());self.assertTrue(v['loki']['values']['loki']['querier']['multi_tenant_queries_enabled'])
  self.assertIsNone(v['alloy']['values']['upstream']['podLogsViaKubernetesApi']['labelSelectors']);self.assertIn('REDACTED',v['alloy']['values']['upstream']['podLogsViaKubernetesApi']['extraLogProcessingStages'])
  r=list(yaml.safe_load_all((self.folder/'out/collector-rbac.yaml').read_text()));self.assertEqual(r[0]['rules'],[{'apiGroups':[''],'resources':['pods'],'verbs':['get','list','watch']},{'apiGroups':[''],'resources':['pods/log'],'verbs':['get']}]);self.assertEqual(r[1]['subjects'],[{'kind':'ServiceAccount','name':'alloy-log-reader','namespace':'alloy'}])
 def test_exact_umbrella_preserves_pins_and_renders_scoped_stages(self):
  from fixtures.render_helpers import build,helm,ordered_values,child_values,release_name
  sources=os.environ.get('PREFLIGHT_SOURCES_DIR')
  if not sources:self.skipTest('Exact pinned source fixtures required')
  src=Path(sources);objects=build(ROOT/'clusters/local');parent=next(x for x in objects if x['kind']=='HelmRelease')
  values=ordered_values(objects,parent)+[(ROOT/'configuration/observability/candidate-values.yaml').read_text(),(ROOT/'configuration/observability/integrated-logging/values.yaml').read_text()]
  baseline=helm(src/'bigbang/chart','bigbang','bigbang',values,('--set','monitoring.enabled=true','--set','grafana.enabled=true'))
  scoped=helm(src/'bigbang/chart','bigbang','bigbang',values+[(self.folder/'out/boundary-values.yaml').read_text()],('--set','monitoring.enabled=true','--set','grafana.enabled=true'))
  for name in ['loki','alloy']:
   hr=next(x for x in scoped if x['kind']=='HelmRelease' and x['metadata']['name']==name)
   def render(outer):return helm(src/name/'chart',release_name(hr),hr['spec']['targetNamespace'],child_values(outer,name),('--include-crds',))
   old,new=render(baseline),render(scoped)
   def pods(items):return {x['metadata']['name']:x['spec']['template']['spec'] for x in items if x['kind'] in ['Deployment','StatefulSet']}
   for key,pod in pods(new).items():
    prior=pods(old)[key]
    for field in ['imagePullSecrets','securityContext','nodeSelector','serviceAccountName']:self.assertEqual(pod.get(field),prior.get(field))
    for container,previous in zip(pod['containers'],prior['containers']):
     for field in ['image','resources','securityContext']:self.assertEqual(container.get(field),previous.get(field))
   if name=='loki':
    nginx=next(x['data']['nginx.conf'] for x in new if x['kind']=='ConfigMap' and 'nginx.conf' in x.get('data',{}))
    self.assertIn('proxy_set_header X-Scope-OrgID $read_scope',nginx)
    self.assertIn('portal-runtime-v1',nginx)
    self.assertNotIn('loki-gateway-auth-v2',str(pods(new)))
   else:
    cr=next(x for x in new if x['kind']=='Alloy');prior=next(x for x in old if x['kind']=='Alloy')
    for field in ['global','configReloader','controller']:self.assertEqual(cr['spec'][field],prior['spec'][field])
    configs='\n'.join(str(x.get('data',{})) for x in new if x['kind']=='ConfigMap')+str(cr)
    self.assertIn('portal-runtime-v1',configs);self.assertIn('platform-unassigned-v1',configs)
    self.assertIn('REDACTED',configs);self.assertNotIn('observability.perkforge.io/logs',configs)
    self.assertIn('__meta_kubernetes_namespace',configs)
    # Evaluate relevant native relabel rules in their actual rendered order.
    import re
    content=next(value for obj in new if obj['kind']=='ConfigMap' for value in obj.get('data',{}).values() if 'discovery.relabel "filtered_pods"' in value)
    discovery=content.split('discovery.relabel "filtered_pods" {',1)[1].split('} // discovery.relabel "filtered_pods"',1)[0]
    annotation=discovery.index('regex = "__meta_kubernetes_pod_annotation_resource_opentelemetry_io_(.+)"')
    final_reset=discovery.rindex('source_labels = ["__meta_kubernetes_namespace"]')
    self.assertGreater(final_reset,annotation)
    labels={'__meta_kubernetes_namespace':'tenant-other','__meta_kubernetes_pod_name':'real-pod','__meta_kubernetes_pod_container_name':'real-container','__meta_kubernetes_pod_annotation_resource_opentelemetry_io_namespace':'tenant-portal'}
    for rule in re.findall(r'\brule\s*\{([^{}]*)\}',discovery,re.S):
     if 'action = "labelmap"' in rule and 'resource_opentelemetry' in rule:
      for key,value in list(labels.items()):
       prefix='__meta_kubernetes_pod_annotation_resource_opentelemetry_io_'
       if key.startswith(prefix):labels[key[len(prefix):]]=value
     elif 'target_label = "namespace"' in rule and '"__meta_kubernetes_namespace"' in rule:
      labels['namespace']=labels['__meta_kubernetes_namespace']
    self.assertEqual(labels['namespace'],'tenant-other')

 def test_existing_output_is_not_replaced(self):
  self.render(copy.deepcopy(self.inputs),expected=1)
 def test_cluster_collection_requires_explicit_all_flag(self):
  x=copy.deepcopy(self.inputs);x['log_collection_namespaces']=[]
  self.render(x,expected=1)
