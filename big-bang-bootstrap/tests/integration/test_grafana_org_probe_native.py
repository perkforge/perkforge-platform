import sys,importlib.util,tempfile,pathlib,subprocess,time,urllib.request,urllib.error,json,base64,threading,http.server,socket,hashlib,yaml
import os, unittest

class NativeProbe(unittest.TestCase):
 def test_native_machine_org_denials_and_cleanup(self):
  if not os.environ.get("GRAFANA_VALIDATE_BIN"): self.skipTest("Set checksum-pinned GRAFANA_VALIDATE_BIN; no download")
  root=pathlib.Path(__file__).resolve().parents[2]
  spec=importlib.util.spec_from_file_location('p',root/'tests/runtime/grafana_org_probe.py');p=importlib.util.module_from_spec(spec);spec.loader.exec_module(p)
  binary=pathlib.Path(os.environ['GRAFANA_VALIDATE_BIN'])
  pins=yaml.safe_load((root/'configuration/observability/tenant-query/sources.yaml').read_text());assert hashlib.sha256(binary.read_bytes()).hexdigest()==pins['grafana']['linux_amd64_binary_sha256']
  class H(http.server.BaseHTTPRequestHandler):
   def log_message(self,*a):pass
   def do_GET(self):
    self.send_response(200);self.send_header('Content-Type','application/json');self.end_headers();self.wfile.write(json.dumps({'status':'success','data':{'resultType':'streams','result':[{'stream':{'namespace':'fixture'},'values':[['1','benign']]}]}}).encode())
  server=http.server.ThreadingHTTPServer(('127.0.0.1',0),H);threading.Thread(target=server.serve_forever,daemon=True).start()
  with socket.socket() as s:s.bind(('127.0.0.1',0));port=s.getsockname()[1]
  with tempfile.TemporaryDirectory() as d:
   f=pathlib.Path(d);base=f'http://127.0.0.1:{port}'
   (f/'grafana.ini').write_text(f'[server]\nhttp_addr=127.0.0.1\nhttp_port={port}\n[paths]\ndata={d}/data\nlogs={d}/logs\nplugins={d}/plugins\nprovisioning={d}/provisioning\n[security]\nadmin_user=fixture\nadmin_password=synthetic\n[analytics]\nreporting_enabled=false\ncheck_for_updates=false\ncheck_for_plugin_updates=false\n[plugins]\npreinstall_disabled=true\n')
   with (f/'log').open('w') as log:
    proc=subprocess.Popen([str(binary),'server','--homepath',str(binary.parents[1]),'--config',str(f/'grafana.ini')],stdout=log,stderr=log)
    try:
     for _ in range(200):
      try:urllib.request.urlopen(base+'/api/health',timeout=1).close();break
      except OSError:time.sleep(.1)
     def api(method,path,headers,body):
      h={'Authorization':'Basic '+base64.b64encode(b'fixture:synthetic').decode(),'Content-Type':'application/json'}|headers
      try:
       with urllib.request.urlopen(urllib.request.Request(base+path,headers=h,data=None if body is None else json.dumps(body).encode(),method=method),timeout=10) as r:return r.status,json.load(r)
      except urllib.error.HTTPError as e:
       try:body=json.load(e)
       except:body={}
       # Never emit response bodies; this fixture uses synthetic data only.
       return e.code,body
     assert api('POST','/api/orgs',{}, {'name':'Tenant'})[0]==200
     for org,uid in [(1,'platform'),(2,'own')]:
      assert api('POST','/api/datasources',{'X-Grafana-Org-Id':str(org)},{'uid':uid,'name':uid,'type':'loki','access':'proxy','url':f'http://127.0.0.1:{server.server_port}'})[0]==200
     assert p.verify(api,lambda r:None,approved=True,org_id=2,org_name='Tenant',own_uid='own',foreign_uids=['platform'],marker='benign',query='/loki/api/v1/query_range?limit=5')['cleaned']
    finally:proc.terminate();proc.wait(timeout=15);server.shutdown();server.server_close()
