"""Offline real-Ansible certificate issuance using disposable synthetic identities only."""
from pathlib import Path
import errno
import json
import os
import pty
import select
import shutil
import subprocess
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / 'configuration/packages/harbor'
SERVICES = ('harbor-core', 'harbor-portal', 'harbor-jobservice', 'harbor-registry', 'harbor-valkey')


@unittest.skipUnless(shutil.which('ansible-playbook') and shutil.which('openssl'), 'Ansible and OpenSSL required')
class HarborTransport(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='harbor-transport-fixture-')
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name)
        self.out = self.path / 'out'
        self.out.mkdir(mode=0o700)
        self.env = {**os.environ, 'ANSIBLE_LOCAL_TEMP': str(self.path / 'local'),
                    'ANSIBLE_REMOTE_TEMP': str(self.path / 'remote'), 'ANSIBLE_NOCOLOR': '1'}

    def ssl(self, *args, success=True):
        result = subprocess.run(['openssl', *map(str, args)], capture_output=True, text=True, timeout=30)
        if success:
            self.assertEqual(result.returncode, 0, result.stderr)
        return result

    def run_play(self, public=False, values=None, check=False, passphrase=None):
        name = 'prepare-public-certificate.yaml' if public else 'prepare-transport.yaml'
        variables = self.path / 'vars.json'
        variables.write_text(json.dumps(values or {}))
        variables.chmod(0o600)
        args = ['ansible-playbook', '-i', 'localhost,', str(PACKAGE / name), '-e', '@' + str(variables)]
        if check:
            args.append('--check')
        if passphrase is None:
            result = subprocess.run(args, env=self.env, capture_output=True, text=True, timeout=120)
            return result.returncode, result.stdout + result.stderr
        # Exercise the real hidden local pause prompt, without a production bypass variable.
        pid, fd = pty.fork()
        if pid == 0:
            os.execvpe(args[0], args, self.env)
        output = b''
        sent = False
        deadline = time.monotonic() + 120
        try:
            while time.monotonic() < deadline:
                if select.select([fd], [], [], 0.1)[0]:
                    try:
                        chunk = os.read(fd, 65536)
                    except OSError as exc:
                        if exc.errno == errno.EIO:
                            break
                        raise
                    if not chunk:
                        break
                    output += chunk
                    if not sent and b'Existing lab CA passphrase (local input only)' in output:
                        time.sleep(0.2)
                        os.write(fd, passphrase.encode() + b'\n')
                        sent = True
            else:
                os.kill(pid, 9)
                self.fail('Timed out waiting for synthetic Ansible issuance')
        finally:
            os.close(fd)
            _, status = os.waitpid(pid, 0)
        self.assertTrue(sent, output.decode(errors='replace'))
        return os.waitstatus_to_exitcode(status), output.decode(errors='replace')

    def internal_vars(self):
        return {'harbor_transport_run': True, 'harbor_transport_scope': 'harbor-internal-transport-issuance-v1',
                'harbor_transport_output_parent': str(self.out)}

    def public_vars(self, days='730'):
        ca = self.path / 'ca'
        ca.mkdir(mode=0o700)
        self.ssl('req', '-x509', '-newkey', 'rsa:2048', '-sha256', '-days', days,
                 '-subj', '/CN=Synthetic Disposable CA', '-addext', 'basicConstraints=critical,CA:TRUE,pathlen:0',
                 '-addext', 'keyUsage=critical,keyCertSign,cRLSign', '-passout', 'pass:fixture-only',
                 '-keyout', ca / 'root-ca.key.pem', '-out', ca / 'root-ca.crt')
        (ca / 'root-ca.key.pem').chmod(0o600)
        fingerprint = self.ssl('x509', '-in', ca / 'root-ca.crt', '-noout', '-fingerprint', '-sha256').stdout.strip()
        return {'harbor_public_certificate_run': True, 'harbor_public_certificate_scope': 'harbor-public-leaf-issuance-v1',
                'harbor_public_certificate_ca_bundle': str(ca),
                'harbor_public_certificate_expected_ca_fingerprint': fingerprint,
                'harbor_public_certificate_output_parent': str(self.out)}

    def assert_protected(self, bundle):
        for path in [bundle, *bundle.rglob('*')]:
            self.assertFalse(path.is_symlink())
            self.assertEqual(path.stat().st_mode & 0o777, 0o700 if path.is_dir() else 0o600, str(path))
        self.assertTrue((bundle / 'READY').is_file())
        self.assertNotIn('prepare.sh', [p.name for p in bundle.rglob('*')])

    def test_default_and_check_do_not_touch_unconfigured_private_inputs(self):
        for public in (False, True):
            prefix = 'harbor_public_certificate' if public else 'harbor_transport'
            for values, check in (({}, False), ({prefix + '_run': True}, True)):
                code, log = self.run_play(public, values, check)
                self.assertEqual(code, 0, log)
                self.assertIn('changed=0', log)
                self.assertEqual(list(self.out.iterdir()), [])

    def test_internal_scope_path_permissions_and_fresh_identities(self):
        values = self.internal_vars()
        for invalid in ({**values, 'harbor_transport_scope': 'wrong'},
                        {**values, 'harbor_transport_output_parent': str(self.out / '..' / 'out')}):
            code, _ = self.run_play(values=invalid)
            self.assertNotEqual(code, 0)
            self.assertEqual(list(self.out.iterdir()), [])
        link = self.path / 'out-link'
        link.symlink_to(self.out, target_is_directory=True)
        code, _ = self.run_play(values={**values, 'harbor_transport_output_parent': str(link)})
        self.assertNotEqual(code, 0)
        self.assertEqual(list(self.out.iterdir()), [])
        self.out.chmod(0o755)
        code, _ = self.run_play(values=values)
        self.assertNotEqual(code, 0)
        self.out.chmod(0o700)
        previous = None
        for _ in range(2):
            before = set(self.out.iterdir())
            code, log = self.run_play(values=values)
            self.assertEqual(code, 0, log)
            self.assertNotIn('BEGIN PRIVATE KEY', log)
            bundle, = set(self.out.iterdir()) - before
            self.assert_protected(bundle)
            delivery = bundle / 'delivery/internal'
            self.assertEqual({p.name for p in delivery.iterdir()}, {'ca.crt', *SERVICES})
            self.assertEqual(len(list((bundle / 'delivery').rglob('*.key'))), 5)
            for service in SERVICES:
                leaf = delivery / service / 'tls.crt'
                san = self.ssl('x509', '-in', leaf, '-noout', '-ext', 'subjectAltName').stdout
                self.assertEqual(san.splitlines()[1].strip(), ', '.join('DNS:' + n for n in
                                 (service, service + '.harbor.svc', service + '.harbor.svc.cluster.local')))
                self.assertNotEqual(self.ssl('verify', '-CAfile', delivery / 'ca.crt', '-verify_hostname',
                                            'wrong.harbor.svc', leaf, success=False).returncode, 0)
                self.assertNotEqual(self.ssl('verify', '-CAfile', delivery / 'ca.crt', '-purpose',
                                            'sslclient', leaf, success=False).returncode, 0)
            ca_bytes = (delivery / 'ca.crt').read_bytes()
            if previous:
                self.assertNotEqual(previous, ca_bytes)
            previous = ca_bytes
            # Re-executing the rendered shell refuses existing output instead of overwriting.
            before_key = (bundle / 'signer/ca.key').read_bytes()
            result = subprocess.run(['bash', str(PACKAGE / 'templates/harbor-internal-transport.sh.j2')],
                                    cwd=bundle, capture_output=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(before_key, (bundle / 'signer/ca.key').read_bytes())

    def test_public_encrypted_prompt_fingerprint_and_exact_leaf(self):
        values = self.public_vars()
        key = self.path / 'ca/root-ca.key.pem'
        original = key.read_bytes()
        for invalid in ({**values, 'harbor_public_certificate_scope': 'wrong'},
                        {**values, 'harbor_public_certificate_expected_ca_fingerprint': 'sha256 Fingerprint=' + ':'.join(['00'] * 32)}):
            code, _ = self.run_play(True, invalid)
            self.assertNotEqual(code, 0)
            self.assertEqual(list(self.out.iterdir()), [])
        saved = self.path / 'saved-ca.key'
        key.rename(saved)
        key.symlink_to(saved)
        code, _ = self.run_play(True, values)
        self.assertNotEqual(code, 0)
        self.assertEqual(list(self.out.iterdir()), [])
        key.unlink()
        saved.rename(key)
        key.chmod(0o644)
        code, _ = self.run_play(True, values)
        self.assertNotEqual(code, 0)
        key.chmod(0o600)
        code, log = self.run_play(True, values, passphrase='fixture-only')
        self.assertEqual(code, 0, log)
        self.assertNotIn('fixture-only', log)
        self.assertNotIn('BEGIN PRIVATE KEY', log)
        bundle, = self.out.iterdir()
        self.assert_protected(bundle)
        delivery = bundle / 'delivery/external'
        self.assertEqual({p.name for p in delivery.iterdir()}, {'ca.crt', 'tls.key', 'tls.crt'})
        self.assertEqual(key.read_bytes(), original)
        self.assertEqual(len(list(bundle.rglob('*.key'))), 1)
        san = self.ssl('x509', '-in', delivery / 'tls.crt', '-noout', '-ext', 'subjectAltName').stdout
        self.assertEqual(san.splitlines()[1].strip(), 'DNS:harbor.perkforge.home.arpa')
        self.assertNotEqual(self.ssl('verify', '-CAfile', delivery / 'ca.crt', '-verify_hostname',
                                    'grafana.perkforge.home.arpa', delivery / 'tls.crt', success=False).returncode, 0)

    def test_public_bad_passphrase_leaves_no_ready_marker_or_copied_signer(self):
        values = self.public_vars()
        key = self.path / 'ca/root-ca.key.pem'
        original = key.read_bytes()
        code, log = self.run_play(True, values, passphrase='intentionally-wrong')
        self.assertNotEqual(code, 0)
        self.assertNotIn('intentionally-wrong', log)
        bundle, = self.out.iterdir()
        self.assertFalse((bundle / 'READY').exists())
        self.assertFalse((bundle / 'prepare.sh').exists())
        self.assertFalse((bundle / 'delivery/external/root-ca.key.pem').exists())
        self.assertEqual(key.read_bytes(), original)
        for artifact in bundle.rglob('*'):
            self.assertEqual(artifact.stat().st_mode & 0o777, 0o700 if artifact.is_dir() else 0o600)

    def test_public_expiring_ca_is_refused_before_prompt_or_output(self):
        code, _ = self.run_play(True, self.public_vars(days='1'))
        self.assertNotEqual(code, 0)
        self.assertEqual(list(self.out.iterdir()), [])
