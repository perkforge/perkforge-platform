"""Full Bash orchestration in a temp directory with mocked OS/service commands.

Not RHEL/sshd integration: root gate and absolute paths are adapted; no real
service, socket, SELinux or network operations occur. Public data is RFC8032.
"""
import base64
import os
from pathlib import Path
import stat
import struct
import subprocess
import tempfile
import unittest

SOURCE = Path(__file__).with_name('enroll-key.sh')

class Flow(unittest.TestCase):
    def run_flow(self, wrong_policy=False, sockets='', units=None, prior=False):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            home = root / 'home/operator'
            configdir = root / 'etc/ssh/sshd_config.d'
            bindir = root / 'bin'
            for path in (home, configdir, bindir):
                path.mkdir(parents=True)
            (root / 'state').write_text('inactive\n')
            (root / 'events').write_text('')
            (root / 'sockets').write_text(sockets)
            (root / 'units').write_text(units or 'sshd.service enabled enabled\nsshd.socket disabled disabled\ndbus.socket static -\n')
            wire = struct.pack('>I', 11) + b'ssh-ed25519' + struct.pack('>I', 32) + bytes.fromhex('d75a980182b10ab7d54bfed3c964073a0ee172f3daa62325af021a68f707511a')
            public = 'ssh-ed25519 ' + base64.b64encode(wire).decode() + ' RFC8032-public-test-vector\n'
            key = root / 'key.pub'
            key.write_text(public)
            auth = home / '.ssh/authorized_keys'
            if prior:
                auth.parent.mkdir()
                auth.write_text('# retain preexisting authorization\n')
            mocks = {
                'getent': f"printf 'operator:x:{os.getuid()}:{os.getgid()}:Fixture:{home}:/bin/bash\\n'",
                'ss': 'exit 0',
                'restorecon': 'exit 0',
                'systemctl': '''case "$1" in
is-active) cat "$TESTROOT/state"; grep -qx active "$TESTROOT/state" || exit 3;;
list-units) cat "$TESTROOT/sockets";;
list-unit-files) cat "$TESTROOT/units";;
start) echo start >> "$TESTROOT/events"; echo active > "$TESTROOT/state";;
stop) echo stop >> "$TESTROOT/events"; echo inactive > "$TESTROOT/state";;
*) exit 99;; esac''',
                'sshd': '''if [ "$1" = -t ]; then exit 0; fi
[ "$1" = -T ] || exit 99
[ -f "$TESTROOT/etc/ssh/sshd_config.d/00-perkforge-console-key.conf" ] || exit 98
cat <<POLICY
pubkeyauthentication yes
authenticationmethods publickey
passwordauthentication ${POLICY_PASSWORD}
kbdinteractiveauthentication no
permitrootlogin no
usepam yes
authorizedkeysfile .ssh/authorized_keys .ssh/authorized_keys2
POLICY''',
            }
            for name, body in mocks.items():
                target = bindir / name
                target.write_text('#!/bin/bash\nset -eu\n' + body + '\n')
                target.chmod(0o700)
            text = SOURCE.read_text()
            text = text.replace('export PATH=/usr/sbin:/usr/bin:/sbin:/bin', f'export PATH={bindir}:/usr/bin:/bin')
            text = text.replace('[[ $EUID == 0 ]]', '[[ 1 == 1 ]]')
            text = text.replace('/home/', str(root / 'home') + '/')
            text = text.replace('/etc/ssh/', str(root / 'etc/ssh') + '/')
            script = root / 'fixture.sh'
            script.write_text(text)
            result = subprocess.run(['bash', str(script), str(key), '192.0.2.1'], capture_output=True, text=True,
                                    env={**os.environ, 'SUDO_USER': 'operator', 'TESTROOT': str(root), 'POLICY_PASSWORD': 'yes' if wrong_policy else 'no'})
            return {'result': result, 'state': (root / 'state').read_text().strip(),
                    'events': (root / 'events').read_text(),
                    'auth': auth.read_text() if auth.exists() else None,
                    'public': public.strip(),
                    'mode': stat.S_IMODE(auth.stat().st_mode) if auth.exists() else None,
                    'config': (configdir / '00-perkforge-console-key.conf').read_text() if (configdir / '00-perkforge-console-key.conf').exists() else None}

    def test_success_preserves_keys_and_starts_only_after_validation(self):
        evidence = self.run_flow(prior=True)
        self.assertEqual(evidence['result'].returncode, 0, evidence['result'].stderr)
        self.assertIn('Key enrolled;', evidence['result'].stdout)
        self.assertIn('# retain preexisting authorization', evidence['auth'])
        self.assertIn(evidence['public'], evidence['auth'])
        self.assertEqual(evidence['mode'], 0o600)
        self.assertIn('PasswordAuthentication no', evidence['config'])
        self.assertEqual(evidence['state'], 'active')
        self.assertEqual(evidence['events'], 'start\n')

    def test_policy_failure_never_starts_service(self):
        evidence = self.run_flow(wrong_policy=True)
        self.assertNotEqual(evidence['result'].returncode, 0)
        self.assertIn('Effective policy differs', evidence['result'].stderr)
        self.assertEqual(evidence['state'], 'inactive')
        self.assertNotIn('start', evidence['events'])

    def test_real_enabled_tcp_socket_blocks_before_writes(self):
        evidence = self.run_flow(units='sshd.service enabled enabled\nsshd.socket enabled enabled\n')
        self.assertNotEqual(evidence['result'].returncode, 0)
        self.assertIsNone(evidence['auth'])
        self.assertIsNone(evidence['config'])
        self.assertEqual(evidence['events'], '')

    def test_description_only_match_demonstrates_overbroad_guard(self):
        evidence = self.run_flow(sockets='example.socket loaded active listening Example SSH helper\n')
        self.assertNotEqual(evidence['result'].returncode, 0)
        self.assertIn('Active or enabled SSH socket', evidence['result'].stderr)
        self.assertIsNone(evidence['auth'])

if __name__ == '__main__':
    unittest.main()
