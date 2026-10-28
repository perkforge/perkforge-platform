"""Offline entrypoint safety checks; never contact libvirt or a guest."""
import os
from pathlib import Path
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[2]
ENTRY = ROOT / 'local-lab-big-bang/provision/prepare.sh'


class LocalProvisionTests(unittest.TestCase):
    def run_entry(self, mode):
        env = dict(os.environ)
        env.pop('LOCAL_TRIAL_APPROVED', None)
        return subprocess.run([str(ENTRY), mode], env=env, text=True,
                              capture_output=True)

    def test_preview_has_exact_deletion_scope(self):
        result = self.run_entry('plan')
        self.assertEqual(result.returncode, 0)
        for vm in ('cks-control', 'cks-worker'):
            self.assertIn(f'/home/corey/src/perkforge-platform/images/{vm}.qcow2', result.stdout)

    def test_actions_require_approval_before_any_tool(self):
        for mode in ('rhel', 'rke2'):
            result = self.run_entry(mode)
            self.assertEqual(result.returncode, 2)
            self.assertIn('Action-time approval required', result.stderr)

    def test_unknown_stage_fails(self):
        self.assertEqual(self.run_entry('destroy').returncode, 2)
