"""Host selection gates refuse connections outside the reviewed live stage."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

PLAY = Path(__file__).resolve().parents[1] / 'playbooks/prepare-longhorn-hosts.yml'


class LonghornHostPreparationTests(unittest.TestCase):
    def test_default_check_and_unreviewed_apply_never_contact_hosts(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            marker = root / 'contacted'
            ssh = root / 'ssh'
            ssh.write_text('#!/bin/sh\ntouch "' + str(marker) + '"\nexit 99\n')
            ssh.chmod(0o700)
            inventory = root / 'inventory.yml'
            inventory.write_text('all:\n  children:\n    rke2_agents:\n      hosts:\n        worker-1:\n        worker-2:\n    rke2_servers:\n      hosts:\n        control-1:\n')
            cases = [([], 0), (['--check', '-e', 'longhorn_host_prepare_apply=true'], 0),
                     (['-e', 'longhorn_host_prepare_apply=true'], 2)]
            for flags, expected in cases:
                with self.subTest(flags=flags):
                    result = subprocess.run(
                        ['ansible-playbook', '-i', str(inventory), str(PLAY), *flags],
                        capture_output=True, text=True, timeout=20,
                        env={**os.environ, 'PATH': directory + ':' + os.environ['PATH'],
                             'ANSIBLE_LOCAL_TEMP': directory + '/local',
                             'ANSIBLE_REMOTE_TEMP': directory + '/remote'})
                    self.assertEqual(result.returncode, expected, result.stdout + result.stderr)
                    self.assertFalse(marker.exists())


if __name__ == '__main__':
    unittest.main()
