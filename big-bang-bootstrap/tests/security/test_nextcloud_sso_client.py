"""Real Ansible against an isolated HTTPS Keycloak fixture, never production."""
import copy
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import ssl
import subprocess
import tempfile
import threading
import unittest
from urllib.parse import urlsplit

ROOT=Path(__file__).resolve().parents[3]
PLAY=ROOT/'big-bang-bootstrap/configuration/authorization/sso/nextcloud/reconcile-client.yaml'
SUB='11111111-1111-1111-1111-111111111111'

class NextcloudClient(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.d=Path(self.tmp.name)
        subprocess.run(['openssl','req','-x509','-newkey','rsa:2048','-nodes','-days','1','-subj','/CN=localhost','-addext','subjectAltName=DNS:localhost','-keyout',str(self.d/'key'),'-out',str(self.d/'ca')],check=True,capture_output=True)
        self.s={'client':None,'roles':[],'scope':[],'members':[],'calls':[],'writes':[],'fail_role':False,'fail_enable':False}
        s=self.s
        basic=[{'name':'auth_time','protocol':'openid-connect','protocolMapper':'oidc-usersessionmodel-note-mapper','config':{'introspection.token.claim':'true','userinfo.token.claim':'true','id.token.claim':'true','access.token.claim':'true','user.session.note':'AUTH_TIME','claim.name':'auth_time','jsonType.label':'long'}}, {'name':'sub','protocol':'openid-connect','protocolMapper':'oidc-sub-mapper','config':{'introspection.token.claim':'true','access.token.claim':'true'}}]
        class Handler(BaseHTTPRequestHandler):
            def log_message(self,*args):pass
            def reply(self,status,value=None):
                self.send_response(status);self.send_header('Content-Type','application/json');self.end_headers()
                if value is not None:self.wfile.write(json.dumps(value).encode())
            def do_GET(self):
                p=urlsplit(self.path).path.removeprefix('/auth/admin/realms/perkforge');s['calls'].append(('GET',p))
                if self.headers.get('Authorization')!='Bearer fixture-operator-token':return self.reply(403,{})
                if p=='':return self.reply(200,{'realm':'perkforge','enabled':True,'attributes':{'perkforge-managed':'true','perkforge-purpose':'realm-foundation-v1'}})
                if p=='/client-scopes':return self.reply(200,[{'id':'basic-id','name':'basic','protocol':'openid-connect'}])
                if p=='/client-scopes/basic-id/protocol-mappers/models':return self.reply(200,basic)
                if p=='/clients':return self.reply(200,[] if s['client'] is None else [{'id':'nc-id','clientId':'nextcloud'}])
                if p=='/clients/nc-id':return self.reply(200,s['client'])
                if p=='/clients/nc-id/default-client-scopes':return self.reply(200,[{'id':'basic-id','name':'basic'}])
                if p=='/clients/nc-id/optional-client-scopes':return self.reply(200,[])
                if p=='/clients/nc-id/protocol-mappers/models':return self.reply(200,s['client']['protocolMappers'])
                if p=='/clients/nc-id/client-secret':return self.reply(200,{'value':'fixture-existing-client-secret'})
                if p=='/clients/nc-id/roles':return self.reply(200,s['roles'])
                if p.startswith('/clients/nc-id/roles/') and p.endswith('/users'):
                    role=p.split('/')[-2];return self.reply(200,[{'id':SUB}] if any(r['name']==role for r in s['members']) else [])
                if p.startswith('/clients/nc-id/roles/') and p.endswith('/groups'):return self.reply(200,[])
                if p.startswith('/clients/nc-id/roles/'):
                    roles=[r for r in s['roles'] if r['name']==p.rsplit('/',1)[1]];return self.reply(200 if roles else 404,roles[0] if roles else {})
                if p=='/clients/nc-id/scope-mappings':return self.reply(200,{})
                if p=='/clients/nc-id/scope-mappings/clients/nc-id':return self.reply(200,s['scope'])
                if p.startswith('/roles-by-id/'):return self.reply(200,[])
                if p=='/users/'+SUB:return self.reply(200,{'id':SUB,'enabled':True})
                if p.startswith('/users/'+SUB+'/role-mappings/clients/nc-id'):return self.reply(200,s['members'])
                return self.reply(404,{})
            def mutate(self):
                p=urlsplit(self.path).path.removeprefix('/auth/admin/realms/perkforge')
                data=json.loads(self.rfile.read(int(self.headers.get('Content-Length',0))))
                if self.headers.get('Authorization')!='Bearer fixture-operator-token':return self.reply(403,{})
                s['writes'].append((self.command,p))
                if p=='/clients':s['client']={**data,'id':'nc-id'};s['client'].pop('secret');return self.reply(201)
                if p=='/clients/nc-id/roles':
                    if s['fail_role'] and data['name']=='owner':return self.reply(503,{})
                    s['roles'].append({**data,'id':'role-'+data['name'],'clientRole':True,'containerId':'nc-id'});return self.reply(201)
                if p=='/clients/nc-id/scope-mappings/clients/nc-id':s['scope']=data;return self.reply(204)
                if p=='/clients/nc-id':
                    if set(data)!={'clientId','enabled'}:return self.reply(400,{})
                    s['client'].update(data)
                    return self.reply(503 if s['fail_enable'] else 204,{})
                if p=='/users/'+SUB+'/role-mappings/clients/nc-id':s['members']=data if self.command=='POST' else [];return self.reply(204)
                return self.reply(404,{})
            do_POST=mutate
            do_PUT=mutate
            do_DELETE=mutate
        self.server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
        context=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER);context.load_cert_chain(self.d/'ca',self.d/'key')
        self.server.socket=context.wrap_socket(self.server.socket,server_side=True)
        threading.Thread(target=self.server.serve_forever,daemon=True).start();self.addCleanup(self.server.server_close);self.addCleanup(self.server.shutdown)
        for name,value in [('token','fixture-operator-token'),('secret','fixture-existing-client-secret')]:
            (self.d/name).write_text(value);(self.d/name).chmod(0o600)
        self.v={'nextcloud_provisioning_approval':'own-client-role-jit-v1','nextcloud_client_run':True,'nextcloud_recovery_verified':True,'nextcloud_native_ready':True,
                'nextcloud_sso_origin':'https://files.example.test','nextcloud_sso_issuer':'https://localhost:'+str(self.server.server_port)+'/auth/realms/perkforge',
                'nextcloud_operator_token_file':str(self.d/'token'),'nextcloud_client_secret_file':str(self.d/'secret'),'nextcloud_ca_file':str(self.d/'ca')}
    def run_play(self,op='prepare',extra=None,success=True,check=False):
        v={**self.v,'nextcloud_client_operation':op,'nextcloud_client_approval':'nextcloud-client-'+op+'-v1',**(extra or {})}
        p=subprocess.run(['ansible-playbook',str(PLAY),'-e',json.dumps(v)]+(['--check'] if check else []),env=dict(os.environ,ANSIBLE_LOCAL_TEMP=str(self.d/'local'),ANSIBLE_REMOTE_TEMP=str(self.d/'remote')),capture_output=True,text=True,timeout=90)
        self.assertEqual(p.returncode==0,success,p.stdout+p.stderr)
        for secret in ['fixture-operator-token','fixture-existing-client-secret']:self.assertNotIn(secret,p.stdout+p.stderr)
        return p
    def test_default_check_and_approval_are_noncontacting(self):
        self.run_play(extra={'nextcloud_client_run':False});self.run_play(check=True)
        self.run_play(extra={'nextcloud_client_approval':'UNAPPROVED'},success=False)
        self.assertEqual(self.s['calls'],[])
    def test_interruption_repeat_membership_activation_and_independent_rollback(self):
        self.s['fail_role']=True;self.run_play(success=False)
        self.assertFalse(self.s['client']['enabled'])
        self.s['fail_role']=False;self.run_play();self.assertIn('changed=0',self.run_play().stdout)
        self.run_play('members',extra={'nextcloud_provisioning_approval':'own-client-role-jit-v1','nextcloud_subjects':[{'sub':SUB,'role':'owner'}]})
        self.assertEqual([r['name'] for r in self.s['members']],['owner'])
        self.v['nextcloud_subjects']=[{'sub':SUB,'role':'owner'}]
        self.s['fail_enable']=True;self.run_play('activate',success=False)
        self.s['fail_enable']=False;self.assertIn('changed=0',self.run_play('activate').stdout)
        self.run_play('members',extra={'nextcloud_provisioning_approval':'own-client-role-jit-v1','nextcloud_subjects':[{'sub':SUB,'role':'absent'}]},success=False)
        self.assertEqual(len(self.s['members']),1)
        self.run_play('members',extra={'nextcloud_provisioning_approval':'own-client-role-jit-v1','nextcloud_subjects':[{'sub':SUB,'role':'absent'}],'nextcloud_native_revoked_subjects':[SUB]})
        self.assertEqual(self.s['members'],[])
        self.run_play('rollback');self.assertFalse(self.s['client']['enabled'])
        self.assertIn('changed=0',self.run_play('rollback').stdout)
    def test_foreign_client_mapper_scope_and_unknown_role_refuse(self):
        self.run_play();client=copy.deepcopy(self.s['client'])
        for changes in [{'redirectUris':['https://foreign.test/callback']},{'attributes':{'perkforge-managed':'false'}}]:
            self.s['client']={**copy.deepcopy(client),**changes};before=len(self.s['writes'])
            self.run_play('activate',success=False);self.assertEqual(len(self.s['writes']),before)
        self.s['client']=copy.deepcopy(client)
        self.s['client']['protocolMappers'][0]['config']['included.client.audience']='foreign'
        before=len(self.s['writes']);self.run_play('activate',success=False);self.assertEqual(len(self.s['writes']),before)
        self.s['client']=client;self.s['roles'].append({'name':'unknown'})
        self.run_play('activate',success=False);self.assertEqual(len(self.s['writes']),before)
