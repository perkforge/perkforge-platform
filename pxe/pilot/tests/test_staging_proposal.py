"""Exercise Markdown child-shell failure handling with mocked mutations only."""
import os
from pathlib import Path
import re
import shlex
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
PLACEHOLDER = "'/ABSOLUTE/PATH/TO/rhel-10.2-x86_64-dvd.iso'"

class StagingProposalTests(unittest.TestCase):
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
        self.blocks = re.findall(r'```sh\n(.*?)```', (ROOT / 'STAGING-PROPOSAL.md').read_text(), re.S)
        self.assertEqual(len(self.blocks), 2)
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

    def run_block(self, index, iso=None, **environment):
        # Replace every native /srv reference before execution. All privileged
        # mutation commands are intercepted by sudo above and never delegated.
        body = self.blocks[index].replace('/srv', str(self.parent))
        body = body.replace(PLACEHOLDER, shlex.quote(str(self.iso if iso is None else iso)))
        self.assertNotIn('/srv', body)
        self.assertNotIn(' && ', body)
        script = 'set -euo pipefail\n' + body + "\nprintf '%s\\n' CALLER_SURVIVED\n"
        return subprocess.run(['bash', '--noprofile', '--norc'], input=script, text=True,
                              capture_output=True, timeout=15, env={**self.env, **environment})

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

    def assert_stopped(self, result, label):
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('CALLER_SURVIVED', result.stdout)
        self.assertIn(label, result.stderr)
        self.assertIn('failed (status ', result.stderr)
        self.assertNotIn('completed. STOP', result.stdout)
        self.assertFalse(self.log.exists(), 'No write-section command may run after a guard failure')

    def test_blocks_parse_and_keep_strict_options_inside_child(self):
        for block in self.blocks:
            self.assertTrue(block.startswith('if BASH_ENV=/dev/null bash '))
            self.assertIn("trap 'rc=$?;", block)
            self.assertNotIn('test -z "$(', block)
            result = subprocess.run(['bash', '-n'], input=block, text=True, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_missing_iso_and_hash_failure_leave_caller_alive_without_writes(self):
        for index in [0, 1]:
            with self.subTest(index=index, failure='missing path'):
                self.assert_stopped(self.run_block(index, iso=''), 'explicit absolute ISO argument')
            with self.subTest(index=index, failure='checksum'):
                self.assert_stopped(self.run_block(index, MOCK_HASH_STATUS='41'), 'ISO SHA-256 match')

    def test_existing_root_guard_is_not_skipped_by_and_list(self):
        (self.parent / 'perkforge-pxe-pilot').mkdir()
        self.assert_stopped(self.run_block(0), 'pilot root must not already exist')

    def test_failed_directory_scan_does_not_become_empty_success(self):
        base = self.parent / 'perkforge-pxe-pilot'
        (base / 'http/rhel-10.2').mkdir(parents=True)
        (base / 'tftp').mkdir()
        self.assert_stopped(self.run_block(1, MOCK_FIND_STATUS='43'), 'HTTP/TFTP staging trees must be empty')
        self.assert_stopped(self.run_block(1, MOCK_FIND_NONEMPTY='1'), 'HTTP/TFTP staging trees must be empty')

    def test_mutation_failure_does_not_run_later_mutations(self):
        result = self.run_block(0)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('CALLER_SURVIVED', result.stdout)
        self.assertIn('status 73', result.stderr)
        self.assertEqual(len(self.log.read_text().splitlines()), 1)
        self.assertTrue(self.log.read_text().startswith('mkdir -m0700 '))
        self.assertFalse((self.parent / 'perkforge-pxe-pilot').exists())

    def test_standalone_matches_reviewed_body_and_parses(self):
        source = (ROOT / 'stage-media.sh').read_text()
        body = source.split('# BEGIN REVIEWED BATCH B BODY\n', 1)[1].split('\n# END REVIEWED BATCH B BODY', 1)[0]
        reviewed = self.blocks[1].split("<<'PXE_BATCH_B'\n", 1)[1].split('\nPXE_BATCH_B\n', 1)[0]
        self.assertEqual(body, reviewed)
        check = subprocess.run(['bash', '-n'], input=source, text=True, capture_output=True)
        self.assertEqual(check.returncode, 0, check.stderr)
        self.assertNotIn('source ', source.replace('# Reviewed Batch B only. Do not source this file.', ''))

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
