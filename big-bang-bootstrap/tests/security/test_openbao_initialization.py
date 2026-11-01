"""Synthetic command clients exercise the actual Ansible init/unseal sequence offline."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[3]
PLAY = ROOT / 'big-bang-bootstrap/configuration/ansible/openbao-initialize.yaml'

class OpenBaoInitialization(unittest.TestCase):
    def run_case(self, existing=False, apply=True):
        with tempfile.TemporaryDirectory(prefix='bao-init-test-') as directory:
            d = Path(directory); (d/'custody').mkdir(mode=0o700); (d/'bin').mkdir()
            # Only the synthetic test copy substitutes an isolated custody directory.
            play = PLAY.read_text().replace('/home/corey/src/perkforge-tmp-secrets', str(d/'custody'))
            (d/'play.yaml').write_text(play)
            fake = '''#!/usr/bin/python3
import json,os,sys
from pathlib import Path
p=Path(os.environ['BAO_TEST_STATE']);s=json.loads(p.read_text())
a=sys.argv[1:]
if Path(sys.argv[0]).name=='kubectl':print('synthetic-cluster');sys.exit()
assert '--connect-to' in a and '--cacert' in a and '--insecure' not in a
url=a[-1];body=sys.stdin.read()
if url.endswith('/sys/init') and '--request' not in a: out={'initialized':s['initialized']}
elif url.endswith('/sys/init'):
 assert not s['initialized'];assert json.loads(a[a.index('--data-binary')+1])=={'secret_shares':3,'secret_threshold':2}
 s['initialized']=True;s['init_count']+=1;out={'keys_base64':['SYNTHETIC_SHARE_ONE','SYNTHETIC_SHARE_TWO','SYNTHETIC_SHARE_THREE'],'root_token':'SYNTHETIC_ROOT_TOKEN'}
elif url.endswith('/sys/unseal'):
 assert json.loads(body)['key'] in ['SYNTHETIC_SHARE_ONE','SYNTHETIC_SHARE_TWO'];s['unseal_count']+=1;out={'sealed':s['unseal_count']<2}
elif url.endswith('/sys/health'):out={'initialized':s['initialized'],'sealed':s['unseal_count']<2,'standby':False}
elif url.endswith('/auth/token/lookup-self'):
 assert 'SYNTHETIC_ROOT_TOKEN' in body;out={'data':{'policies':['root']}}
else:raise AssertionError(url)
p.write_text(json.dumps(s));print(json.dumps(out))
'''
            for name in ['curl','kubectl']:
                (d/'bin'/name).write_text(fake); (d/'bin'/name).chmod(0o700)
            state=d/'state.json'; state.write_text(json.dumps({'initialized':existing,'init_count':0,'unseal_count':0}))
            (d/'inventory.yaml').write_text('bootstrap_clusters:\n  hosts:\n    local:\n      ansible_connection: local\n      deployment_environment: local\n')
            inputs={'openbao_initialize_apply':apply,'openbao_custody_run':'openbao-v0130-test','target_kubeconfig':'synthetic','target_context':'synthetic','expected_cluster_uid':'synthetic-cluster','platform_tls_bundle':str(d)}
            (d/'inputs.json').write_text(json.dumps(inputs))
            env=dict(os.environ, PATH=str(d/'bin')+':'+os.environ['PATH'],BAO_TEST_STATE=str(state),ANSIBLE_LOCAL_TEMP=str(d/'tmp'),ANSIBLE_REMOTE_TEMP=str(d/'remote-tmp'),ANSIBLE_NOCOLOR='1')
            result=subprocess.run(['ansible-playbook','-i',str(d/'inventory.yaml'),str(d/'play.yaml'),'-e','@'+str(d/'inputs.json')],env=env,capture_output=True,text=True,timeout=60)
            output=result.stdout+result.stderr
            self.assertNotIn('SYNTHETIC_ROOT_TOKEN',output);self.assertNotIn('SYNTHETIC_SHARE_ONE',output)
            final=json.loads(state.read_text())
            if apply and not existing:
                self.assertEqual(result.returncode,0,output)
                self.assertEqual(final['init_count'],1);self.assertEqual(final['unseal_count'],2)
                for file in (d/'custody').rglob('*'):
                    self.assertEqual(file.stat().st_mode & 0o777,0o700 if file.is_dir() else 0o600)
                response=json.loads(next((d/'custody').rglob('initialization-response.json')).read_text())
                self.assertNotIn('root_token',response)
            else:
                self.assertEqual(final['init_count'],0);self.assertEqual(final['unseal_count'],0)
                self.assertEqual(list((d/'custody').iterdir()),[])
                self.assertEqual(result.returncode != 0,existing and apply,output)
    def test_real_playbook_synthetic_success_keeps_values_private(self): self.run_case()
    def test_initialized_store_is_never_reinitialized(self): self.run_case(existing=True)
    def test_default_does_not_access_or_initialize(self): self.run_case(apply=False)
