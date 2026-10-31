"""Offline public-CA selection gates; never install trust on a test runner."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

PLAY = Path(__file__).resolve().parents[1] / 'playbooks/install-lab-ca-trust.yml'


class LabCATrustTests(unittest.TestCase):
    def test_default_check_and_wrong_fingerprint_never_select_trust_targets(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            cert = root/'root.crt'
            subprocess.run(['openssl','req','-new','-x509','-newkey','rsa:2048','-noenc',
                            '-subj','/CN=Synthetic Test CA','-days','1','-addext','basicConstraints=critical,CA:TRUE',
                            '-keyout',str(root/'synthetic.key'),'-out',str(cert)],
                           check=True,capture_output=True)
            cases = [({}, [], 0), ({'lab_ca_trust_apply': True}, ['--check'], 0),
                     ({'lab_ca_trust_apply': True, 'lab_ca_trust_workstation': True,
                       'lab_ca_public_file': str(cert), 'lab_ca_expected_fingerprint': 'deliberately-wrong',
                       'lab_ca_leaf_bundle': str(root)}, [], 2)]
            for values, flags, expected in cases:
                with self.subTest(values=values):
                    result = subprocess.run(['ansible-playbook','-i','localhost,',str(PLAY),
                                             '-e',json.dumps(values),*flags],
                                            capture_output=True,text=True,timeout=20,
                                            env={**os.environ,'ANSIBLE_LOCAL_TEMP':str(root/'local'),
                                                 'ANSIBLE_REMOTE_TEMP':str(root/'remote')})
                    self.assertEqual(result.returncode,expected,result.stdout+result.stderr)
                    self.assertNotIn('TASK [Copy only the public CA certificate]',result.stdout)
                    self.assertNotIn('changed: [localhost]',result.stdout)


if __name__ == '__main__': unittest.main()
