"""Offline issuance using synthetic passphrase input; no trust or live credentials."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
import yaml
ROOT = Path(__file__).resolve().parents[1]
PLAY = ROOT / 'playbooks/create-lab-pki.yml'


class LabPKITests(unittest.TestCase):
    def run_play(self, play, directory, flags):
        return subprocess.run(['ansible-playbook', '-i', 'localhost,', str(play), *flags],
                              capture_output=True, text=True, timeout=90,
                              env={**os.environ, 'ANSIBLE_LOCAL_TEMP': str(directory/'local'),
                                   'ANSIBLE_REMOTE_TEMP': str(directory/'remote')})

    def test_default_and_check_never_prompt_or_issue(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for flags in [[], ['--check', '-e', 'lab_pki_apply=true']]:
                result = self.run_play(PLAY, root, flags)
                self.assertEqual(result.returncode, 0, result.stdout+result.stderr)
                self.assertNotIn('New lab CA key passphrase (', result.stdout)
                self.assertEqual(list(root.glob('lab-pki-*')), [])

    def test_real_issuance_encrypts_root_and_limits_leaf_hostnames(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in ['playbooks', 'tasks', 'templates']:
                (root/name).mkdir()
            shutil.copy2(ROOT/'tasks/issue-lab-certificate.yml', root/'tasks')
            shutil.copy2(ROOT/'templates/lab-certificate.ext.j2', root/'templates')
            document = yaml.safe_load(PLAY.read_text())
            # Replace only interactive input; execute actual issuance/verification tasks.
            for task in document[0]['tasks'][-1]['block']:
                if 'ansible.builtin.pause' in task:
                    register = task.pop('register')
                    task.pop('ansible.builtin.pause')
                    task['ansible.builtin.set_fact'] = {register: {'user_input': 'synthetic-test-passphrase-only'}}
            fixture = root/'playbooks/create-lab-pki.yml'
            fixture.write_text(yaml.safe_dump(document))
            result = self.run_play(fixture, root, ['-e', 'lab_pki_apply=true', '-e', 'lab_pki_output_parent='+str(root)])
            self.assertEqual(result.returncode, 0, result.stdout+result.stderr)
            self.assertNotIn('synthetic-test-passphrase-only', result.stdout+result.stderr)
            bundles = list(root.glob('lab-pki-*'))
            self.assertEqual(len(bundles), 1)
            bundle = bundles[0]
            self.assertEqual(bundle.stat().st_mode & 0o777, 0o700)
            key = bundle/'root-ca.key.pem'
            self.assertTrue(key.read_text().startswith('-----BEGIN ENCRYPTED PRIVATE KEY-----'))
            denied = subprocess.run(['openssl', 'pkey', '-in', str(key), '-passin', 'stdin', '-noout'],
                                    input='wrong-synthetic-passphrase\n', capture_output=True, text=True)
            self.assertNotEqual(denied.returncode, 0)
            for app in ['headlamp', 'keycloak', 'rancher', 'openbao']:
                self.assertEqual((bundle/app/'tls.key').stat().st_mode & 0o777, 0o600)
                self.assertFalse((bundle/app/'request.csr').exists())
                denied = subprocess.run(['openssl', 'verify', '-CAfile', str(bundle/'root-ca.crt'),
                                         '-verify_hostname', 'unassigned.perkforge.home.arpa', str(bundle/app/'tls.crt')],
                                        capture_output=True, text=True)
                self.assertNotEqual(denied.returncode, 0)
                certkey = subprocess.check_output(['openssl','x509','-in',str(bundle/app/'tls.crt'),'-pubkey','-noout'])
                actualkey = subprocess.check_output(['openssl','pkey','-in',str(bundle/app/'tls.key'),'-pubout'])
                self.assertEqual(certkey,actualkey)
            self.assertFalse(yaml.safe_load((bundle/'summary.yml').read_text())['trust_installed'])

    def test_grafana_existing_ca_new_leaf_without_copying_signing_key(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); ca=root/'ca';ca.mkdir(mode=0o700)
            for name in ['playbooks','tasks','templates']:(root/name).mkdir()
            shutil.copy2(ROOT/'tasks/issue-lab-certificate.yml',root/'tasks')
            shutil.copy2(ROOT/'templates/lab-certificate.ext.j2',root/'templates')
            def ssl(*args):
                return subprocess.run(['openssl',*args],input='synthetic-grafana-passphrase\n',capture_output=True,text=True,check=True)
            ssl('req','-new','-x509','-newkey','rsa:2048','-days','730','-subj','/CN=Synthetic Existing CA',
                '-keyout',str(ca/'root-ca.key.pem'),'-out',str(ca/'root-ca.crt'),'-passout','stdin',
                '-addext','basicConstraints=critical,CA:TRUE,pathlen:0')
            (ca/'root-ca.key.pem').chmod(0o600)
            before=(ca/'root-ca.key.pem').read_bytes()
            fp=ssl('x509','-in',str(ca/'root-ca.crt'),'-fingerprint','-sha256','-noout').stdout.strip()
            doc=yaml.safe_load((ROOT/'playbooks/issue-grafana-certificate.yml').read_text())
            for task in doc[0]['tasks'][-1]['block']:
                if 'ansible.builtin.pause' in task:
                    task.pop('ansible.builtin.pause');name=task.pop('register')
                    task['ansible.builtin.set_fact']={name:{'user_input':'synthetic-grafana-passphrase'}}
            play=root/'playbooks/fixture.yml';play.write_text(yaml.safe_dump(doc))
            default=self.run_play(play,root,[]);self.assertEqual(default.returncode,0,default.stdout+default.stderr)
            checked=self.run_play(play,root,['--check','-e','grafana_certificate_apply=true']);self.assertEqual(checked.returncode,0,checked.stdout+checked.stderr)
            self.assertEqual(list(root.glob('grafana-pki-*')),[])
            import json
            inputs={'grafana_certificate_apply':True,'grafana_certificate_ca_bundle':str(ca),
                    'grafana_certificate_output_parent':str(root),'grafana_certificate_expected_ca_fingerprint':fp}
            result=self.run_play(play,root,['-e',json.dumps(inputs)])
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            self.assertNotIn('synthetic-grafana-passphrase',result.stdout+result.stderr)
            bundle=next(root.glob('grafana-pki-*'))
            self.assertFalse((bundle/'root-ca.key.pem').exists())
            self.assertEqual((ca/'root-ca.key.pem').read_bytes(),before)
            self.assertEqual((bundle/'grafana/tls.key').stat().st_mode & 0o777,0o600)
            ssl('verify','-CAfile',str(ca/'root-ca.crt'),'-verify_hostname','grafana.perkforge.home.arpa','-purpose','sslserver',str(bundle/'grafana/tls.crt'))
            inputs['grafana_certificate_expected_ca_fingerprint']='WRONG'
            refused=self.run_play(play,root,['-e',json.dumps(inputs)])
            self.assertNotEqual(refused.returncode,0)
            self.assertEqual(len(list(root.glob('grafana-pki-*'))),1)


if __name__ == '__main__': unittest.main()
