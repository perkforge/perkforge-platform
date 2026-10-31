"""Whole hardening script flow with temp paths and mocked sshd/systemctl/SELinux."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

SOURCE = Path(__file__).with_name('harden-ssh.sh')

class Hardening(unittest.TestCase):
    def run_flow(self, password='no', existing=False, invalid=False):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config = root / '00-perkforge-key-only.conf'
            if existing:
                config.write_text('preserve existing\n')
            bindir = root / 'bin'
            bindir.mkdir()
            events = root / 'events'
            events.write_text('')
            commands = {
                'restorecon': 'exit 0',
                'systemctl': 'printf "%s\\n" "$*" >> "$EVENTS"',
                'sshd': '''if [ "$1" = -t ]; then exit "$SYNTAX_STATUS"; fi
[ "$1" = -T ] || exit 99
cat <<POLICY
pubkeyauthentication yes
authenticationmethods publickey
passwordauthentication $PASSWORD_POLICY
kbdinteractiveauthentication no
permitrootlogin no
usepam yes
POLICY''',
            }
            for name, body in commands.items():
                path = bindir / name
                path.write_text('#!/bin/bash\nset -eu\n'+body+'\n')
                path.chmod(0o700)
            text = SOURCE.read_text().replace('[[ $EUID == 0 && $# == 2 ]]', '[[ 1 == 1 && $# == 2 ]]')
            text = text.replace('/etc/ssh/sshd_config.d/00-perkforge-key-only.conf', str(config))
            text = text.replace('/usr/sbin/sshd', str(bindir / 'sshd'))
            script = root / 'fixture.sh'
            script.write_text(text)
            result = subprocess.run(['bash', str(script), 'operator', '192.0.2.1'], capture_output=True, text=True,
                env={**os.environ, 'PATH':str(bindir)+':/usr/bin:/bin', 'EVENTS':str(events),
                     'PASSWORD_POLICY':password, 'SYNTAX_STATUS':'1' if invalid else '0'})
            return result, events.read_text(), config.read_text()

    def test_valid_policy_reloads(self):
        result, events, config = self.run_flow()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(events, 'reload sshd.service\n')
        self.assertIn('PasswordAuthentication no', config)

    def test_effective_password_policy_mismatch_never_reloads(self):
        result, events, _ = self.run_flow(password='yes')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('effective policy differs', result.stderr)
        self.assertEqual(events, '')

    def test_invalid_syntax_never_reloads(self):
        result, events, _ = self.run_flow(invalid=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(events, '')

    def test_existing_config_not_overwritten(self):
        result, events, config = self.run_flow(existing=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(events, '')
        self.assertEqual(config, 'preserve existing\n')

if __name__ == '__main__':
    unittest.main()
