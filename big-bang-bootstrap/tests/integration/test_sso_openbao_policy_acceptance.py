"""Default-off guards and opt-in real pinned engine/Ansible cleanup tests.
Only isolated synthetic tokens and values, never operator inputs or live URLs.
"""
import importlib.util
import json
import os
from pathlib import Path
import secrets
import ssl
import subprocess
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import requests

ROOT = Path(__file__).resolve().parents[2]
PLAY = ROOT/'configuration/authorization/sso/accept-policy.yaml'
spec = importlib.util.spec_from_file_location('policy_fixture', Path(__file__).with_name('test_sso_openbao_self_session.py'))
fixture = importlib.util.module_from_spec(spec);spec.loader.exec_module(fixture)


class Defaults(unittest.TestCase):
    def test_default_and_check_contact_no_api_or_credentials(self):
        with tempfile.TemporaryDirectory() as d:
            for args in ([], ['-e','bao_test_apply=true','--check']):
                r=subprocess.run(['ansible-playbook',str(PLAY),*args],
                    env={**os.environ,'ANSIBLE_LOCAL_TEMP':d+'/local','ANSIBLE_REMOTE_TEMP':d+'/remote'},
                    capture_output=True,text=True,timeout=30)
                self.assertEqual(r.returncode,0,r.stdout+r.stderr)
                self.assertIn('changed=0',r.stdout)


@unittest.skipUnless(os.environ.get('RUN_OPENBAO_POLICY_TESTS') == '1',
                     'opt in to isolated pinned 2.7.2 engine and Ansible')
