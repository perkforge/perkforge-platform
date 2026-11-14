"""Pinned native Grafana OAuth org sync, synthetic localhost issuer; no live credentials."""
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import http.cookiejar
import json
import os
from pathlib import Path
import socket
import subprocess
import tempfile
import threading
import time
import unittest
import urllib.parse
import urllib.request
import yaml
from security.test_grafana_org_mapping import SOURCE, CONTEXT

class Issuer(BaseHTTPRequestHandler):
    subject = 'mixed'
    claims = {'mixed':['pf-observability-portal-tenant-admin','pf-observability-other-tenant-viewer'],
              'engineer':['pf-observability-platform-viewer'], 'owner':['/platform/admins'], 'unknown':[]}
    def log_message(self, *args): pass
    def do_GET(self):
        if self.path.startswith('/authorize'):
            args = urllib.parse.parse_qs(urllib.parse.urlsplit(self.path).query)
            self.send_response(302); self.send_header('Location', args['redirect_uri'][0]+'?'+urllib.parse.urlencode({'code':'synthetic','state':args['state'][0]})); self.end_headers(); return
        self.reply({'sub':self.subject, 'preferred_username':self.subject, 'email':self.subject+'@example.test', 'groups':self.claims[self.subject]})
    def do_POST(self):
        self.rfile.read(int(self.headers.get('Content-Length', 0)))
        self.reply({'access_token':'synthetic', 'token_type':'Bearer'})
    def reply(self, body):
        self.send_response(200); self.send_header('Content-Type','application/json'); self.end_headers(); self.wfile.write(json.dumps(body).encode())

def port():
    with socket.socket() as sock: sock.bind(('127.0.0.1',0)); return sock.getsockname()[1]

