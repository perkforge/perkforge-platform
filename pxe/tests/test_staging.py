"""Offline staging-script safety checks with mocked mutations only."""
import os
from pathlib import Path
import shlex
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1] / 'transport'
PLACEHOLDER = "'/ABSOLUTE/PATH/TO/rhel-10.2-x86_64-dvd.iso'"

class StagingTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='pxe-batch-safety-')
        self.addCleanup(self.tmp.cleanup)
        self.work = Path(self.tmp.name)
        self.parent = self.work / 'native-parent'
        self.parent.mkdir()
        self.iso = self.work / 'fixture.iso'
        self.iso.write_text('dummy, not real media')
        self.log = self.work / 'mock-mutations'
        self.bin = self.work / 'bin'
        self.bin.mkdir()
        self.env = {**os.environ, 'PATH': str(self.bin) + ':' + os.environ['PATH'],
                    'MOCK_LOG': str(self.log), 'BASH_ENV': '/dev/null'}
        self.env.pop('PXE_ISO', None)
        scripts = {
            'stat': '#!/bin/sh\nprintf "0:0:755\\n"\n',
            'sha256sum': '#!/bin/sh\nexit "${MOCK_HASH_STATUS:-0}"\n',
            'getent': '#!/bin/sh\nexit "${MOCK_GETENT_STATUS:-0}"\n',
            'python3': '#!/bin/sh\nexit 0\n',
            'sudo': '''#!/bin/sh
case "$1" in
  test) shift; exec /usr/bin/test "$@" ;;
  stat) printf '0:0:700\\n'; exit 0 ;;
  find)
    if [ "${MOCK_FIND_STATUS:-0}" != 0 ]; then exit "$MOCK_FIND_STATUS"; fi
    if [ "${MOCK_FIND_NONEMPTY:-0}" = 1 ]; then printf 'fixture-existing-file\\n'; fi
    exit 0 ;;
  *) printf '%s\\n' "$*" >> "$MOCK_LOG"; exit 73 ;;
esac
'''}
        for name, data in scripts.items():
            path = self.bin / name
            path.write_text(data)
            path.chmod(0o700)

    def run_standalone(self, iso=None, **environment):
        source = (ROOT / 'stage-media.sh').read_text().replace('/srv', str(self.parent))
        self.assertNotIn('/srv', source)
        script_path = self.work / 'stage-media-fixture.sh'
        script_path.write_text(source)
        argument = self.iso if iso is None else iso
        caller = ('set -euo pipefail\n'
            + 'if BASH_ENV=/dev/null bash --noprofile --norc '
            + shlex.quote(str(script_path)) + ' ' + shlex.quote(str(argument))
            + '; then :; else pxe_status=$?; printf "Batch B exited %s; inspect before retrying.\\n" "$pxe_status" >&2; fi\n'
            + "printf '%s\\n' CALLER_SURVIVED\n")
        return subprocess.run(['bash', '--noprofile', '--norc'], input=caller, text=True,
            capture_output=True, timeout=15, env={**self.env, **environment})

    def test_standalone_parses_and_retains_fail_closed_guards(self):
        source = (ROOT / 'stage-media.sh').read_text()
        check = subprocess.run(['bash', '-n'], input=source, text=True, capture_output=True)
        self.assertEqual(check.returncode, 0, check.stderr)
        self.assertIn('set -Eeuo pipefail', source)
        self.assertIn('trap ', source)
        self.assertIn('sha256sum --check --status', source)
        self.assertIn('sudo find -P', source)
        self.assertNotRegex(source, r'(?m)^\s*(?:sudo\s+)?mount\s')

    def test_standalone_guards_stop_before_writes_and_preserve_caller(self):
        base = self.parent / 'perkforge-pxe-pilot'
        (base / 'http/rhel-10.2').mkdir(parents=True)
        (base / 'tftp').mkdir()
        for argument, environment, label in [
            ('', {}, 'explicit absolute ISO argument'),
            (self.iso, {'MOCK_HASH_STATUS': '41'}, 'ISO SHA-256 match'),
            (self.iso, {'MOCK_FIND_STATUS': '43'}, 'HTTP/TFTP staging trees must be empty'),
            (self.iso, {'MOCK_FIND_NONEMPTY': '1'}, 'HTTP/TFTP staging trees must be empty')]:
            result = self.run_standalone(iso=argument, **environment)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn('CALLER_SURVIVED', result.stdout)
            self.assertIn(label, result.stderr)
            self.assertIn('Batch B exited ', result.stderr)
            self.assertNotIn('completed. STOP', result.stdout)
            self.assertFalse(self.log.exists())

    def test_standalone_extraction_failure_does_not_copy_or_normalize(self):
        base = self.parent / 'perkforge-pxe-pilot'
        (base / 'http/rhel-10.2').mkdir(parents=True)
        (base / 'tftp').mkdir()
        result = self.run_standalone()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('CALLER_SURVIVED', result.stdout)
        self.assertIn('WRITE SECTION: approved non-mount extraction', result.stderr)
        self.assertIn('exited 73', result.stderr)
        calls = self.log.read_text().splitlines()
        self.assertEqual(len(calls), 1)
        self.assertTrue(calls[0].startswith('xorriso '))
        self.assertEqual(list((base / 'http/rhel-10.2').iterdir()), [])
        self.assertEqual(list((base / 'tftp').iterdir()), [])

if __name__ == '__main__':
    unittest.main()
