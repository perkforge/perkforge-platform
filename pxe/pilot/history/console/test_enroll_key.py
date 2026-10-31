"""Offline rejection tests: no root, node, network, credential generation or writes."""
import pathlib
import subprocess
import tempfile
import unittest

SCRIPT = pathlib.Path(__file__).with_name('enroll-key.sh')

class Rejections(unittest.TestCase):
    def run_case(self, args, message):
        result = subprocess.run(['bash', str(SCRIPT), *args], capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(message, result.stderr)
        self.assertNotIn('Key enrolled;', result.stdout)

    def test_legacy_empty_filtered_query_reproduces_silent_errexit(self):
        script="set -e; systemctl() { return 1; }; enabled=$(systemctl list-unit-files --type=socket --state=enabled,enabled-runtime --no-legend); echo reached"
        result=subprocess.run(['bash','-c',script],capture_output=True,text=True)
        self.assertEqual(result.returncode,1)
        self.assertEqual(result.stdout,'')
        self.assertEqual(result.stderr,'')

    def test_empty_enabled_socket_list_does_not_abort(self):
        text = SCRIPT.read_text()
        snippet = text[text.index('unit_files=$('):text.index('if grep -Eiq')]
        mock = "systemctl() { printf 'sshd.service enabled enabled\\nexample.socket static -\\n'; };\n"
        result = subprocess.run(['bash', '-ec', mock + snippet + '\nprintf \"reached:%s\" \"$enabled_sockets\"'], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, 'reached:')

    def test_enabled_socket_is_retained_for_rejection(self):
        text = SCRIPT.read_text()
        snippet = text[text.index('unit_files=$('):text.index('if grep -Eiq')]
        mock = "systemctl() { printf 'sshd.socket enabled-runtime enabled\\n'; };\n"
        result = subprocess.run(['bash', '-ec', mock + snippet + '\nprintf \"%s\" \"$enabled_sockets\"'], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, 'sshd.socket')

    def test_usage(self):
        self.run_case([], 'Usage:')

    def test_invalid_address(self):
        self.run_case(['/nonexistent', '192.0.2.999'], 'Invalid IPv4 octet')
        self.run_case(['/nonexistent', 'host;echo'], 'Expected workstation IPv4')

    def test_missing_key(self):
        self.run_case(['/nonexistent', '192.0.2.1'], 'regular non-symlink')

    def test_reject_options_multiline_and_private_material(self):
        with tempfile.TemporaryDirectory() as directory:
            key = pathlib.Path(directory) / 'dummy.pub'
            for text in ['command="true" ssh-ed25519 AAAA\n',
                         'ssh-ed25519 AAAA\nssh-ed25519 AAAA\n',
                         '-----BEGIN OPENSSH PRIVATE KEY-----\n', '']:
                key.write_text(text)
                self.run_case([str(key), '192.0.2.1'], 'one Ed25519 public key')

    def test_symlink_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            link = pathlib.Path(directory) / 'link.pub'
            link.symlink_to('/etc/hosts')
            self.run_case([str(link), '192.0.2.1'], 'regular non-symlink')

    def test_invalid_key_encoding(self):
        with tempfile.TemporaryDirectory() as directory:
            key = pathlib.Path(directory) / 'dummy.pub'
            key.write_text('ssh-ed25519 AAAA dummy-only\n')
            self.run_case([str(key), '192.0.2.1'], 'Invalid public key')

if __name__ == '__main__':
    unittest.main()
