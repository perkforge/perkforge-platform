"""Real-Ansible offline issuance; all private identities are disposable test data."""
from pathlib import Path
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
import unittest

from cryptography import x509
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / 'configuration/packages/harbor'
PLAY = PACKAGE / 'prepare-token-signing.yaml'
SCOPE = 'harbor-token-signing-issuance-v1'


@unittest.skipUnless(shutil.which('ansible-playbook') and shutil.which('openssl') and shutil.which('git'),
                     'Ansible, OpenSSL and Git required')
class HarborTokenGeneration(unittest.TestCase):
    def setUp(self):
        # Protected ancestry, unlike world-writable /tmp. Never use operator inputs.
        self.tmp = tempfile.TemporaryDirectory(prefix='harbor-token-fixture-', dir=Path.home())
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name)
        self.out = self.path / 'out'
        self.out.mkdir(mode=0o700)
        self.env = {**os.environ, 'ANSIBLE_LOCAL_TEMP': str(self.path / 'local'),
                    'ANSIBLE_REMOTE_TEMP': str(self.path / 'remote'), 'ANSIBLE_NOCOLOR': '1',
                    'KUBECONFIG': '/dev/null'}

    def variables(self, **changes):
        return {'harbor_token_signing_run': True, 'harbor_token_signing_scope': SCOPE,
                'harbor_token_signing_output_parent': str(self.out),
                'harbor_token_signing_cluster_id': 'synthetic-cluster', **changes}

    def run_play(self, values=None, check=False, env=None):
        variables = self.path / 'vars.json'
        variables.write_text(json.dumps(values or {}))
        variables.chmod(0o600)
        args = ['ansible-playbook', '-i', 'localhost,', str(PLAY), '-e', '@' + str(variables)]
        if check:
            args.append('--check')
        result = subprocess.run(args, env=env or self.env, capture_output=True, text=True, timeout=120)
        log = result.stdout + result.stderr
        self.assertNotIn('-----BEGIN RSA PRIVATE KEY-----', log)
        self.assertNotIn('-----BEGIN CERTIFICATE-----', log)
        return result.returncode, log

    def bundle(self, name='harbor-token-signing-pkcs1-v1'):
        return self.out / name

    def snapshot(self, path):
        return {str(p.relative_to(path)): (p.stat().st_mode, p.read_bytes())
                for p in path.rglob('*') if p.is_file()}

    def verify_bundle(self, bundle, log, cluster_id, namespace_uid):
        self.assertEqual({str(p.relative_to(bundle)) for p in bundle.rglob('*')},
                         {'delivery', 'delivery/token-signing', 'delivery/token-signing/tls.crt',
                          'delivery/token-signing/tls.key', 'receipt.txt', 'READY'})
        for p in [bundle, *bundle.rglob('*')]:
            self.assertFalse(p.is_symlink())
            self.assertEqual(p.stat().st_uid, os.getuid())
            self.assertEqual(p.stat().st_mode & 0o777, 0o700 if p.is_dir() else 0o600)
            if p.is_file():
                self.assertEqual(p.stat().st_nlink, 1)
        key_pem = (bundle / 'delivery/token-signing/tls.key').read_bytes()
        cert_pem = (bundle / 'delivery/token-signing/tls.crt').read_bytes()
        key = serialization.load_pem_private_key(key_pem, None)
        cert = x509.load_pem_x509_certificate(cert_pem)
        self.assertIsInstance(key, rsa.RSAPrivateKey)
        self.assertEqual(key.key_size, 3072)
        self.assertEqual(key_pem, key.private_bytes(serialization.Encoding.PEM,
                         serialization.PrivateFormat.TraditionalOpenSSL, serialization.NoEncryption()))
        self.assertEqual(cert_pem.count(b'-----BEGIN CERTIFICATE-----'), 1)
        self.assertEqual(key.public_key().public_numbers(), cert.public_key().public_numbers())
        self.assertEqual(cert.subject, cert.issuer)
        self.assertEqual((cert.not_valid_after_utc - cert.not_valid_before_utc).days, 365)
        self.assertTrue(cert.extensions.get_extension_for_class(x509.KeyUsage).value.digital_signature)
        self.assertFalse(cert.extensions.get_extension_for_class(x509.BasicConstraints).value.ca)
        result = subprocess.run(['openssl', 'verify', '-CAfile', str(bundle / 'delivery/token-signing/tls.crt'),
                                 str(bundle / 'delivery/token-signing/tls.crt')], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((bundle / 'READY').read_text(), SCOPE + '\n')
        self.assertIn('Secret: harbor-token-signing-pkcs1-v1', (bundle / 'receipt.txt').read_text())
        self.assertIn('Cluster identity: ' + cluster_id, (bundle / 'receipt.txt').read_text())
        self.assertIn('Namespace UID: ' + namespace_uid, (bundle / 'receipt.txt').read_text())
        public_der = key.public_key().public_bytes(serialization.Encoding.DER,
                                                   serialization.PublicFormat.SubjectPublicKeyInfo)
        self.assertIn(hashlib.sha256(public_der).hexdigest(), (bundle / 'receipt.txt').read_text())
        self.assertNotIn(key_pem.decode().splitlines()[1], log)
        return key_pem

    def test_default_and_check_are_noops_even_with_invalid_private_paths(self):
        for values, check in (({}, False), (self.variables(harbor_token_signing_output_parent='/absent/private'), True)):
            code, log = self.run_play(values, check)
            self.assertEqual(code, 0, log)
            self.assertIn('changed=0', log)
            self.assertEqual(list(self.out.iterdir()), [])

    def test_two_new_clusters_have_independent_keys_and_repeat_refuses(self):
        keys = []
        for name in ('cluster-one', 'cluster-two'):
            namespace_uid = 'NOT_CREATED' if name == 'cluster-one' else 'synthetic-namespace-uid'
            values = self.variables(harbor_token_signing_bundle_name=name,
                                    harbor_token_signing_cluster_id=name,
                                    harbor_token_signing_namespace_uid=namespace_uid)
            code, log = self.run_play(values)
            self.assertEqual(code, 0, log)
            bundle = self.bundle(name)
            keys.append(self.verify_bundle(bundle, log, name, namespace_uid))
            before = self.snapshot(bundle)
            code, log = self.run_play(values)
            self.assertNotEqual(code, 0, log)
            self.assertEqual(self.snapshot(bundle), before)
        self.assertNotEqual(*keys)

    def test_generated_bundle_passes_exact_native_harbor_parser(self):
        if not shutil.which('go'):
            if os.environ.get('REQUIRE_NATIVE_HARBOR_SIGNING') == '1':
                self.fail('Go is required for the explicitly requested native signing check')
            self.skipTest('Go unavailable; native producer output was not tested')
        code, log = self.run_play(self.variables())
        self.assertEqual(code, 0, log)
        fixture = ROOT / 'tests/fixtures/harbor-token-signing'
        result = subprocess.run(['go', 'test', '-mod=readonly', '-count=1', '-v',
                                 '-run', '^TestGeneratedTokenBundle$', '.'], cwd=fixture,
                                capture_output=True, text=True, timeout=180,
                                env={**self.env, 'GOPROXY': 'off', 'GOSUMDB': 'off',
                                     'GOTOOLCHAIN': 'local', 'GOWORK': 'off',
                                     'HARBOR_SYNTHETIC_TOKEN_BUNDLE': str(self.bundle())})
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('--- PASS: TestGeneratedTokenBundle', result.stdout)
        self.assertNotIn('-----BEGIN RSA PRIVATE KEY-----', result.stdout + result.stderr)

    def test_bad_scope_parent_mode_symlinks_and_names_refuse_before_output(self):
        link = self.path / 'linked-parent'
        link.symlink_to(self.out, target_is_directory=True)
        cases = [self.variables(harbor_token_signing_scope='wrong'),
                 self.variables(harbor_token_signing_cluster_id='UNCONFIGURED'),
                 self.variables(harbor_token_signing_namespace_uid='invalid'),
                 self.variables(harbor_token_signing_output_parent=str(link)),
                 self.variables(harbor_token_signing_output_parent=str(self.out / '..' / 'out')),
                 self.variables(harbor_token_signing_bundle_name='../escape')]
        for values in cases:
            code, log = self.run_play(values)
            self.assertNotEqual(code, 0, log)
            self.assertEqual(list(self.out.iterdir()), [])
        self.out.chmod(0o750)
        code, log = self.run_play(self.variables())
        self.assertNotEqual(code, 0, log)
        self.assertEqual(list(self.out.iterdir()), [])
        self.out.chmod(0o700)

    def test_git_worktree_output_refused(self):
        subprocess.run(['git', 'init', '-q', str(self.out)], check=True, capture_output=True)
        code, log = self.run_play(self.variables())
        self.assertNotEqual(code, 0, log)
        self.assertFalse(self.bundle().exists())

    def test_partial_and_symlink_or_hardlinked_output_never_adopted(self):
        bundle = self.bundle()
        bundle.mkdir(mode=0o700)
        partial = bundle / 'tls.key'
        partial.write_bytes(b'partial synthetic material')
        partial.chmod(0o600)
        before = self.snapshot(bundle)
        code, log = self.run_play(self.variables())
        self.assertNotEqual(code, 0, log)
        self.assertEqual(self.snapshot(bundle), before)
        self.assertFalse((bundle / 'READY').exists())
        # Refuse without opening even a hardlinked file occupying the bundle path.
        bundle.rename(self.out / 'partial-retained')
        os.link(self.out / 'partial-retained/tls.key', bundle)
        code, log = self.run_play(self.variables())
        self.assertNotEqual(code, 0, log)
        self.assertEqual(bundle.read_bytes(), b'partial synthetic material')
        bundle.unlink()
        bundle.symlink_to(self.out / 'partial-retained', target_is_directory=True)
        code, log = self.run_play(self.variables())
        self.assertNotEqual(code, 0, log)
        self.assertEqual(self.snapshot(self.out / 'partial-retained'), before)

    def test_failed_generation_retains_partial_without_receipt_or_ready(self):
        # Simulate OpenSSL failure after reserving the bundle, without touching any
        # real credentials or adding a production failure-injection switch.
        bin_dir = self.path / 'bin'
        bin_dir.mkdir(mode=0o700)
        fake = bin_dir / 'openssl'
        fake.write_text('#!/bin/sh\nprintf "partial synthetic material" > delivery/token-signing/tls.key\nexit 1\n')
        fake.chmod(0o700)
        env = {**self.env, 'PATH': str(bin_dir) + os.pathsep + self.env['PATH']}
        code, log = self.run_play(self.variables(), env=env)
        self.assertNotEqual(code, 0, log)
        self.assertTrue((self.bundle() / 'delivery/token-signing/tls.key').is_file())
        self.assertFalse((self.bundle() / 'receipt.txt').exists())
        self.assertFalse((self.bundle() / 'READY').exists())
        before = self.snapshot(self.bundle())
        code, log = self.run_play(self.variables())
        self.assertNotEqual(code, 0, log)
        self.assertEqual(self.snapshot(self.bundle()), before)
