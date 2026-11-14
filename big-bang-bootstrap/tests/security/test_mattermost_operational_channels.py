"""Real Ansible against disposable HTTPS; no live secrets or native writes."""
from http.server import BaseHTTPRequestHandler
from security import test_mattermost_bootstrap as bootstrap
from security import test_mattermost_membership as membership
from security import test_mattermost_context as fixture
import json

class OperationalChannels(fixture.MattermostFixture):
    def setUp(self):
        fixture.MattermostFixture.setUp(self)
        self.s["apply_fixture"] = True
        self.play=fixture.ROOT/'big-bang-bootstrap/configuration/authorization/sso/mattermost/channels/prepare.yaml'
        self.v.update(mattermost_channels_apply=True,mattermost_channels_approved=True,mattermost_bootstrap_receipt_file=str(self.d/'bootstrap-receipt.json'))
        (self.d/'bootstrap-receipt.json').write_text(json.dumps(dict(origin=self.origin,team_name='perkforge',operator_id='b'*26,ids=dict(team_id=fixture.T))))
        (self.d/'bootstrap-receipt.json').chmod(0o600)
        s=self.s;s['channels']={}
        class Handler(BaseHTTPRequestHandler):
            def log_message(self,*args):pass
            def reply(self,status,body):
                self.send_response(status);self.send_header('Content-Type','application/json');self.end_headers();self.wfile.write(json.dumps(body).encode())
            def do_GET(self):
                s['calls'].append(('GET',self.path))
                if self.path=='/api/v4/users/me':return self.reply(200,dict(id='b'*26,roles='system_user system_admin',delete_at=0))
                if self.path=='/api/v4/teams/'+fixture.T:return self.reply(200,dict(id=fixture.T,name='perkforge',type='I',delete_at=0,allow_open_invite=False))
                if '/channels/name/' in self.path:
                    obj=s['channels'].get(self.path.split('/')[-1]);return self.reply(200 if obj else 404,obj or {})
                if '/members/' in self.path:return self.reply(200,dict(user_id='b'*26,roles='channel_admin channel_user'))
                obj=next((c for c in s['channels'].values() if c['id']==self.path.split('/')[-1]),None)
                self.reply(200 if obj else 404,obj or {})
            def do_POST(self):
                s['calls'].append(('POST',self.path));body=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                assert self.path=='/api/v4/channels' and body['type']=='P'
                body.update(id=str(len(s['channels'])+1)*26,delete_at=0);s['channels'][body['name']]=body;self.reply(201,body)
        self.server.RequestHandlerClass=Handler
    def test_create_and_receipt_repeat(self):
        self.run_play();self.assertEqual(len(self.s['channels']),3);self.assertEqual(len([x for x in self.s['calls'] if x[0]=='POST']),3)
        self.s['calls']=[];self.run_play();self.assertTrue(all(m=='GET' for m,_ in self.s['calls']))
    def test_foreign_user_collision_stops_before_any_write(self):
        self.s['channels']['portal-deployments']=dict(id='x'*26,name='portal-deployments')
        self.run_play(success=False);self.assertTrue(all(m=='GET' for m,_ in self.s['calls']))
    def test_default_and_check_no_private_reads(self):
        self.run_play(dict(mattermost_channels_apply=False,mattermost_context_token_file='/missing'))
        self.run_play(dict(mattermost_context_token_file='/missing'),check=True);self.assertEqual(self.s['calls'],[])

class OperationalAudience(fixture.MattermostFixture):
    setUp = membership.MattermostMembership.setUp
    def test_platform_excludes_all_tenant_roles(self):
        self.contract.update(audience_model='operational-v1',context_id='platform',channel_name='platform-alerts')
        self.contract['groups']=[dict(id='platform-admins',path='/platform/admins'),dict(id='engineers',path='/platform/engineers')]
        for g in self.contract['groups']:
            self.s['extra_paths'][f"/admin/realms/perkforge/groups/{g['id']}"]=dict(g,subGroupCount=0,subGroups=[])
            self.s['extra_paths'][f"/admin/realms/perkforge/groups/{g['id']}/members?first=0&max=200&briefRepresentation=false"]=[dict(id='subject-one',enabled=True)]
        self.s['channel']['name']='platform-alerts'
        self.assertIn('0 additions, 0 removals',self.run_play().stdout)
        self.contract['groups'].append(dict(id='viewers',path='/tenants/portal/viewers'))
        self.run_play(success=False)

class InvitationPolicy(fixture.MattermostFixture):
    def setUp(self):
        super().setUp();self.play=fixture.ROOT/'big-bang-bootstrap/configuration/authorization/sso/mattermost/channels/invitation-policy.yaml'
        self.v.update(mattermost_invitation_apply=True,mattermost_invitation_approved=True,mattermost_channel_user_role_id='r'*26,mattermost_channel_user_permissions=['read_channel','manage_private_channel_members','manage_public_channel_members'])
        s=self.s;s['apply_fixture']=True;s['roles']={name:dict(id='r'*26 if name=='channel_user' else name,name=name,permissions=list(self.v['mattermost_channel_user_permissions'])) for name in ['channel_user','channel_admin','team_admin','system_admin']}
        class Handler(BaseHTTPRequestHandler):
            def log_message(self,*args):pass
            def reply(self,body):
                self.send_response(200);self.send_header('Content-Type','application/json');self.end_headers();self.wfile.write(json.dumps(body).encode())
            def do_GET(self):
                s['calls'].append(('GET',self.path));self.reply(s['roles'][self.path.split('/')[-1]])
            def do_PUT(self):
                s['calls'].append(('PUT',self.path));assert self.path=='/api/v4/roles/'+('r'*26)+'/patch'
                body=json.loads(self.rfile.read(int(self.headers['Content-Length'])));assert list(body)==['permissions'];s['roles']['channel_user']['permissions']=body['permissions'];self.reply(s['roles']['channel_user'])
        self.server.RequestHandlerClass=Handler
    def test_exact_removal_repeat_and_drift(self):
        self.run_play();self.assertNotIn('manage_private_channel_members',self.s['roles']['channel_user']['permissions']);self.assertIn('manage_public_channel_members',self.s['roles']['channel_user']['permissions'])
        self.s['calls']=[];self.run_play();self.assertTrue(all(m=='GET' for m,_ in self.s['calls']))
        self.s['roles']['channel_user']['permissions'].append('foreign');self.s['calls']=[];self.run_play(success=False);self.assertTrue(all(m=='GET' for m,_ in self.s['calls']))
    def test_confirmation_and_default(self):
        self.run_play(dict(mattermost_invitation_approved=False),success=False);self.assertEqual(self.s['calls'],[])
        self.run_play(dict(mattermost_invitation_apply=False,mattermost_context_token_file='/missing'));self.assertEqual(self.s['calls'],[])