class AcceptanceAPI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = fixture.PinnedEngine
        cls.engine.setUpClass()
        cls.addClassCleanup(cls.engine.doClassCleanups)
        for mount in ('platform','tenants'):
            assert cls.engine.call('POST','/sys/mounts/'+mount+'/tune',
                {'description':'PerkForge coordinated-sso-v1 data mount'}).status_code == 204
        assert cls.engine.call('PUT','/sys/policies/acl/perkforge-sso-v1-platform-admin',
                               {'policy':fixture.policy()}).status_code == 204

    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='openbao-acceptance-api-');self.addCleanup(self.tmp.cleanup)
        self.d=Path(self.tmp.name);self.evidence=self.d/'evidence';self.evidence.mkdir(mode=0o700)
        subprocess.run(['openssl','req','-x509','-newkey','rsa:2048','-nodes','-days','1','-subj','/CN=localhost',
            '-addext','subjectAltName=DNS:localhost','-keyout',str(self.d/'key'),'-out',str(self.d/'ca')],
            check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        engine=self.engine;state={'mode':'normal','calls':[],'issued':[]};self.state=state
        class Handler(BaseHTTPRequestHandler):
            def log_message(self,*args):pass
            def forward(self):
                length=int(self.headers.get('Content-Length','0'));body=self.rfile.read(length)
                header=self.headers.get('X-Vault-Token');state['calls'].append((self.command,self.path,header==engine.root))
                headers={k:self.headers[k] for k in ['X-Vault-Token','Content-Type'] if k in self.headers}
                if state['mode']=='cleanup-fails' and self.command=='DELETE' and '/platform/metadata/acceptance/' in self.path:
                    status,data=403,b'{"errors":["synthetic cleanup interruption"]}'
                elif state['mode']=='tenant-admitted' and self.command=='GET' and '/tenants/data/acceptance/' in self.path and header!=engine.root:
                    status,data=200,b'{"data":{"data":{"sample":"synthetic-only"}}}'
                else:
                    r=engine.session.request(self.command,engine.base.removesuffix('/v1')+self.path,
                        headers=headers,data=body or None,timeout=5,allow_redirects=False)
                    status,data=r.status_code,r.content
                    if self.path=='/v1/auth/token/create' and status==200:
                        state['issued'].append(r.json()['auth'])
                        if state['mode']=='uncertain-issuance':status,data=500,b'{"errors":["synthetic lost response"]}'
                self.send_response(status);self.send_header('Content-Type','application/json');self.end_headers()
                if data:self.wfile.write(data)
            do_GET=forward;do_POST=forward;do_PUT=forward;do_DELETE=forward
        self.server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
        context=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER);context.load_cert_chain(str(self.d/'ca'),str(self.d/'key'))
        self.server.socket=context.wrap_socket(self.server.socket,server_side=True)
        thread=threading.Thread(target=self.server.serve_forever,daemon=True);thread.start()
        self.addCleanup(self.server.server_close);self.addCleanup(self.server.shutdown)
        rootfile=self.d/'root';rootfile.write_text(self.engine.root);rootfile.chmod(0o600)
        cluster=self.engine.call('GET','/sys/health').json()['cluster_id']
        self.ident='openbao-check-'+secrets.token_hex(6);self.key='acceptance/'+self.ident+'/sample'
        self.vars={'bao_test_apply':True,'bao_test_scope':'openbao-policy-acceptance-v1',
            'bao_test_origin':'https://localhost:'+str(self.server.server_port),'bao_test_ca_file':str(self.d/'ca'),
            'bao_test_root_file':str(rootfile),'bao_test_cluster_id':cluster,
            'bao_test_evidence_dir':str(self.evidence),'bao_test_id':self.ident}

    def play(self,extra=None):
        inputs=self.d/'inputs.json';inputs.write_text(json.dumps({**self.vars,**(extra or {})}));inputs.chmod(0o600)
        r=subprocess.run(['ansible-playbook',str(PLAY),'-e','@'+str(inputs)],capture_output=True,text=True,timeout=120,
            env={**os.environ,'ANSIBLE_LOCAL_TEMP':str(self.d/'local'),'ANSIBLE_REMOTE_TEMP':str(self.d/'remote')})
        self.assertNotIn(self.engine.root,r.stdout+r.stderr)
        for token in self.state['issued']:self.assertNotIn(token['client_token'],r.stdout+r.stderr)
        return r

    def assert_token_rejected(self):
        for token in self.state['issued']:
            r=self.engine.call('POST','/auth/token/lookup-accessor',{'accessor':token['accessor']})
            self.assertEqual(r.status_code,400)
            self.assertEqual(self.engine.call('GET','/auth/token/lookup-self',token=token['client_token']).status_code,403)
        self.assertFalse((self.evidence/'test-token.json').exists())

    def assert_data_gone(self):
        for mount in ('platform','tenants'):
            self.assertEqual(self.engine.call('GET','/'+mount+'/metadata/'+self.key).status_code,404)

    def test_full_allow_denial_and_exact_cleanup(self):
        r=self.play();self.assertEqual(r.returncode,0,r.stdout+r.stderr)
        result=json.loads((self.evidence/'result.json').read_text())
        self.assertTrue(result['testsPassed'] and result['exactTokenRevoked'] and result['exactDummyKeysDestroyed'])
        self.assertFalse(result['oidcGroupDenialTested'])
        self.assertEqual(len(self.state['issued']),1)
        self.assert_token_rejected();self.assert_data_gone()
        self.assertEqual(self.engine.call('GET','/auth/token/lookup-self').status_code,200)
        self.assertTrue(any(method=='POST' and '/platform/data/acceptance/' in path and not root for method,path,root in self.state['calls']))

    def test_preexisting_key_and_wrong_target_refuse_before_writes(self):
        self.engine.call('POST','/platform/data/'+self.key,{'data':{'sample':'existing-fixture-only'}})
        r=self.play();self.assertNotEqual(r.returncode,0)
        self.assertEqual(self.state['issued'],[])
        self.assertFalse(any(method in ('POST','PUT','DELETE') for method,_,_ in self.state['calls']))
        self.assertEqual(self.engine.call('GET','/platform/data/'+self.key).json()['data']['data']['sample'],'existing-fixture-only')
        self.state['calls'].clear()
        r=self.play({'bao_test_cluster_id':'wrong'});self.assertNotEqual(r.returncode,0)
        self.assertFalse(any(root for _,_,root in self.state['calls']))

    def test_unexpected_tenant_admission_fails_but_cleans_known_token_and_data(self):
        self.state['mode']='tenant-admitted';r=self.play();self.assertNotEqual(r.returncode,0)
        result=json.loads((self.evidence/'result.json').read_text())
        self.assertFalse(result['testsPassed']);self.assertTrue(result['exactTokenRevoked'] and result['exactDummyKeysDestroyed'])
        self.assert_token_rejected();self.assert_data_gone()

    def test_cleanup_interruption_is_reported_and_token_still_revoked(self):
        self.state['mode']='cleanup-fails';r=self.play();self.assertNotEqual(r.returncode,0)
        result=json.loads((self.evidence/'result.json').read_text())
        self.assertTrue(result['testsPassed']);self.assertTrue(result['exactTokenRevoked']);self.assertFalse(result['exactDummyKeysDestroyed'])
        self.assert_token_rejected()
        self.assertEqual(self.engine.call('GET','/platform/metadata/'+self.key).json()['data']['custom_metadata']['perkforge-test-id'],self.ident)

    def test_uncertain_issuance_never_claims_revocation_or_enumerates_tokens(self):
        self.state['mode']='uncertain-issuance';r=self.play();self.assertNotEqual(r.returncode,0)
        result=json.loads((self.evidence/'result.json').read_text())
        self.assertFalse(result['exactTokenRevoked']);self.assertTrue(result['exactDummyKeysDestroyed'])
        self.assertTrue((self.evidence/'issuance-started.json').exists())
        self.assertFalse(any('accessors' in path for _,path,_ in self.state['calls']))
        # Fixture knows its synthetic response; production must not recover it by scanning.
        for token in self.state['issued']:
            self.engine.call('POST','/auth/token/revoke-accessor',{'accessor':token['accessor']})
