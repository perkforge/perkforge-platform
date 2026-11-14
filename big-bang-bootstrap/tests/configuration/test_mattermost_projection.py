"""Pure event minimization tests using Node; pinned njs runtime is a separate gate."""
import pathlib,subprocess,json,tempfile,unittest
ROOT=pathlib.Path(__file__).resolve().parents[3]
class Projection(unittest.TestCase):
 def test_projection_and_denials(self):
  source=(ROOT/'big-bang-bootstrap/configuration/observability/mattermost-projection/project.js').read_text()
  script=source.replace("import fs from 'fs';", "import fs from 'node:fs';").replace("import crypto from 'crypto';", "import crypto from 'node:crypto';")
  script+='''
const route={sources:['tenant-portal-config/portal'],title:'Portal deployments',link:'https://portal.example.invalid'};
const event={involvedObject:{kind:'HelmRelease',apiVersion:'helm.toolkit.fluxcd.io/v2',namespace:'tenant-portal-config',name:'portal'},message:'Helm upgrade succeeded for release evil\\nsecret=DO-NOT-FORWARD',severity:'info',metadata:{url:'https://evil.invalid',token:'DO-NOT-FORWARD'}};
const out=JSON.stringify(project(event,route));if(out.includes('DO-NOT-FORWARD')||out.includes('evil'))throw Error('leak');
for(const bad of [{...event,severity:'error'},{...event,message:'periodic reconcile'},{...event,involvedObject:{...event.involvedObject,namespace:'foreign'}},{...event,involvedObject:{...event.involvedObject,kind:'Kustomization'}}]) {let denied=false;try{project(bad,route)}catch(e){denied=true}if(!denied)throw Error('not denied');}
console.log('projection and denials passed');
'''
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d)/'test.mjs';p.write_text(script);r=subprocess.run(['node',str(p)],capture_output=True,text=True);self.assertEqual(r.returncode,0,r.stderr)