class NativeGrafanaOrgOAuth(unittest.TestCase):
    platform_only=False
    def test_native_mixed_roles_engineer_and_owner(self):
        binary = os.environ.get('GRAFANA_VALIDATE_BIN')
        if not binary: self.skipTest('Set checksum-pinned GRAFANA_VALIDATE_BIN; no download')
        pins = yaml.safe_load((SOURCE.parents[3]/'observability/tenant-query/sources.yaml').read_text())
        self.assertEqual(hashlib.sha256(Path(binary).read_bytes()).hexdigest(), pins['grafana']['linux_amd64_binary_sha256'])
        with tempfile.TemporaryDirectory() as temp:
            folder=Path(temp); context=yaml.safe_load(CONTEXT.read_text())['paas_context']
            other=json.loads(json.dumps(context).replace('portal','other'))
            inputs={'grafana_org_render':True,'grafana_org_output':str(folder/'render'), 'grafana_org_contexts':[
                {'context':context,'org_id':2,'query_identity':'pf-log-portal-read'}, {'context':other,'org_id':3,'query_identity':'pf-log-other-read'}]}
            if self.platform_only: inputs.update(grafana_org_contexts=[],grafana_org_platform_only=True)
            run=subprocess.run(['ansible-playbook','-i','localhost,',str(SOURCE/'render.yaml'),'-e',json.dumps(inputs)], capture_output=True,text=True)
            self.assertEqual(run.returncode,0,run.stdout+run.stderr)
            oauth=yaml.safe_load((folder/'render/oauth.yaml').read_text())
            issuer=ThreadingHTTPServer(('127.0.0.1',0),Issuer); threading.Thread(target=issuer.serve_forever,daemon=True).start()
            self.addCleanup(issuer.server_close); self.addCleanup(issuer.shutdown)
            base='http://127.0.0.1:'+str(port()); identity='http://127.0.0.1:'+str(issuer.server_port)
            oauth.update(enabled=True, client_id='fixture',client_secret='synthetic',auth_url=identity+'/authorize',token_url=identity+'/token',api_url=identity+'/userinfo',allow_sign_up=True,scopes='openid profile email')
            config='[server]\nhttp_addr=127.0.0.1\nhttp_port='+base.rsplit(':',1)[1]+'\nroot_url='+base+'\n[paths]\ndata='+str(folder/'data')+'\nlogs='+str(folder/'logs')+'\nplugins='+str(folder/'plugins')+'\nprovisioning='+str(folder/'provisioning')+'\n[security]\nadmin_user=fixture\nadmin_password=synthetic\n[analytics]\nreporting_enabled=false\ncheck_for_updates=false\ncheck_for_plugin_updates=false\n[plugins]\npreinstall_disabled=true\n[auth.generic_oauth]\n'
            config+='\n'.join(k+' = '+(str(v).lower() if isinstance(v,bool) else str(v)) for k,v in oauth.items())+'\n'
            (folder/'grafana.ini').write_text(config)
            with (folder/'process.log').open('w') as log:
                proc=subprocess.Popen([binary,'server','--homepath',str(Path(binary).resolve().parents[1]),'--config',str(folder/'grafana.ini')],stdout=log,stderr=log)
                try:
                    for _ in range(200):
                        try:
                            urllib.request.urlopen(base+'/api/health',timeout=1).close(); break
                        except OSError: time.sleep(.1)
                    else: self.fail((folder/'process.log').read_text()[-4000:])
                    import base64
                    admin={'Authorization':'Basic '+base64.b64encode(b'fixture:synthetic').decode()}
                    for name in ['fixture-a','fixture-b']:
                        req=urllib.request.Request(base+'/api/orgs',data=json.dumps({'name':name}).encode(),headers=admin|{'Content-Type':'application/json'})
                        urllib.request.urlopen(req).close()
                    created_users=json.load(urllib.request.urlopen(urllib.request.Request(base+'/api/orgs/2/users',headers=admin)))
                    self.assertEqual([(u['login'],u['role']) for u in created_users],[('fixture','Admin')])

                    source=urllib.request.Request(base+'/api/datasources',data=json.dumps({'uid':'platform-only','name':'platform-only','type':'prometheus','access':'proxy','url':'http://127.0.0.1:1'}).encode(),headers=admin|{'Content-Type':'application/json'})
                    urllib.request.urlopen(source).close()
                    cases=[('engineer',{1:'Viewer'}),('owner',{1:'Admin'})] if self.platform_only else [('mixed',{2:'Admin',3:'Viewer'}),('engineer',{1:'Viewer'}),('owner',{1:'Admin'})]
                    for actor,expected in cases:
                        Issuer.subject=actor
                        browser=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
                        browser.open(base+'/login/generic_oauth').close()
                        user=json.load(browser.open(base+'/api/user'))
                        self.assertEqual(user['isGrafanaAdmin'],actor=='owner')
                        orgs=json.load(browser.open(base+'/api/user/orgs'))
                        self.assertEqual({o['orgId']:o['role'] for o in orgs},expected, actor)
                        if actor == 'mixed':
                            # Default auto_assign_org must not leak platform org or datasource.
                            for path,method in [('/api/user/using/1','POST'),('/api/datasources/uid/platform-only','GET')]:
                                request=urllib.request.Request(base+path,headers={'X-Grafana-Org-Id':'1'},method=method)
                                with self.assertRaises(urllib.error.HTTPError) as denied: browser.open(request)
                                self.assertIn(denied.exception.code,[401,403,404])
                            # Existing cookie loses only A after native membership removal.
                            remove=urllib.request.Request(base+'/api/orgs/2/users/'+str(user['id']),headers=admin,method='DELETE')
                            urllib.request.urlopen(remove).close()
                            req=urllib.request.Request(base+'/api/user/using/2',method='POST')
                            with self.assertRaises(urllib.error.HTTPError) as denied: browser.open(req)
                            self.assertIn(denied.exception.code,[401,403])
                            orgs=json.load(browser.open(base+'/api/user/orgs'))
                            self.assertEqual({o['orgId']:o['role'] for o in orgs},{3:'Viewer'})
                            logout=urllib.request.Request(base+'/api/admin/users/'+str(user['id'])+'/logout',headers=admin,method='POST')
                            urllib.request.urlopen(logout).close()
                            with self.assertRaises(urllib.error.HTTPError): browser.open(base+'/api/user')
                            Issuer.claims['mixed']=['pf-observability-other-tenant-viewer']
                            browser.open(base+'/login/generic_oauth').close()
                            orgs=json.load(browser.open(base+'/api/user/orgs'))
                            self.assertEqual({o['orgId']:o['role'] for o in orgs},{3:'Viewer'})
                            with self.assertRaises(urllib.error.HTTPError):
                                browser.open(urllib.request.Request(base+'/api/user/using/2',method='POST'))


                    # An authenticated but unmapped identity must gain no org access.
                    if self.platform_only:
                        Issuer.subject='tenant-only'; Issuer.claims['tenant-only']=['pf-observability-portal-tenant-admin']
                        browser=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
                        browser.open(base+'/login/generic_oauth').close()
                        with self.assertRaises(urllib.error.HTTPError): browser.open(base+'/api/user')
                    Issuer.subject='unknown'
                    browser=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
                    browser.open(base+'/login/generic_oauth').close()
                    with self.assertRaises(urllib.error.HTTPError): browser.open(base+'/api/user')
                finally:
                    proc.terminate()
                    try: proc.wait(timeout=10)
                    except subprocess.TimeoutExpired: proc.kill(); proc.wait()

class NativeGrafanaPlatformOnlyOAuth(NativeGrafanaOrgOAuth):
    platform_only=True
