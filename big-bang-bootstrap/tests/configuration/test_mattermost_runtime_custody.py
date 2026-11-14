"""Synthetic exact-custody checks; never contacts a real cluster or vault."""
import base64
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
import yaml

ROOT = Path(__file__).resolve().parents[3]
MODULE = ROOT / 'big-bang-bootstrap/configuration/packages/mattermost/runtime'

class MattermostCustody(unittest.TestCase):
    def test_default_and_check_are_inert(self):
        for args in ([], ['--check', '-e', 'mattermost_runtime_activate=true']):
            result = subprocess.run(['ansible-playbook', '-i', 'localhost,', str(MODULE/'activate.yaml'), *args], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('changed=0', result.stdout)

    def test_exact_secret_retry_and_mismatch_are_redacted(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)
            binary = path/'kubectl'
            wrapper = path/'check.yaml'
            wrapper.write_text(yaml.safe_dump([{'hosts':'localhost','connection':'local','gather_facts':False,'vars':{'mm_expected':{'password':'synthetic-private-value'},'mm_allow_absent':False,'consumer':{'name':'mattermost-test','type':'Opaque','fields':{'password':'password'}}},'tasks':[{'ansible.builtin.include_tasks':str(MODULE/'verify-secret.yaml'),'no_log':True}]}]))
            for value, status in [('synthetic-private-value',0),('synthetic-wrong-value',2)]:
                payload={'type':'Opaque','data':{'password':base64.b64encode(value.encode()).decode()}}
                binary.write_text("#!/bin/sh\ncat <<'DATA'\n"+json.dumps(payload)+"\nDATA\n")
                binary.chmod(0o700)
                result=subprocess.run(['ansible-playbook','-i','localhost,',str(wrapper)],capture_output=True,text=True,env={**os.environ,'PATH':str(path)+':'+os.environ['PATH']})
                self.assertEqual(result.returncode,status,result.stdout+result.stderr)
                self.assertNotIn('synthetic-private-value',result.stdout+result.stderr)
                self.assertNotIn('synthetic-wrong-value',result.stdout+result.stderr)

if __name__ == '__main__': unittest.main()
