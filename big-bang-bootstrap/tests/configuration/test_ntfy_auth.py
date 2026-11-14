"""Inactive auth source and opt-in isolated native credentials/ACL tests."""
import copy
import importlib.util
import json
from pathlib import Path
import unittest
import time
import jinja2
import yaml
from configuration import test_ntfy_deployment as deployment
BASE=Path(__file__).resolve().parents[2]/'configuration/packages/ntfy/auth'
spec=importlib.util.spec_from_file_location('ntfy_auth_inputs',BASE/'verify_inputs.py')
guard=importlib.util.module_from_spec(spec);spec.loader.exec_module(guard)
HASH='$2a$10$YLiO8U21sX1uhZamTLJXHuxgVC0Z/GKISibrKCLohPgtG7yIxSk4C'
def accounts():
    return [dict(username='fixture-publisher',kind='publisher',role='service',subject_id=None,
                 approved=True,topics=['tenant-portal-alerts'],password_hash=HASH,token='tk_'+'a'*29),
            dict(username='fixture-subscriber',kind='subscriber',role='tenant-developer',
                 subject_id='00000000-0000-0000-0000-000000000001',approved=True,
                 topics=['tenant-portal-alerts'],password_hash=HASH,token='tk_'+'b'*29)]
def entitlements():
    return {'fixture-publisher':dict(kind='publisher',role='service',topics=['tenant-portal-alerts']),
            '00000000-0000-0000-0000-000000000001':dict(kind='subscriber',role='tenant-developer',topics=['tenant-portal-alerts'])}
def verify(a,p,e,r):
    return guard.verify(a,p,e,r,entitlements())
def render(items):
    verify(items,[],[],[])
    e=jinja2.Environment(undefined=jinja2.StrictUndefined);e.filters['to_json']=json.dumps
    return yaml.safe_load(e.from_string((BASE/'native-auth.yaml.j2').read_text()).render(ntfy_accounts=items))
class NtfyAuth(unittest.TestCase):
    def test_empty_and_native_roles(self):
        self.assertEqual(render([]),{'auth-default-access':'deny-all','auth-users':[],'auth-access':[],'auth-tokens':[]})
        c=render(accounts())
        self.assertTrue(all(s.endswith(':user') for s in c['auth-users']))
        self.assertEqual(c['auth-access'],['fixture-publisher:tenant-portal-alerts:write-only','fixture-subscriber:tenant-portal-alerts:read-only'])
    def test_unsafe_inputs_rejected(self):
        changes=[dict(approved=False),dict(role='tenant-viewer'),dict(role='admin'),
                 dict(topics=['tenant-other-alerts']),dict(topics=['*']),dict(topics=['tenant-*']),dict(topics=['portal:rw']),
                 dict(topics=[]),dict(topics=['portal','portal']),dict(username='everyone'),
                 dict(username='bad:name'),dict(token='bad'),dict(password_hash='plaintext'),
                 dict(subject_id='unknown'),dict(extra='override')]
        for mutation in changes:
            a=accounts();a[1].update(mutation)
            with self.subTest(mutation=list(mutation)):
                with self.assertRaises(guard.InvalidInputs):verify(a,[],[],[])
    def test_duplicate_and_lifecycle_guards(self):
        a=accounts()
        with self.assertRaises(guard.InvalidInputs):verify(a+[a[0]],[],[],[])
        a[1]['token']=a[0]['token']
        with self.assertRaises(guard.InvalidInputs):verify(a,[],[],[])
        with self.assertRaises(guard.InvalidInputs):verify(accounts(),[],['fixture-publisher'],[])
        with self.assertRaises(guard.InvalidInputs):verify([],['old-user'],['old-user'],[])
        self.assertTrue(verify([],['old-user'],['old-user'],['old-user']))
        with self.assertRaises(guard.InvalidInputs):verify([],[],[],['wrong-user'])

class NativeNtfyAuth(deployment.NtfyDeployment):
    def native_config(self, config):
        return {**config,**render(accounts())}
    def native_checks(self,name,run):
        def request(token,topic,post=False,ok=True,status=403):
            args=['podman','exec',name,'wget','-S','-O-',
                  '--header=Authorization: Bearer '+token]
            if post:args+=['--post-data=synthetic-authorized-message']
            args+=['https://localhost:8443/'+topic+('' if post else '/json?poll=1')]
            result=run(*args,check=False)
            self.assertEqual(result.returncode==0,ok)
            if not ok:self.assertIn(str(status),result.stderr)
            return result.stdout
        pub,sub=accounts()
        request(pub['token'],'tenant-portal-alerts',post=True)
        self.assertIn('synthetic-authorized-message',request(sub['token'],'tenant-portal-alerts'))
        request(pub['token'],'tenant-portal-alerts',ok=False)
        request(sub['token'],'tenant-portal-alerts',post=True,ok=False)
        for a in accounts():
            request(a['token'],'tenant-other-alerts',post=True,ok=False)
            request(a['token'],'tenant-other-alerts',ok=False)

        # Native rotation against only this synthetic fixture DB. A replaced
        # declared token must not silently retain access after restart.
        info=json.loads(run('podman','inspect',name).stdout)[0]
        config_path=Path(next(m['Source'] for m in info['Mounts'] if m['Destination']=='/etc/ntfy/server.yml'))
        config=yaml.safe_load(config_path.read_text())
        rotated=accounts(); rotated[0]['token']='tk_'+'c'*29
        config.update(render(rotated))
        config_path.write_text(yaml.safe_dump(config))
        run('podman','restart',name)
        for _ in range(30):
            probe=run('podman','exec',name,'wget','-qO-','https://localhost:8443/v1/health',check=False)
            if probe.returncode==0:break
            time.sleep(1)
        self.assertEqual(probe.returncode,0)
        request(rotated[0]['token'],'tenant-portal-alerts',post=True)
        request(rotated[0]['token'],'tenant-portal-alerts',ok=False)
        request(rotated[0]['token'],'tenant-other-alerts',post=True,ok=False)
        request(pub['token'],'tenant-portal-alerts',post=True,ok=False,status=401)
        request(sub['token'],'tenant-portal-alerts')
        pub=rotated[0]

        # Native declarative offboarding against only this synthetic fixture DB.
        info=json.loads(run('podman','inspect',name).stdout)[0]
        config_path=Path(next(m['Source'] for m in info['Mounts'] if m['Destination']=='/etc/ntfy/server.yml'))
        config=yaml.safe_load(config_path.read_text())
        verify([pub], [pub['username'],sub['username']],
                     [pub['username'],sub['username']], [sub['username']])
        config.update(render([pub]))
        config_path.write_text(yaml.safe_dump(config))
        run('podman','restart',name)
        for _ in range(30):
            probe=run('podman','exec',name,'wget','-qO-','https://localhost:8443/v1/health',check=False)
            if probe.returncode==0:break
            time.sleep(1)
        self.assertEqual(probe.returncode,0)
        request(sub['token'],'tenant-portal-alerts',ok=False,status=401)
        request(pub['token'],'tenant-portal-alerts',post=True)
