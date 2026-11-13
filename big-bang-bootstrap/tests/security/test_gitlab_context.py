"""Real read-only Ansible over synthetic HTTPS, never the installed GitLab."""
import copy
import json
import os
import ssl
import subprocess
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PLAY = ROOT / 'configuration/packages/gitlab/inspect-context.yaml'

class ContextInspection(unittest.TestCase):
    def test_exact_context_and_fail_closed_boundaries(self):
        with tempfile.TemporaryDirectory(prefix='gitlab-context-') as directory:
            d = Path(directory)
            subprocess.run(['openssl','req','-x509','-newkey','rsa:2048','-nodes','-days','1',
                            '-subj','/CN=localhost','-addext','subjectAltName=DNS:localhost',
                            '-keyout',str(d/'key'),'-out',str(d/'ca')], check=True,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            baseline = {
                '/api/v4/version': {'version':'19.4.2-ee'},
                '/api/v4/groups/31?with_projects=false': {'id':31,'full_path':'tenants/example','visibility':'private'},
                '/api/v4/projects/41': {'id':41,'path_with_namespace':'tenants/example/portal','visibility':'private','archived':False,
                                      'namespace':{'kind':'group','id':31,'full_path':'tenants/example'},
                                      'description':'UNTRUSTED-PRIVATE-DESCRIPTION'},
            }
            state = {'responses':copy.deepcopy(baseline), 'calls':[], 'status':200}
            class Handler(BaseHTTPRequestHandler):
                def log_message(self,*args): pass
                def do_GET(self):
                    state['calls'].append(('GET',self.path))
                    status = state['status'] if self.headers.get('PRIVATE-TOKEN') == 'OFFLINE-CONTEXT-TOKEN' else 403
                    self.send_response(status); self.send_header('Content-Type','application/json'); self.end_headers()
                    self.wfile.write(json.dumps(state['responses'].get(self.path, {})).encode())
                def do_POST(self): state['calls'].append(('POST',self.path)); self.send_error(405)
                do_PUT = do_PATCH = do_DELETE = do_POST
            server = ThreadingHTTPServer(('127.0.0.1',0),Handler)
            ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER); ctx.load_cert_chain(d/'ca',d/'key')
            server.socket = ctx.wrap_socket(server.socket,server_side=True)
            threading.Thread(target=server.serve_forever,daemon=True).start()
            self.addCleanup(server.server_close); self.addCleanup(server.shutdown)
            token = d/'token'; token.write_text('OFFLINE-CONTEXT-TOKEN'); token.chmod(0o600)
            values = {'gitlab_context_run':True,'gitlab_context_scope':'gitlab-context-inspect-v1',
                      'gitlab_context_id':'example','gitlab_native_origin':'https://localhost:'+str(server.server_port),
                      'gitlab_native_ca_file':str(d/'ca'),'gitlab_native_token_file':str(token),
                      'gitlab_context_group_id':31,'gitlab_context_group_path':'tenants/example',
                      'gitlab_context_project_id':41,'gitlab_context_project_path':'tenants/example/portal'}
            def run(overrides=None, check=False):
                state['calls'].clear()
                vf=d/'vars.json'; vf.write_text(json.dumps({**values,**(overrides or {})})); vf.chmod(0o600)
                r=subprocess.run(['ansible-playbook','-i','localhost,',str(PLAY),'-e','@'+str(vf)]+(['--check'] if check else []),
                                 env={**os.environ,'ANSIBLE_LOCAL_TEMP':str(d/'local'),'ANSIBLE_REMOTE_TEMP':str(d/'remote')},
                                 capture_output=True,text=True,timeout=60)
                self.assertNotIn('OFFLINE-CONTEXT-TOKEN',r.stdout+r.stderr)
                self.assertNotIn('UNTRUSTED-PRIVATE-DESCRIPTION',r.stdout+r.stderr)
                self.assertTrue(all(m=='GET' for m,p in state['calls']))
                return r
            for overrides,check in [({'gitlab_context_run':False},False), ({},True)]:
                r=run(overrides,check); self.assertEqual(r.returncode,0,r.stdout+r.stderr); self.assertEqual(state['calls'],[])
            for _ in range(2):
                r=run(); self.assertEqual(r.returncode,0,r.stdout+r.stderr)
                self.assertIn('changed=0',r.stdout)
                self.assertEqual([p for m,p in state['calls']],list(baseline))
            bad_inputs=[{'gitlab_context_group_id':True},{'gitlab_context_project_id':0},
                        {'gitlab_context_project_path':'tenants/other/portal'},
                        {'gitlab_context_project_path':'tenants/example/../portal'},
                        {'gitlab_context_scope':'wrong'}, {'gitlab_native_origin':'http://localhost'},
                        {'gitlab_context_id':'../portal'}]
            for override in bad_inputs:
                with self.subTest(override=override):
                    self.assertNotEqual(run(override).returncode,0); self.assertEqual(state['calls'],[])
            for target,field,value in [('/api/v4/groups/31?with_projects=false','id',32),
                                       ('/api/v4/groups/31?with_projects=false','visibility','public'),
                                       ('/api/v4/projects/41','id',42),
                                       ('/api/v4/projects/41','path_with_namespace','tenants/other/portal'),
                                       ('/api/v4/projects/41','visibility','internal'),
                                       ('/api/v4/projects/41','archived',True),
                                       ('/api/v4/projects/41','namespace',{'kind':'user','id':31,'full_path':'tenants/example'}),
                                       ('/api/v4/projects/41','namespace',{'kind':'group','id':32,'full_path':'tenants/example'}),
                                       ('/api/v4/version','version','20.0.0')]:
                with self.subTest(field=field,value=value):
                    state['responses']=copy.deepcopy(baseline); state['responses'][target][field]=value
                    self.assertNotEqual(run().returncode,0)
            state['responses']=copy.deepcopy(baseline)
            for status in (302,403,404,503):
                state['status']=status
                self.assertNotEqual(run().returncode,0)
            state['status']=200; token.chmod(0o644)
            self.assertNotEqual(run().returncode,0); self.assertEqual(state['calls'],[])
