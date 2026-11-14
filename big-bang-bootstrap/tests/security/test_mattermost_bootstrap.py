"""Real Ansible with synthetic HTTPS native API; never a real account/token."""
from http.server import BaseHTTPRequestHandler
import json
from security import test_mattermost_context as fixture

class NativeBootstrap(fixture.MattermostFixture):
    def setUp(self):
        super().setUp()
        self.play=fixture.ROOT/'big-bang-bootstrap/configuration/authorization/sso/mattermost/bootstrap/prepare.yaml'
        self.contract=dict(schema_version=1,subject='fixture-sub',subject_verified=True,username='fixture-owner',email='fixture@example.invalid',email_verified=False,operator_id='b'*26,operator_exception_approved=True,team_name='perkforge',channel_name='portal-alerts')
        self.v.update(mattermost_bootstrap_apply=True,mattermost_bootstrap_approved=True)
        self.s.update(apply_fixture=True,objects={},members={})
        s=self.s
        class Handler(BaseHTTPRequestHandler):
            def log_message(self,*args): pass
            def reply(self,status,data):
                self.send_response(status); self.send_header('Content-Type','application/json'); self.end_headers(); self.wfile.write(json.dumps(data).encode())
            def do_GET(self):
                s['calls'].append(('GET',self.path))
                if self.headers.get('Authorization')!='Bearer fixture-secret-token': return self.reply(403,{})
                if self.path=='/api/v4/users/me': return self.reply(200,dict(id='b'*26,roles='system_user system_admin',auth_service='',delete_at=0))
                if self.path.startswith('/api/v4/users/username/') or self.path.startswith('/api/v4/users/email/'): obj=s['objects'].get('user')
                elif self.path=='/api/v4/teams/name/perkforge': obj=s['objects'].get('team')
                elif self.path.endswith('/channels/name/portal-alerts'): obj=s['objects'].get('channel')
                else: obj=s['members'].get(self.path)
                self.reply(200 if obj else 404,obj or {})
            def do_POST(self):
                s['calls'].append(('POST',self.path)); body=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                if self.path=='/api/v4/users':
                    assert body['disable_welcome_email'] is True and body['roles']=='system_user' and body['email_verified'] is False
                    obj=dict(body,id=fixture.U,delete_at=0); s['objects']['user']=obj
                elif self.path=='/api/v4/teams':
                    obj=dict(body,id=fixture.T,delete_at=0); s['objects']['team']=obj
                    s['members'][f'/api/v4/teams/{fixture.T}/members/'+('b'*26)]=dict(user_id='b'*26,roles='team_user team_admin')
                elif self.path=='/api/v4/channels':
                    obj=dict(body,id=fixture.C,delete_at=0); s['objects']['channel']=obj
                    s['members'][f'/api/v4/channels/{fixture.C}/members/'+('b'*26)]=dict(user_id='b'*26,roles='channel_user channel_admin')
                else:
                    assert self.path.endswith('/members')
                    role='team_user' if '/teams/' in self.path else 'channel_user'
                    if '/teams/' in self.path: assert body['team_id']==fixture.T
                    obj=dict(body,roles=role,delete_at=0); s['members'][self.path+'/'+body['user_id']]=obj
                self.reply(201,obj)
        self.server.RequestHandlerClass=Handler
    def test_create_and_receipt_repeat(self):
        self.run_play(); self.assertEqual(len([x for x in self.s['calls'] if x[0]=='POST']),5)
        self.assertEqual((self.d/'bootstrap-receipt.json').stat().st_mode & 0o777,0o600)
        self.s['calls']=[]; self.run_play(); self.assertTrue(all(m=='GET' for m,_ in self.s['calls']))
    def test_foreign_user_collision_stops_before_any_write(self):
        self.s['objects']['user']=dict(id=fixture.U,username='fixture-owner',email='fixture@example.invalid',auth_service='email',auth_data='',roles='system_user',delete_at=0)
        self.run_play(success=False); self.assertTrue(all(m=='GET' for m,_ in self.s['calls']))
    def test_default_and_check_no_private_reads(self):
        self.run_play(dict(mattermost_bootstrap_apply=False,mattermost_context_token_file='/missing'))
        self.run_play(dict(mattermost_context_token_file='/missing'),check=True)
        self.assertEqual(self.s['calls'],[])
