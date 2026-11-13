"""Native-shaped Mattermost API fixture; read-only context checks, never live access."""
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

ROOT = Path(__file__).resolve().parents[3]
PLAY = ROOT / 'big-bang-bootstrap/configuration/authorization/sso/mattermost/context/inspect.yaml'
T, C, U, H = (x * 26 for x in 'tcuh')


class MattermostContext(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.d = Path(self.tmp.name)
        self.d.chmod(0o700)
        subprocess.run(['openssl', 'req', '-x509', '-newkey', 'rsa:2048', '-nodes', '-days', '1',
                        '-subj', '/CN=localhost', '-addext', 'subjectAltName=DNS:localhost',
                        '-keyout', str(self.d / 'key'), '-out', str(self.d / 'ca')], check=True, capture_output=True)
        self.contract = dict(schema_version=1, context_id='portal', team_name='tenant-portal', channel_name='alerts',
                             team_id=T, channel_id=C, webhook_id=H, publisher_user_id=U,
                             team_members=[dict(user_id=U, roles='team_user')],
                             channel_members=[dict(user_id=U, roles='channel_user')])
        self.s = dict(calls=[], team=dict(id=T, name='tenant-portal', type='I', delete_at=0, allow_open_invite=False),
                      channel=dict(id=C, team_id=T, name='alerts', type='P', delete_at=0),
                      team_members=[dict(team_id=T, user_id=U, roles='team_user', delete_at=0)],
                      channel_members=[dict(channel_id=C, user_id=U, roles='channel_user')],
                      hook=dict(id=H, team_id=T, channel_id=C, user_id=U, delete_at=0, channel_locked=True))
        s = self.s
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args): pass
            def do_GET(self):
                s['calls'].append(('GET', self.path))
                status, data = 200, None
                if self.headers.get('Authorization') != 'Bearer fixture-secret-token': status, data = 403, {}
                elif s.get('redirect'): status, data = 302, {}
                else:
                    paths = {f'/api/v4/teams/{T}':'team', f'/api/v4/channels/{C}':'channel',
                             f'/api/v4/teams/{T}/members?page=0&per_page=200':'team_members',
                             f'/api/v4/channels/{C}/members?page=0&per_page=200':'channel_members',
                             f'/api/v4/hooks/incoming/{H}':'hook'}
                    data = s.get(paths.get(self.path))
                    if data is None: status, data = 404, {}
                self.send_response(status)
                self.send_header('Content-Type', 'application/json')
                if status == 302: self.send_header('Location', '/credential-leak')
                self.end_headers(); self.wfile.write(json.dumps(data).encode())
            def do_POST(self):
                s['calls'].append(('POST', self.path)); self.send_error(405)
            do_PUT = do_POST
            do_DELETE = do_POST
        self.server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ctx.load_cert_chain(self.d/'ca', self.d/'key')
        self.server.socket = ctx.wrap_socket(self.server.socket, server_side=True)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.addCleanup(self.server.server_close); self.addCleanup(self.server.shutdown)
        self.origin = f'https://localhost:{self.server.server_port}'
        (self.d/'token').write_text('fixture-secret-token'); (self.d/'token').chmod(0o600)
        self.v = dict(mattermost_context_inspect=True, mattermost_context_origin=self.origin,
                      mattermost_context_contract_file=str(self.d/'contract'), mattermost_context_token_file=str(self.d/'token'),
                      mattermost_context_ca_file=str(self.d/'ca'))

    def run_play(self, changes=None, success=True, check=False):
        (self.d/'contract').write_text(json.dumps(self.contract)); (self.d/'contract').chmod(0o600)
        p = subprocess.run(['ansible-playbook', str(PLAY), '-e', json.dumps(self.v | (changes or {}))] + (['--check'] if check else []),
                           capture_output=True, text=True, timeout=90,
                           env=dict(os.environ, KUBECONFIG='/dev/null', ANSIBLE_LOCAL_TEMP=str(self.d/'local'), ANSIBLE_REMOTE_TEMP=str(self.d/'remote')))
        self.assertEqual(p.returncode == 0, success, p.stdout+p.stderr)
        self.assertNotIn('fixture-secret-token',p.stdout+p.stderr)
        self.assertNotIn(H,p.stdout+p.stderr)
        self.assertTrue(all(m=='GET' for m,_ in self.s['calls']))
        return p

    def test_default_and_check_no_contact_or_private_input(self):
        self.run_play(dict(mattermost_context_inspect=False, mattermost_context_token_file='/missing'))
        self.run_play(dict(mattermost_context_token_file='/missing'),check=True)
        self.assertEqual(self.s['calls'],[])

    def test_exact_context_and_repeat(self):
        self.assertIn('changed=0',self.run_play().stdout)
        self.run_play()
        self.assertEqual(len(self.s['calls']),10)

    def test_foreign_public_deleted_or_invitable_context(self):
        original=copy.deepcopy(self.s)
        for key,field,value in [('team','name','tenant-other'),('team','type','O'),('team','allow_open_invite',True),
                                ('team','delete_at',42),('channel','team_id','x'*26),('channel','type','O'),('channel','delete_at',42)]:
            self.s.clear(); self.s.update(copy.deepcopy(original)); self.s[key][field]=value
            self.run_play(success=False)

    def test_membership_drift_role_escalation_and_truncation(self):
        original=copy.deepcopy(self.s)
        for key,value in [('team_members',[]),('channel_members',[]),
                          ('team_members',[dict(team_id=T,user_id=U,roles='team_user team_admin',delete_at=0)]),
                          ('channel_members',[dict(channel_id=C,user_id=U,roles='channel_user channel_admin')]),
                          ('channel_members',self.s['channel_members']*200),
                          ('channel_members',self.s['channel_members']+[dict(channel_id=C,user_id='x'*26,roles='channel_user')])]:
            self.s.clear(); self.s.update(copy.deepcopy(original)); self.s[key]=value
            self.run_play(success=False)

    def test_unlocked_foreign_or_deleted_webhook(self):
        original=copy.deepcopy(self.s['hook'])
        for field,value in [('channel_locked',False),('channel_locked','true'),('channel_id','x'*26),('user_id','x'*26),('team_id','x'*26),('delete_at',1)]:
            self.s['hook']=original | {field:value}
            self.run_play(success=False)

    def test_bad_input_fails_before_contact(self):
        original=copy.deepcopy(self.contract)
        for field,value in [('team_id','../foreign'),('webhook_id','x'*26+'\n'),('team_name','tenant-other'),('channel_name','../path')]:
            self.contract=original | {field:value}; self.run_play(success=False)
            self.assertEqual(self.s['calls'],[])
        self.contract=original
        self.run_play(dict(mattermost_context_origin='http://localhost'),success=False)
        (self.d/'token').chmod(0o644)
        self.run_play(success=False)
        self.assertEqual(self.s['calls'],[])

    def test_redirect_and_wrong_auth_are_denied(self):
        self.s['redirect']=True; self.run_play(success=False)
        self.assertNotIn(('GET','/credential-leak'),self.s['calls'])
        self.s['redirect']=False; (self.d/'token').write_text('wrong'); self.run_play(success=False)

    def test_missing_ca_and_wrong_hostname_are_denied(self):
        self.run_play(dict(mattermost_context_ca_file='/missing'),success=False)
        self.run_play(dict(mattermost_context_origin=self.origin.replace('localhost','127.0.0.1')),success=False)
        self.assertEqual(self.s['calls'],[])
