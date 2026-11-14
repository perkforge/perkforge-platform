"""Synthetic HTTPS protocol fixture; does not prove live Keycloak permissions."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import ssl
import subprocess
import tempfile
import threading
import unittest
import urllib.parse
import yaml
from security.test_grafana_org_metadata import SOURCE

class Api(BaseHTTPRequestHandler):
    role=None; bindings={}; writes=[]; drift=False; mapper_drift=False; effective_only={}
    client_id='11111111-1111-4111-8111-111111111111'
    group_id='22222222-2222-4222-8222-222222222222'
    role_id='33333333-3333-4333-8333-333333333333'
    def log_message(self,*args): pass
    def reply(self,body,status=200):
        self.send_response(status); self.send_header('Content-Type','application/json'); self.end_headers()
        if status != 204: self.wfile.write(json.dumps(body).encode())
    def do_GET(self):
        path=urllib.parse.unquote(self.path)
        if path.endswith('/default-client-scopes'):
            self.reply([{'id':name,'name':name,'protocol':'openid-connect'} for name in ['basic','email','profile']])
        elif path.endswith('/optional-client-scopes'): self.reply([])
        elif '/client-scopes/' in path and path.endswith('/protocol-mappers/models'):
            name=path.split('/client-scopes/')[1].split('/')[0]
            self.reply(yaml.safe_load((SOURCE.parents[1]/'client-scopes.yaml').read_text())['sso_expected_client_scopes'][name])
        elif path == '/admin/realms/perkforge/clients/'+self.client_id:
            client=json.loads((SOURCE.parent/'client.json').read_text()); client['id']=self.client_id
            if self.drift: client['fullScopeAllowed']=True
            if self.mapper_drift: client['protocolMappers'].append({'name':'foreign-groups','protocol':'openid-connect','protocolMapper':'oidc-usermodel-realm-role-mapper','config':{'claim.name':'groups'}})
            self.reply(client)
        elif '/group-by-path/' in path:
            self.reply({'id':self.group_id if path.endswith('/engineers') else '44444444-4444-4444-8444-444444444444','path':path.split('/group-by-path/')[-1]})
        elif '/roles/pf-observability-platform-viewer' in path:
            self.reply(self.role or {},200 if self.role else 404)
        elif '/role-mappings/clients/' in path or '/scope-mappings/clients/' in path:
            self.reply(self.effective_only[path] if path in self.effective_only else self.bindings.get(path.removesuffix('/composite'), [] if '/groups/' in path else [{'id':'existing-owner','name':'/platform/admins'}]))
        else: self.reply({'error':'unexpected path'},404)
    def do_POST(self):
        path=urllib.parse.unquote(self.path); body=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
        self.writes.append((path,body))
        if path.endswith('/roles'):
            type(self).role=body|{'id':self.role_id,'containerId':self.client_id}; self.reply({},201)
        elif '/role-mappings/clients/' in path or '/scope-mappings/clients/' in path:
            before=self.bindings.get(path,[] if '/groups/' in path else [{'id':'existing-owner','name':'/platform/admins'}]); self.bindings[path]=before+body; self.reply({},204)
        else: self.reply({},400)

class ProtocolFixture(unittest.TestCase):
    def test_exact_additive_retry_and_client_drift(self):
        Api.role=None; Api.bindings={}; Api.writes=[]; Api.drift=False; Api.mapper_drift=False; Api.effective_only={}
        with tempfile.TemporaryDirectory() as temp:
            folder=Path(temp); cert=folder/'ca.pem'; key=folder/'key.pem'
            subprocess.run(['openssl','req','-x509','-newkey','rsa:2048','-nodes','-keyout',str(key),'-out',str(cert),'-days','1','-subj','/CN=localhost','-addext','subjectAltName=DNS:localhost'],check=True,capture_output=True)
            server=ThreadingHTTPServer(('127.0.0.1',0),Api)
            tls=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER); tls.load_cert_chain(cert,key); server.socket=tls.wrap_socket(server.socket,server_side=True)
            threading.Thread(target=server.serve_forever,daemon=True).start(); self.addCleanup(server.server_close); self.addCleanup(server.shutdown)
            play=[{'hosts':'localhost','connection':'local','gather_facts':False,'vars':{
                'grafana_entitlement_approval':'grafana-exact-canonical-group-entitlement-v1',
                'grafana_org_context_id':'portal','metadata_api':'https://localhost:'+str(server.server_port)+'/admin/realms/perkforge',
                'metadata_client':{'json':[{'id':Api.client_id}]},'metadata_kc_headers':{'Authorization':'Bearer synthetic'},
                'entitlement':{'client_id':Api.client_id,'group_id':Api.group_id,'canonical_group':'/platform/engineers','role_name':'pf-observability-platform-viewer'}},
                'module_defaults':{'ansible.builtin.uri':{'ca_path':str(cert),'validate_certs':True,'use_proxy':False,'use_netrc':False,'follow_redirects':'none'}},
                'tasks':[{'ansible.builtin.include_tasks':str(SOURCE/'ensure-entitlement.yaml')}]}]
            (folder/'play.yaml').write_text(yaml.safe_dump(play))
            def run(): return subprocess.run(['ansible-playbook','-i','localhost,',str(folder/'play.yaml')],env=dict(os.environ,KUBECONFIG='/dev/null'),capture_output=True,text=True)
            result=run(); self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            self.assertEqual(len(Api.writes),3)
            self.assertEqual(len(Api.bindings),2)
            for path,roles in Api.bindings.items(): self.assertEqual({r['id'] for r in roles},{Api.role_id} if '/groups/' in path else {'existing-owner',Api.role_id})
            result=run(); self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            self.assertEqual(len(Api.writes),3)
            Api.drift=True; result=run(); self.assertNotEqual(result.returncode,0)
            self.assertEqual(len(Api.writes),3)
            Api.drift=False
            Api.bindings['/admin/realms/perkforge/groups/44444444-4444-4444-8444-444444444444/role-mappings/clients/'+Api.client_id]=[{'id':'unexpected','name':'/platform/admins','composite':False,'containerId':Api.client_id}]
            result=run(); self.assertNotEqual(result.returncode,0); self.assertEqual(len(Api.writes),3)
            Api.bindings.pop('/admin/realms/perkforge/groups/44444444-4444-4444-8444-444444444444/role-mappings/clients/'+Api.client_id)
            Api.mapper_drift=True; result=run(); self.assertNotEqual(result.returncode,0); self.assertEqual(len(Api.writes),3)
            Api.mapper_drift=False
            for gid in ['44444444-4444-4444-8444-444444444444',Api.group_id]:
                Api.effective_only={'/admin/realms/perkforge/groups/'+gid+'/role-mappings/clients/'+Api.client_id+'/composite':[{'name':'/platform/admins','id':'unexpected','composite':True,'containerId':Api.client_id}]}
                result=run(); self.assertNotEqual(result.returncode,0); self.assertEqual(len(Api.writes),3)