class NativeNjs(unittest.TestCase):
 def test_pinned_runtime_transport_and_denials(self):
  import ssl,socket,threading,urllib.request,urllib.error,time
  from http.server import HTTPServer,BaseHTTPRequestHandler
  source=ROOT/'big-bang-bootstrap/configuration/observability/mattermost-projection'
  image='docker.io/library/nginx:1.31.6-alpine@sha256:0530961ff0592b58c10f767535cc0abdfccf9e389ff7cc90f87320c1bc7e8506'
  with tempfile.TemporaryDirectory() as d:
   d=pathlib.Path(d);d.chmod(0o755)
   subprocess.run(['openssl','req','-x509','-newkey','rsa:2048','-nodes','-days','1','-subj','/CN=localhost','-addext','subjectAltName=DNS:localhost','-keyout',str(d/'tls.key'),'-out',str(d/'tls.crt')],check=True,capture_output=True)
   (d/'tls.key').chmod(0o644);(d/'ca.crt').write_bytes((d/'tls.crt').read_bytes());(d/'resolver.conf').write_text('resolver 127.0.0.1;\n')
   received=[]; response_status=[200]
   class Handler(BaseHTTPRequestHandler):
    def log_message(self,*a):pass
    def do_POST(self):
     received.append(json.loads(self.rfile.read(int(self.headers['Content-Length']))));self.send_response(response_status[0]);self.end_headers();self.wfile.write(b'ok')
   srv=HTTPServer(('127.0.0.1',0),Handler);ctx=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER);ctx.load_cert_chain(d/'tls.crt',d/'tls.key');srv.socket=ctx.wrap_socket(srv.socket,server_side=True);threading.Thread(target=srv.serve_forever,daemon=True).start()
   with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
   route={'sources':['tenant-portal-config/portal'],'title':'Portal deployments','link':'https://portal.example.invalid','token':'fixture-token','hook':f'https://localhost:{srv.server_port}/hooks/'+('h'*26)}
   (d/'routes.json').write_text(json.dumps({'/portal':route}));(d/'nginx.conf').write_text((source/'nginx.conf').read_text().replace('listen 8443 ssl;',f'listen {port} ssl;'))
   cmd=['podman','run','--rm','--network','host','--read-only','--user','101:101','--cap-drop=all','--security-opt=no-new-privileges','--tmpfs','/tmp:rw,size=16m','-v',f'{source}:/etc/projection:ro','-v',f'{d}/nginx.conf:/etc/nginx/nginx.conf:ro']
   for target in ['projection','projection-tls','projection-ca','projection-dns']:cmd+=['-v',f'{d}:/run/{target}:ro']
   p=subprocess.Popen(cmd+[image,'nginx','-g','daemon off;'],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
   try:
    opener=urllib.request.build_opener(urllib.request.HTTPSHandler(context=ssl.create_default_context(cafile=d/'tls.crt')),urllib.request.ProxyHandler({}))
    for _ in range(60):
     try:
      with opener.open(f'https://localhost:{port}/healthz',timeout=1) as r:break
     except Exception:
      if p.poll() is not None: raise RuntimeError(p.stderr.read().decode())
      time.sleep(.1)
    event={'involvedObject':{'kind':'HelmRelease','apiVersion':'helm.toolkit.fluxcd.io/v2','namespace':'tenant-portal-config','name':'portal'},'message':'Helm upgrade succeeded for release X\nDO-NOT-FORWARD','severity':'info','metadata':{'secret':'DO-NOT-FORWARD'}}
    def send(path,token,body):
     try:
      with opener.open(urllib.request.Request(f'https://localhost:{port}'+path,data=json.dumps(body).encode(),headers={'Authorization':'Bearer '+token,'Content-Type':'application/json'}),timeout=12) as r:return r.status
     except urllib.error.HTTPError as e:return e.code
    self.assertEqual(send('/portal','fixture-token',event),200)
    self.assertEqual(send('/portal','wrong',event),403);self.assertEqual(send('/portal?override=1','fixture-token',event),403)
    event['involvedObject']['namespace']='foreign';self.assertEqual(send('/portal','fixture-token',event),400)
    self.assertEqual(len(received),1);self.assertNotIn('DO-NOT-FORWARD',json.dumps(received));self.assertEqual(list(received[0]),['text'])
    event['involvedObject']['namespace']='tenant-portal-config'
    response_status[0]=500;self.assertEqual(send('/portal','fixture-token',event),502)
    self.assertEqual(len(received),2)
    # IP URL fails the DNS-only certificate SAN; verify=true must fail closed.
    route['hook']=route['hook'].replace('localhost','127.0.0.1')
    (d/'routes.json').write_text(json.dumps({'/portal':route}))
    self.assertEqual(send('/portal','fixture-token',event),400)
    self.assertEqual(len(received),2)

   finally:
    p.terminate();out,err=p.communicate(timeout=10);srv.shutdown();srv.server_close()
   self.assertNotIn('fixture-token',err.decode());self.assertNotIn('hhhhhhhh',err.decode())

class Manifests(unittest.TestCase):
 def test_render_and_custody_scope(self):
  import yaml
  source=ROOT/'big-bang-bootstrap/configuration/observability/mattermost-projection'
  with tempfile.TemporaryDirectory() as d:
   d=pathlib.Path(d);ca='-----BEGIN CERTIFICATE-----\nFIXTURE\n-----END CERTIFICATE-----\n'
   v={'projection_render':True,'projection_cluster_dns':'10.0.0.10','projection_output':str(d/'runtime'),'projection_sources':{'platform':['bigbang/bigbang','bigbang/mattermost'],'portal':['tenant-portal-config/portal']},'projection_mattermost_endpoint_cidrs':['192.0.2.4/32'],'projection_public_ca':ca}
   v.update(projection_ingress_namespace='kube-system',projection_ingress_name='rke2-traefik',projection_ingress_instance='rke2-traefik-kube-system',projection_ingress_port=8443)
   r=subprocess.run(['ansible-playbook',str(source/'render.yaml'),'-e',json.dumps(v)],capture_output=True,text=True);self.assertEqual(r.returncode,0,r.stdout+r.stderr)
   docs=list(yaml.safe_load_all((d/'runtime/runtime.yaml').read_text()));docs=[x for x in docs if x]
   for x in docs:
    if x['kind'] in ['Provider','Alert']:self.assertTrue(x['spec']['suspend'])
   net=next(x for x in docs if x['kind']=='NetworkPolicy')['spec']
   self.assertEqual(net['egress'][-1],{'to':[{'namespaceSelector':{'matchLabels':{'kubernetes.io/metadata.name':'kube-system'}},'podSelector':{'matchLabels':{'app.kubernetes.io/name':'rke2-traefik','app.kubernetes.io/instance':'rke2-traefik-kube-system'}}}], 'ports':[{'protocol':'TCP','port':8443}]})
   public=next(x for x in docs if x['kind']=='ConfigMap' and x['metadata']['name']=='mattermost-projection-public')
   self.assertEqual(public['data']['resolver.conf'],'resolver 10.0.0.10 valid=30s ipv6=off;')
   portable=[x for x in yaml.safe_load_all((d/'runtime/source.yaml').read_text()) if x]
   target=[x for x in yaml.safe_load_all((d/'runtime/target-prerequisites.yaml').read_text()) if x]
   self.assertEqual(len(target),2);self.assertNotIn('192.0.2.4',json.dumps(portable));self.assertNotIn('FIXTURE',json.dumps(portable))
   self.assertFalse(any(x['kind']=='ConfigMap' and x['metadata']['name']=='mattermost-projection-public' for x in portable))
   deploy=next(x for x in docs if x['kind']=='Deployment');self.assertFalse(deploy['spec']['template']['spec']['automountServiceAccountToken'])
   private=d/'private';private.mkdir(mode=0o700)
   for name,value in {'tls.crt':ca,'tls.key':'FIXTURE','platform-hook':'https://chat.example.invalid/hooks/'+('a'*26),'portal-hook':'https://chat.example.invalid/hooks/'+('b'*26)}.items():
    f=private/name;f.write_text(value);f.chmod(0o600)
   v.update(projection_prepare=True,projection_private_dir=str(private),projection_platform_hook_file=str(private/'platform-hook'),projection_portal_hook_file=str(private/'portal-hook'),projection_links={'platform':'https://grafana.example.invalid/alerting/list','portal':'https://portal.example.invalid/'})
   r=subprocess.run(['ansible-playbook',str(source/'prepare-records.yaml'),'-e',json.dumps(v)],capture_output=True,text=True);self.assertEqual(r.returncode,0,r.stdout+r.stderr)
   record=json.loads((private/'records.json').read_text());routes=json.loads(record['routes-v1']['routes.json'])
   self.assertNotEqual(routes['/platform']['token'],routes['/portal']['token']);self.assertEqual(len(routes['/platform']['token']),64)
   self.assertEqual(json.loads(record['portal-v1']['headers'])['Authorization'],'Bearer '+routes['/portal']['token'])
   self.assertEqual((private/'records.json').stat().st_mode & 0o777,0o600)
   v.update(projection_custody_render=True,projection_custody_output=str(d/'custody'),projection_bao_server='https://bao.example.invalid')
   r=subprocess.run(['ansible-playbook',str(source/'custody.yaml'),'-e',json.dumps(v)],capture_output=True,text=True);self.assertEqual(r.returncode,0,r.stdout+r.stderr)
   pre=[x for x in yaml.safe_load_all((d/'custody/prerequisites.yaml').read_text()) if x];con=[x for x in yaml.safe_load_all((d/'custody/consumers.yaml').read_text()) if x]
   self.assertEqual(len(pre),18);self.assertEqual(len(con),8)
   for x in pre:
    if x['kind']=='Role':
     for rule in x['rules']:
      if 'secrets' in rule['resources']:self.assertEqual(rule['verbs'],['get','update','patch']);self.assertEqual(len(rule['resourceNames']),1)
   for x in con:
    if x['kind']=='ExternalSecret':self.assertEqual(x['spec']['target']['creationPolicy'],'Merge');self.assertTrue(all(y['remoteRef']['key'].startswith('notifications/mm-projection/') for y in x['spec']['data']))
