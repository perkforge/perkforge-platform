"""TEST ONLY: execute real Ansible URI tasks against isolated synthetic HTTPS APIs."""
import copy
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import shutil
import ssl
import subprocess
import tempfile
import threading
import unittest
from urllib.parse import urlsplit
import yaml

ROOT=Path(__file__).resolve().parents[2]


@unittest.skipUnless(os.environ.get('RUN_PLATFORM_CONFIG_TESTS') and shutil.which('ansible-playbook'), 'enable isolated Ansible API tests explicitly')
class PlatformConfigAPI(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.work=Path(self.tmp.name)
        subprocess.run(['openssl','req','-x509','-newkey','rsa:2048','-nodes','-days','1','-subj','/CN=localhost',
            '-addext','subjectAltName=DNS:localhost','-keyout',str(self.work/'key.pem'),'-out',str(self.work/'ca.pem')],
            check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        self.state={'client':None,'mappers':[],'scope':{},'mounts':{},'auths':{},'resources':{},'writes':[]}
        state=self.state
        class Handler(BaseHTTPRequestHandler):
            def log_message(self,*args):pass
            def respond(self,status,value=None):
                data=json.dumps(value).encode() if value is not None else b''
                self.send_response(status);self.send_header('Content-Type','application/json');self.end_headers();self.wfile.write(data)
            def do_GET(self):
                path=urlsplit(self.path).path
                if path=='/kc/admin/realms/perkforge':return self.respond(200,{'attributes':{'perkforge-managed':'true'}})
                if path=='/kc/admin/realms/perkforge/clients':return self.respond(200,[state['client']] if state['client'] else [])
                if path.endswith('/protocol-mappers/models'):return self.respond(200,state['mappers'])
                if path.endswith('/scope-mappings'):return self.respond(200,state['scope'])
                if path.endswith('/client-secret'):return self.respond(200,{'value':'synthetic-client-credential'})
                if path=='/v1/sys/mounts':return self.respond(200,{'data':state['mounts']})
                if path=='/v1/sys/auth':return self.respond(200,{'data':state['auths']})
                if path in state['resources']:return self.respond(200,{'data':state['resources'][path]})
                return self.respond(404,{'errors':['synthetic missing resource']})
            def do_POST(self):self.mutate()
            def do_PUT(self):self.mutate()
            def mutate(self):
                path=urlsplit(self.path).path
                raw=self.rfile.read(int(self.headers.get('Content-Length',0)))
                if path=='/kc/realms/master/protocol/openid-connect/token':
                    return self.respond(200,{'access_token':'synthetic-admin-session'})
                value=json.loads(raw)
                state['writes'].append((self.command,path))
                if path=='/kc/admin/realms/perkforge/clients':
                    state['client']={**value,'id':'owned-client'}
                    state['client']['attributes']['keycloak-default']='preserved'
                    state['mappers']=[{**m,'id':'groups-id'} for m in value['protocolMappers']]
                    return self.respond(201)
                if '/protocol-mappers/models/' in path:
                    state['mappers']=[value];return self.respond(204)
                if path=='/kc/admin/realms/perkforge/clients/owned-client':
                    state['client']=value;return self.respond(204)
                if path.startswith('/v1/sys/mounts/'):
                    state['mounts'][path.rsplit('/',1)[1]+'/']=value;return self.respond(204)
                if path.startswith('/v1/sys/auth/'):
                    state['auths'][path.rsplit('/',1)[1]+'/']=value;return self.respond(204)
                state['resources'][path]=value
                return self.respond(204)
        self.server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
        context=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(str(self.work/'ca.pem'),str(self.work/'key.pem'))
        self.server.socket=context.wrap_socket(self.server.socket,server_side=True)
        thread=threading.Thread(target=self.server.serve_forever,daemon=True);thread.start()
        self.addCleanup(self.server.server_close);self.addCleanup(self.server.shutdown)
        for name in ('admin-password','bootstrap-token'):
            p=self.work/name;p.write_text('synthetic-private-input');p.chmod(0o600)
        (self.work/'ansible.cfg').write_text('[defaults]\nretry_files_enabled = False\n')
        self.url=f'https://localhost:{self.server.server_port}'
        self.vars={'keycloak_url':self.url+'/kc','openbao_url':self.url,
            'keycloak_admin_password_file':str(self.work/'admin-password'),
            'openbao_operator_token_file':str(self.work/'bootstrap-token'),
            'public_ca_file':str(self.work/'ca.pem')}
        (self.work/'vars.yaml').write_text(yaml.safe_dump(self.vars))

    def run_play(self):
        result=subprocess.run(['ansible-playbook','-i','localhost,',str(ROOT/'platform-config/configure.yaml'),
            '-e','@'+str(self.work/'vars.yaml')],capture_output=True,text=True,timeout=90,
            env={**os.environ,'ANSIBLE_LOCAL_TEMP':str(self.work/'local'),'ANSIBLE_REMOTE_TEMP':str(self.work/'remote'),
                 'ANSIBLE_NOCOLOR':'1','ANSIBLE_CONFIG':str(self.work/'ansible.cfg')})
        for marker in ('synthetic-private-input','synthetic-client-credential','synthetic-admin-session'):
            self.assertNotIn(marker,result.stdout+result.stderr)
        return result

    def test_create_then_idempotent_reconcile_and_refuse_unowned_client(self):
        first=self.run_play()
        self.assertEqual(first.returncode,0,first.stdout+first.stderr)
        self.assertTrue(self.state['writes'])
        before=copy.deepcopy(self.state['writes'])
        second=self.run_play()
        self.assertEqual(second.returncode,0,second.stdout+second.stderr)
        self.assertEqual(self.state['writes'],before)
        self.assertIn('changed=0',second.stdout)
        self.assertEqual(self.state['client']['attributes']['keycloak-default'],'preserved')
        self.assertFalse(any('/users' in path or '/groups' in path or 'role-mappings' in path for _,path in before))
        self.state['client']['attributes']={}
        denied=self.run_play()
        self.assertNotEqual(denied.returncode,0)
        self.assertEqual(self.state['writes'],before)

    def test_conflicting_mount_is_never_converted(self):
        desired=json.loads((ROOT/'local-lab/openbao/config/keycloak-client.json').read_text())
        self.state['client']={**desired,'id':'owned-client'}
        self.state['mappers']=[{**desired['protocolMappers'][0],'id':'groups-id'}]
        self.state['mounts']['tenants/']={'type':'kv','options':{'version':'1'}}
        result=self.run_play()
        self.assertNotEqual(result.returncode,0)
        self.assertIn('Refuse conflicting platform or tenant mounts',result.stdout)
        self.assertFalse(any(path.startswith('/v1/sys/mounts/') for _,path in self.state['writes']))
