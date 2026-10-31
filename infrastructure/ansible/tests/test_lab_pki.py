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


if __name__ == '__main__': unittest.main()
