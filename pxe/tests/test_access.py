"""Shared access orchestration with mocked SSH; existing policy fixtures remain separate."""
import base64
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1] / 'transport'

class AccessTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='pxe-access-test-')
        self.addCleanup(self.tmp.cleanup)
        self.work = Path(self.tmp.name)
        self.pilot = self.work / 'pilot'
        self.pilot.mkdir(parents=True)
        shutil.copy2(ROOT / 'access.sh', self.pilot / 'access.sh')
        shutil.copy2(ROOT / 'harden-ssh.sh', self.pilot / 'harden-ssh.sh')
        self.run = self.work / 'trust'; self.run.mkdir(mode=0o700)
        self.key = self.work / 'existing-key'
        self.key.write_text('SYNTHETIC_PRIVATE_MUST_NOT_BE_TRANSFERRED')
        raw = b'\x00\x00\x00\x0bssh-ed25519\x00\x00\x00\x20' + b'\x01' * 32
        self.public = 'ssh-ed25519 ' + base64.b64encode(raw).decode()
        self.key.with_suffix('.pub').write_text(self.public+'\n')
        (self.run / 'known_hosts').write_text('192.0.2.11 '+self.public+'\n')
        (self.run / 'trust-confirmed.txt').write_text('synthetic physical match confirmed\n')
        for file in self.run.iterdir(): file.chmod(0o600)
        self.bin = self.work / 'bin';self.bin.mkdir()
        mock = self.bin / 'mock.py'
        mock.write_text('''#!/usr/bin/python3
import json,os,sys
from pathlib import Path
name=Path(sys.argv[0]).name;args=sys.argv[1:]
if name=='ssh-copy-id':stage='enrollment'
else:
 command=args[-1]
 stage='inspection' if 'Remote helper:' in command else 'sudo' if 'sudo -k' in command else 'policy'
 if stage=='inspection':
  data=sys.stdin.read()
  assert 'SYNTHETIC_PRIVATE' not in data
  assert 'SSH_POLICY' in data
  print('Hostname: '+('wrong-node' if os.environ['SCENARIO']=='hostname' else 'fixture-node'))
  print('User: operator')
  print('Remote helper: /tmp/perkforge-access-abcdefgh/harden-ssh.sh')
with open(os.environ['EVENTS'],'a') as out:out.write(json.dumps({'stage':stage,'args':args})+'\\n')
if stage==os.environ['SCENARIO']:sys.exit(12)
''');mock.chmod(0o700)
        for name in ['ssh','ssh-copy-id']:(self.bin / name).symlink_to(mock)

    def invoke(self,scenario='success',approved='approved'):
        return subprocess.run(['bash',str(self.pilot/'access.sh'),approved,'192.0.2.11','operator',
            str(self.key),'192.0.2.10',str(self.run),'fixture-node'],capture_output=True,text=True,
            env={**os.environ,'PATH':str(self.bin)+':'+os.environ['PATH'],
                 'SCENARIO':scenario,'EVENTS':str(self.work/'events')},timeout=15)

    def test_success_and_failure_boundaries(self):
        for scenario in ['success','enrollment','inspection','hostname','policy','sudo']:
            with self.subTest(scenario=scenario):
                self.setUp()
                result=self.invoke(scenario)
                self.assertEqual(result.returncode==0,scenario=='success',result.stdout+result.stderr)
                events=[json.loads(line) for line in (self.work/'events').read_text().splitlines()]
                stages=[x['stage'] for x in events]
                expected={'success':['enrollment','inspection','policy','sudo'],
                          'enrollment':['enrollment'],'inspection':['enrollment','inspection'],
                          'hostname':['enrollment','inspection'],'policy':['enrollment','inspection','policy'],
                          'sudo':['enrollment','inspection','policy','sudo']}[scenario]
                self.assertEqual(stages,expected)
                for event in events:
                    options=' '.join(event['args'])
                    self.assertIn('StrictHostKeyChecking=yes',options)
                    self.assertIn('ControlPath=none',options)
                    self.assertIn('UserKnownHostsFile='+str(self.run/'known_hosts'),options)
                    if event['stage']!='enrollment':
                        self.assertIn('PreferredAuthentications=publickey',options)
                        self.assertIn('PasswordAuthentication=no',options)
                summary=next(self.run.glob('access-output-*.summary.txt'))
                self.assertIn('Final stage: complete' if scenario=='success' else 'Exit status:',summary.read_text())
                self.assertEqual(summary.stat().st_mode & 0o777,0o600)
                for file in self.run.glob('access-output-*'):
                    self.assertNotIn('SYNTHETIC_PRIVATE',file.read_text())

    def test_refuse_missing_approval_or_wrong_pinned_host_before_network(self):
        denied=self.invoke(approved='not-approved')
        self.assertEqual(denied.returncode,2)
        self.assertFalse((self.work/'events').exists())
        (self.run/'known_hosts').write_text('192.0.2.12 '+self.public+'\n')
        wrong=self.invoke()
        self.assertEqual(wrong.returncode,2)
        self.assertFalse((self.work/'events').exists())
        self.assertFalse(list(self.run.glob('access-output-*')))

if __name__=='__main__':unittest.main()
