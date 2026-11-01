"""No live APIs: exercise verifier login sequence and actual UID-guarded cleanup."""
import base64
import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time
import unittest
from unittest.mock import patch
import urllib.error

ROOT=Path(__file__).resolve().parents[3]
FILES=ROOT/'big-bang-bootstrap/configuration/ansible'
spec=importlib.util.spec_from_file_location('headlamp_access',FILES/'files/verify-headlamp-access.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)

class Response(io.BytesIO):
    status=200
    def __enter__(self):return self
    def __exit__(self,*args):self.close()

class FakeHeadlamp:
    def __init__(self,principal,revoked=False):self.principal=principal;self.revoked=revoked;self.cookie=False;self.calls=[]
    def open(self,request,timeout):
        path=request.full_url.split('14466',1)[1];self.calls.append(path)
        def deny():raise urllib.error.HTTPError(request.full_url,403,'denied',{},None)
        if path=='/config':out={'clusters':[{'name':'synthetic'}]}
        elif path=='/':return Response(b'<html>Headlamp</html>')
        elif path.endswith('/set-token'):self.cookie=bool(json.loads(request.data)['token']);out={}
        elif path.endswith('/api/v1/namespaces?limit=1'):
            if self.revoked or not (self.cookie or request.get_header('Authorization')):deny()
            out={'kind':'NamespaceList','items':[]}
        elif path.endswith('/selfsubjectreviews'):
            out={'status':{'userInfo':{'username':self.principal,'uid':'synthetic-uid'}}}
        elif path.endswith('/selfsubjectaccessreviews'):
            out={'status':{'allowed':True}}
        else:raise AssertionError(path)
        return Response(json.dumps(out).encode())

class HeadlampAccess(unittest.TestCase):
    def fixture(self,d,lifetime=3600,subject=None):
        principal='system:serviceaccount:headlamp:headlamp-bootstrap-admin-synthetic';now=int(time.time())
        claims={'sub':subject or principal,'iat':now,'exp':now+lifetime,'kubernetes.io':{'serviceaccount':{'uid':'synthetic-uid'}}}
        encoded=base64.urlsafe_b64encode(json.dumps(claims).encode()).decode().rstrip('=');token='synthetic.'+encoded+'.not-a-signature'
        (d/'token.txt').write_text(token);(d/'token.txt').chmod(0o600)
        import datetime
        expires=datetime.datetime.fromtimestamp(claims['exp'],datetime.timezone.utc).isoformat()
        (d/'metadata.json').write_text(json.dumps({'principal':principal,'sa_uid':'synthetic-uid','expires':expires,'revoked':False}));(d/'metadata.json').chmod(0o600)
        return principal,token
    def test_cookie_login_and_revocation_without_secret_output(self):
        with tempfile.TemporaryDirectory() as directory:
            d=Path(directory);principal,token=self.fixture(d);capture=io.StringIO()
            with patch.object(module.urllib.request,'build_opener',return_value=FakeHeadlamp(principal)),contextlib.redirect_stdout(capture):module.verify(d,'access')
            self.assertNotIn(token,capture.getvalue());self.assertFalse(json.loads((d/'verification.json').read_text())['personalBrowserLoginObserved'])
            with patch.object(module.urllib.request,'build_opener',return_value=FakeHeadlamp(principal,True)),contextlib.redirect_stdout(capture):module.verify(d,'revoked')
            self.assertTrue(json.loads((d/'metadata.json').read_text())['revoked'])
    def test_wrong_subject_and_excessive_lifetime_stop_before_http(self):
        for args in [{'subject':'another-identity'},{'lifetime':7200}]:
            with self.subTest(args=args),tempfile.TemporaryDirectory() as directory:
                d=Path(directory);self.fixture(d,**args)
                with patch.object(module.urllib.request,'build_opener') as client,self.assertRaises(RuntimeError):module.verify(d,'access')
                client.assert_not_called()
    def cleanup(self,mismatch):
        with tempfile.TemporaryDirectory() as directory:
            d=Path(directory);(d/'bin').mkdir();state=d/'state.json';state.write_text(json.dumps({'uid':'replacement' if mismatch else 'ours','deleted':False}))
            fake='''#!/usr/bin/python3
import os,json,sys
from pathlib import Path
p=Path(os.environ['CLEANUP_STATE']);o=json.loads(p.read_text())
if 'delete' in sys.argv:o.update(uid='',deleted=True);p.write_text(json.dumps(o));print('deleted')
else:print(o['uid'],end='')
'''
            (d/'bin/kubectl').write_text(fake);(d/'bin/kubectl').chmod(0o700)
            import yaml
            play=[{'hosts':'localhost','gather_facts':False,'vars':{'target_kubeconfig':'synthetic','target_context':'synthetic','headlamp_access_name':'headlamp-bootstrap-admin-synthetic','headlamp_access_cleanup_failed':False,'access_cleanup':{'kind':'clusterrolebinding','uid':'ours'}},'tasks':[{'ansible.builtin.include_tasks':str(FILES/'headlamp-access-cleanup.yaml')}]}]
            (d/'play.yaml').write_text(yaml.safe_dump(play))
            env=dict(os.environ,PATH=str(d/'bin')+':'+os.environ['PATH'],CLEANUP_STATE=str(state),ANSIBLE_LOCAL_TEMP=str(d/'tmp'),ANSIBLE_REMOTE_TEMP=str(d/'remote'))
            p=subprocess.run(['ansible-playbook','-i','localhost,','-c','local',str(d/'play.yaml')],env=env,capture_output=True,text=True,timeout=45)
            self.assertEqual(p.returncode,0,p.stdout+p.stderr);self.assertEqual(json.loads(state.read_text())['deleted'],not mismatch)
    def test_cleanup_removes_only_recorded_uid(self):self.cleanup(False)
    def test_cleanup_preserves_replacement_uid(self):self.cleanup(True)
    def test_safe_default_never_needs_cluster_or_credentials(self):
        with tempfile.TemporaryDirectory() as directory:
            env=dict(os.environ,ANSIBLE_LOCAL_TEMP=directory,ANSIBLE_REMOTE_TEMP=directory)
            p=subprocess.run(['ansible-playbook','-i',str(FILES/'inventory.yaml'),str(FILES/'headlamp-access-smoke.yaml')],env=env,capture_output=True,text=True,timeout=30)
            self.assertEqual(p.returncode,0,p.stdout+p.stderr)
