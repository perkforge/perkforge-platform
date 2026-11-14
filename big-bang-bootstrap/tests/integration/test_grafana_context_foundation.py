"""Synthetic native REST contract only; no live identity writes."""
from integration.test_grafana_org_adapter import *
import uuid
class FoundationApi(Api):
    groups={}; roles={}; mapped={}; writes=[]
    def do_GET(self):
        p=urllib.parse.unquote(self.path)
        if '/group-by-path/' in p:
            v=self.groups.get('/'+p.split('/group-by-path/')[-1].lstrip('/')); self.reply(v or {},200 if v else 404)
        elif '/roles/' in p:
            v=self.roles.get(p.rsplit('/',1)[-1]);self.reply(v or {},200 if v else 404)
        elif '/groups/' in p and '/role-mappings' in p:
            gid=p.split('/groups/')[1].split('/')[0];v=self.mapped.get(gid,[])
            self.reply({'realmMappings':v} if p.endswith('/role-mappings') else v)
        else:self.reply({},404)
    def do_POST(self):
        p=urllib.parse.unquote(self.path);b=json.loads(self.rfile.read(int(self.headers['Content-Length'])));self.writes.append((p,b))
        if p.endswith('/roles'):
            self.roles[b['name']]=b|{'id':str(uuid.uuid4())};self.reply({},201)
        elif p.endswith('/children'):
            parent=p.split('/groups/')[1].split('/')[0];found=next(g for g in self.groups.values() if g['id']==parent)
            gid=str(uuid.uuid4());path=found['path']+'/'+b['name'];self.groups[path]=b|{'id':gid,'path':path}
            self.send_response(201);self.send_header('Location','https://localhost/groups/'+gid);self.end_headers()
        elif p.endswith('/role-mappings/realm'):
            gid=p.split('/groups/')[1].split('/')[0];self.mapped[gid]=b;self.reply({},204)
        else:self.reply({},400)
class FoundationFixture(unittest.TestCase):
    def test_additive_foundation_and_no_adoption(self):
        parent='55555555-5555-4555-8555-555555555555'
        FoundationApi.groups={'/tenants':{'id':parent,'name':'tenants','path':'/tenants','attributes':{'perkforge-managed':['true'],'perkforge-foundation':['v1']}}};FoundationApi.roles={};FoundationApi.mapped={};FoundationApi.writes=[]
        with tempfile.TemporaryDirectory() as temp:
            folder=Path(temp);cert=folder/'ca.pem';key=folder/'key.pem'
            subprocess.run(['openssl','req','-x509','-newkey','rsa:2048','-nodes','-keyout',str(key),'-out',str(cert),'-days','1','-subj','/CN=localhost','-addext','subjectAltName=DNS:localhost'],check=True,capture_output=True)
            server=ThreadingHTTPServer(('127.0.0.1',0),FoundationApi);tls=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER);tls.load_cert_chain(cert,key);server.socket=tls.wrap_socket(server.socket,server_side=True);threading.Thread(target=server.serve_forever,daemon=True).start();self.addCleanup(server.server_close);self.addCleanup(server.shutdown)
            vars={'grafana_foundation_approval':'grafana-canonical-context-foundation-v1','grafana_org_context_id':'portal','foundation_parent_id':parent,'foundation_expected_ids':{p:None for p in ['/tenants/portal','/tenants/portal/admins','/tenants/portal/developers','/tenants/portal/viewers']},'metadata_api':'https://localhost:'+str(server.server_port)+'/admin/realms/perkforge','metadata_kc_headers':{'Authorization':'Bearer synthetic'}}
            play=[{'hosts':'localhost','connection':'local','gather_facts':False,'vars':vars,'module_defaults':{'ansible.builtin.uri':{'ca_path':str(cert),'validate_certs':True,'use_proxy':False,'use_netrc':False,'follow_redirects':'none'}},'tasks':[{'ansible.builtin.include_tasks':str(SOURCE/'ensure-foundation.yaml')}]}]
            def run():
                (folder/'play.yaml').write_text(yaml.safe_dump(play));return subprocess.run(['ansible-playbook','-i','localhost,',str(folder/'play.yaml')],capture_output=True,text=True)
            result=run();self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            self.assertEqual(len(FoundationApi.writes),10);self.assertEqual(len(FoundationApi.groups),5);self.assertEqual(len(FoundationApi.roles),3)
            # Retry requires reviewed newly assigned IDs, never silently adopt by name.
            result=run();self.assertNotEqual(result.returncode,0);self.assertEqual(len(FoundationApi.writes),10)
            vars['foundation_expected_ids']={p:FoundationApi.groups[p]['id'] for p in vars['foundation_expected_ids']}
            result=run();self.assertEqual(result.returncode,0,result.stdout+result.stderr);self.assertEqual(len(FoundationApi.writes),10)
