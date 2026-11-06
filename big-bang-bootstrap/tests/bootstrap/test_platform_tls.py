"""Synthetic TLS delivery and refusal tests; no live keys or Kubernetes API."""
import base64
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
import yaml
ROOT = Path(__file__).resolve().parents[2]


class PlatformTLSTests(unittest.TestCase):
    def test_delivery_redaction_key_validation_and_existing_resource_refusal(self):
        self.delivery_fixture("headlamp")

    def test_grafana_dedicated_namespace_public_readback_and_existing_refusal(self):
        self.delivery_fixture("grafana")

    def delivery_fixture(self, application):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); app = root/application; app.mkdir(mode=0o700)
            namespace_name = 'monitoring' if application == 'grafana' else application
            def openssl(*args):
                subprocess.run(['openssl',*args],check=True,capture_output=True)
            openssl('req','-new','-x509','-newkey','rsa:2048','-noenc','-days','2',
                    '-subj','/CN=Synthetic Test CA','-addext','basicConstraints=critical,CA:TRUE',
                    '-keyout',str(root/'root.key'),'-out',str(root/'root-ca.crt'))
            openssl('req','-new','-newkey','rsa:2048','-noenc','-subj','/CN='+application+'.perkforge.home.arpa',
                    '-keyout',str(app/'tls.key'),'-out',str(app/'request.csr'))
            (root/'extensions').write_text('basicConstraints=CA:FALSE\nextendedKeyUsage=serverAuth\nsubjectAltName=DNS:'+application+'.perkforge.home.arpa\n')
            openssl('x509','-req','-in',str(app/'request.csr'),'-CA',str(root/'root-ca.crt'),
                    '-CAkey',str(root/'root.key'),'-set_serial','42','-days','365',
                    '-extfile',str(root/'extensions'),'-out',str(app/'tls.crt'))
            (app/'tls.key').chmod(0o600)
            state = root/'state.json'; state.write_text(json.dumps({'resources':{},'creates':0,'calls':0}))
            cli = root/'kubectl'; cli.write_text('''#!/usr/bin/env python3
import base64,json,os,sys
from pathlib import Path
p=Path(os.environ['TLS_FIXTURE_STATE']);s=json.loads(p.read_text());a=sys.argv[1:];s['calls']+=1
if a[:2]==['get','namespace']:
 print(json.dumps({'metadata':{'name':os.environ['TLS_FIXTURE_NAMESPACE'],'labels':{'app.kubernetes.io/managed-by':'Ansible',**({'pod-security.kubernetes.io/enforce':'privileged','pod-security.kubernetes.io/enforce-version':'v1.36'} if os.environ['TLS_FIXTURE_NAMESPACE']=='monitoring' else {'app.kubernetes.io/component':'headlamp'})}}}))
elif a[0]=='get':
 if os.environ['TLS_FIXTURE_NAMESPACE']=='monitoring' and a[1]=='secret':
  assert a[-1] != 'json', 'Grafana readback must never return private key payload'
 key=a[1]+'/'+a[2];v=s['resources'].get(key)
 if v:print(json.dumps(v) if a[-1]=='json' else (v['type']+' '+v['data']['tls.crt'] if a[-1].startswith('jsonpath={.type}') else 'existing-uid'))
elif a[:3]==['create','secret','tls']:
 cert=Path(next(x.split('=',1)[1] for x in a if x.startswith('--cert='))).read_bytes()
 key=Path(next(x.split('=',1)[1] for x in a if x.startswith('--key='))).read_bytes()
 print(json.dumps({'kind':'Secret','metadata':{'name':a[3],'namespace':os.environ['TLS_FIXTURE_NAMESPACE']},'type':'kubernetes.io/tls','data':{'tls.crt':base64.b64encode(cert).decode(),'tls.key':base64.b64encode(key).decode()}}))
elif a[:2]==['create','configmap']:
 data=next(x[len('--from-file='):] for x in a if x.startswith('--from-file='));name,path=data.split('=',1)
 print(json.dumps({'kind':'ConfigMap','metadata':{'name':a[2],'namespace':os.environ['TLS_FIXTURE_NAMESPACE']},'data':{name:Path(path).read_text()}}))
elif a[:3]==['create','-f','-']:
 obj=json.load(sys.stdin);key=obj['kind'].lower()+'/'+obj['metadata']['name'];assert key not in s['resources'];s['resources'][key]=obj;s['creates']+=1;print('created')
else:raise SystemExit('Unexpected fixture invocation')
p.write_text(json.dumps(s))
''');cli.chmod(0o700)
            playdir=root/'configuration/ansible';playdir.mkdir(parents=True)
            namespace=playdir.parent/'packages/headlamp/prerequisites';namespace.mkdir(parents=True)
            shutil.copy2(ROOT/'configuration/packages/headlamp/prerequisites/namespace.yaml',namespace/'namespace.yaml')
            foundation=playdir.parent/'observability/metrics-prerequisites';foundation.mkdir(parents=True)
            shutil.copy2(ROOT/'configuration/observability/metrics-prerequisites/foundation.yaml',foundation/'foundation.yaml')
            play=playdir/'fixture.yaml';play.write_text(yaml.safe_dump([{'hosts':'localhost','connection':'local','gather_facts':False,
                'vars':{'platform_tls_bundle':str(root),'platform_tls_apply':True,'platform_tls_namespaces_apply':False,
                        'tls_application':application,'tls_cli':[str(cli)]},
                'tasks':[{'ansible.builtin.include_tasks':str(ROOT/'configuration/ansible/tasks/platform-tls-validate.yaml')},
                         {'ansible.builtin.include_tasks':str(ROOT/'configuration/ansible/tasks/platform-tls-application.yaml')}]}]))
            def run():
                result=subprocess.run(['ansible-playbook','-i','localhost,',str(play)],capture_output=True,text=True,timeout=30,
                    env={**os.environ,'TLS_FIXTURE_STATE':str(state),'TLS_FIXTURE_NAMESPACE':namespace_name,'ANSIBLE_LOCAL_TEMP':str(root/'local'),'ANSIBLE_REMOTE_TEMP':str(root/'remote')})
                self.assertNotIn((app/'tls.key').read_text(),result.stdout+result.stderr)
                return result
            result=run();self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            after=json.loads(state.read_text());self.assertEqual(after['creates'],1 if application == 'grafana' else 2)
            delivered=after['resources']['secret/'+application+'-local-tls']
            self.assertEqual(base64.b64decode(delivered['data']['tls.key']),(app/'tls.key').read_bytes())
            self.assertEqual(delivered['metadata']['namespace'],namespace_name)
            if application == 'headlamp':
                self.assertEqual(after['resources']['configmap/identity-ca']['data']['ca.crt'],(root/'root-ca.crt').read_text())
            result=run();self.assertNotEqual(result.returncode,0)
            self.assertEqual(json.loads(state.read_text())['creates'],1 if application == 'grafana' else 2)
            state.write_text(json.dumps({'resources':{},'creates':0,'calls':0}))
            shutil.copy2(root/'root.key',app/'tls.key');(app/'tls.key').chmod(0o600)
            result=run();self.assertNotEqual(result.returncode,0)
            self.assertEqual(json.loads(state.read_text())['calls'],0)


if __name__ == '__main__': unittest.main()
