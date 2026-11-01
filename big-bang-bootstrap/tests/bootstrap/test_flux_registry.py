"""Synthetic credential delivery; never reads operator files or contacts a cluster."""
import base64
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
import yaml

ROOT = Path(__file__).resolve().parents[2]


class FluxRegistryTests(unittest.TestCase):
    def test_bootstrap_default_and_check_mode_do_not_read_credentials_or_call_api(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            cli = root / 'kubectl'
            cli.write_text('#!/bin/sh\nexit 91\n'); cli.chmod(0o700)
            env = {**os.environ, 'PATH': str(root)+':'+os.environ['PATH'],
                   'ANSIBLE_LOCAL_TEMP': str(root/'local'), 'ANSIBLE_REMOTE_TEMP': str(root/'remote')}
            args = ['ansible-playbook', '-i', str(ROOT/'configuration/ansible/inventory.yaml'),
                    str(ROOT/'configuration/ansible/bootstrap.yaml'), '-e', json.dumps({
                        'bootstrap_registry_apply': True, 'registry_credential_file': '/absent/credential'})]
            for options in [[], ['--check', '-e', 'bootstrap_apply=true']]:
                result = subprocess.run(args+options, capture_output=True, text=True, env=env, timeout=30)
                self.assertEqual(result.returncode, 0, result.stdout+result.stderr)
                self.assertNotIn('rc": 91', result.stdout)

    def test_create_reuse_and_fail_closed_without_disclosing_credentials(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            credential = root/'credential'; credential.write_text('synthetic-registry-token'); credential.chmod(0o600)
            state = root/'state.json'
            cli = root/'kubectl'
            cli.write_text('''#!/usr/bin/env python3
import json,os,sys,base64
from pathlib import Path
p=Path(os.environ['FLUX_REGISTRY_STATE']);s=json.loads(p.read_text());a=sys.argv[1:]
if a[0]=='--kubeconfig':a=a[4:]
s['calls'].append(a)
if a[0]=='kustomize':print('apiVersion: v1\\nkind: Namespace\\nmetadata:\\n  name: flux-system')
elif a[0]=='apply':
 obj=json.load(sys.stdin);assert obj['kind']=='Namespace' and obj['metadata']['name']=='flux-system';print('namespace/flux-system unchanged')
elif a[:2]==['get','secret']:
 if s.get('secret'):print(json.dumps(s['secret']))
elif a[0]=='create':
 obj=json.load(sys.stdin);assert not s.get('secret');assert obj['metadata']=={'name':'private-registry','namespace':'flux-system'}
 s['secret']={**obj,'data':{'.dockerconfigjson':base64.b64encode(obj['stringData']['.dockerconfigjson'].encode()).decode()}}
 del s['secret']['stringData'];s['creates']+=1;print('secret/private-registry created')
else:raise SystemExit('Unexpected fixture invocation')
p.write_text(json.dumps(s))
'''); cli.chmod(0o700)
            env = {**os.environ, 'PATH': str(root)+':'+os.environ['PATH'],
                   'FLUX_REGISTRY_STATE': str(state), 'ANSIBLE_LOCAL_TEMP': str(root/'local'),
                   'ANSIBLE_REMOTE_TEMP': str(root/'remote')}
            play = root/'fixture.yaml'
            def reset(secret=None):
                state.write_text(json.dumps({'calls': [], 'creates': 0, 'secret': secret}))
            def run(deliver=False, path=None):
                play.write_text(yaml.safe_dump([{'hosts':'localhost','connection':'local','gather_facts':False,
                    'vars': {'bootstrap_registry_apply':deliver, 'registry_username':'synthetic-user',
                             'registry_credential_file': str(path or credential), 'target_kubeconfig':'/synthetic/config',
                             'target_context':'synthetic', 'flux_manifest_path':'/synthetic/pinned-flux'},
                    'tasks':[{'ansible.builtin.include_tasks':str(ROOT/'configuration/ansible/flux-registry.yaml')}]}]))
                result = subprocess.run(['ansible-playbook','-i','localhost,',str(play)],
                    capture_output=True,text=True,env=env,timeout=30)
                output = result.stdout+result.stderr
                for value in ['synthetic-registry-token',base64.b64encode(b'synthetic-user:synthetic-registry-token').decode()]:
                    self.assertNotIn(value, output)
                return result
            reset()
            result=run();self.assertNotEqual(result.returncode,0)
            self.assertEqual(json.loads(state.read_text())['creates'],0)
            result=run(True);self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            created=json.loads(state.read_text());self.assertEqual(created['creates'],1)
            auth=json.loads(base64.b64decode(created['secret']['data']['.dockerconfigjson']))['auths']['registry1.dso.mil']['auth']
            self.assertEqual(base64.b64decode(auth),b'synthetic-user:synthetic-registry-token')
            result=run(path=root/'absent');self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            self.assertEqual(json.loads(state.read_text())['creates'],1)
            result=run(True);self.assertNotEqual(result.returncode,0)
            self.assertEqual(json.loads(state.read_text())['creates'],1)
            for mode in [0o644, 0o600]:
                with self.subTest(mode=oct(mode)):
                    reset();credential.chmod(mode)
                    link=root/'credential-link'
                    if not link.exists():link.symlink_to(credential)
                    result=run(True,credential if mode==0o644 else link)
                    self.assertNotEqual(result.returncode,0)
                    self.assertEqual(json.loads(state.read_text())['creates'],0)
            reset();credential.write_text('   \n');credential.chmod(0o600)
            result=run(True);self.assertNotEqual(result.returncode,0)
            self.assertEqual(json.loads(state.read_text())['creates'],0)
            reset({'type':'Opaque','data':{}})
            result=run();self.assertNotEqual(result.returncode,0)
            self.assertEqual(json.loads(state.read_text())['creates'],0)

    def test_delivery_is_inside_release_and_target_guard_before_controller_apply(self):
        play=yaml.safe_load((ROOT/'configuration/ansible/bootstrap.yaml').read_text())[0]
        block=next(t['block'] for t in play['tasks'] if 'block' in t)
        names=[t.get('name','') for t in block]
        delivery=next(i for i,t in enumerate(block) if t.get('ansible.builtin.include_tasks')=='flux-registry.yaml')
        self.assertLess(names.index('Refuse unpublished or modified bootstrap code'),delivery)
        self.assertLess(names.index('Refuse a different cluster'),delivery)
        self.assertLess(delivery,names.index('Apply only the pinned Flux prerequisites'))
        inventory=yaml.safe_load((ROOT/'configuration/ansible/inventory.yaml').read_text())
        self.assertFalse(inventory['all']['children']['bootstrap_clusters']['vars']['bootstrap_registry_apply'])
