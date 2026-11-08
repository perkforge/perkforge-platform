"""Exact Iron Bank scripts, synthetic roots, rootless mounts; no image pulls/apps."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import tempfile
import unittest

import yaml

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / 'tests/fixtures/harbor-image-startup'
ALIAS = '/etc/pki/tls/certs/ca-bundle.crt'
TARGET = '/etc/pki/ca-trust/extracted/pem/tls-ca-bundle.pem'
BASE = b'-----BEGIN CERTIFICATE-----\nsynthetic image root\n-----END CERTIFICATE-----\n'
INTERNAL = b'-----BEGIN CERTIFICATE-----\nsynthetic internal root\n-----END CERTIFICATE-----\n'
CUSTOM = b'-----BEGIN CERTIFICATE-----\nsynthetic custom root\n-----END CERTIFICATE-----\n'


def initialization(component):
    values = yaml.safe_load((ROOT / 'configuration/packages/harbor/application/values.yaml').read_text())
    patches = values['addons']['harbor']['postRenderers'][0]['kustomize']['patches']
    patch = next(p for p in patches if p['target'] == {'kind': 'Deployment', 'name': 'harbor-' + component})
    return yaml.safe_load(patch['patch'])['spec']['template']['spec']['initContainers'][0]


class HarborImageSource(unittest.TestCase):
    def test_fixtures_are_exact_immutable_2152_sources_for_both_components(self):
        sources = json.loads((FIXTURES / 'sources.json').read_text())
        self.assertEqual(set(sources), {'core', 'jobservice'})
        for component, source in sources.items():
            self.assertEqual(source['image'], 'registry1.dso.mil/ironbank/opensource/goharbor/harbor-' + component + ':v2.15.2')
            self.assertEqual(set(source['files']), {'install_cert.sh', component + '-entrypoint.sh'})
            for name, metadata in source['files'].items():
                self.assertEqual(hashlib.sha256((FIXTURES / name).read_bytes()).hexdigest(), metadata['sha256'])
                self.assertIn('/-/raw/' + source['commit'] + '/scripts/', metadata['url'])
        self.assertEqual(initialization('core')['args'], initialization('jobservice')['args'])


@unittest.skipUnless(shutil.which('bwrap'), 'Rootless mount test requires preinstalled bubblewrap; never installs it')
@unittest.skipIf(os.getuid() == 0, 'Run this fixture as an ordinary non-root user')
class HarborImageStartup(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='harbor-startup-')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.etc = self.root / 'etc'
        self.harbor = self.root / 'harbor'
        self.custom = self.root / 'custom'
        self.trust = self.root / 'trust'
        for path in (self.etc, self.harbor, self.custom, self.trust):
            path.mkdir()
        self.original = self.root / 'image-bundle'
        self.original.write_bytes(BASE)
        self.original.chmod(0o444)
        target = self.local(TARGET)
        target.parent.mkdir(parents=True)
        target.write_bytes(BASE)
        target.chmod(0o444)
        alias = self.local(ALIAS)
        alias.parent.mkdir(parents=True)
        alias.symlink_to(TARGET)
        (self.custom / 'custom-ca.crt').write_bytes(CUSTOM)
        (self.custom / 'custom-ca.crt').chmod(0o444)
        (self.custom / 'ignored.txt').write_text('not a certificate\n')
        (self.custom / 'ignored.pem').mkdir()
        shutil.copyfile(FIXTURES / 'install_cert.sh', self.harbor / 'install_cert.sh')
        (self.harbor / 'install_cert.sh').chmod(0o700)

    def local(self, absolute):
        return self.etc / absolute.removeprefix('/etc/')

    def component(self, name):
        cert = self.etc / 'harbor/ssl' / name / 'ca.crt'
        cert.parent.mkdir(parents=True, exist_ok=True)
        cert.write_bytes(INTERNAL)
        cert.chmod(0o444)
        shutil.copyfile(FIXTURES / (name + '-entrypoint.sh'), self.harbor / 'entrypoint.sh')
        (self.harbor / 'entrypoint.sh').chmod(0o700)
        binary = self.harbor / ('harbor_' + name)
        # Only the application binary is a sentinel; both startup scripts are
        # executed byte-for-byte. UBI's /bin/sh is Bash, unlike Debian's dash.
        binary.write_text('#!/bin/sh\nset -e\n'
                          'test "$(id -u)" = 10000\n'
                          'test "$(id -g)" = 1000\n'
                          'test ! -w /harbor_cust_cert/custom-ca.crt\n'
                          f'test ! -w /etc/harbor/ssl/{name}/ca.crt\n'
                          f'printf "binary-started:{name}:%s\\n" "$*"\n')
        binary.chmod(0o700)

    def run_shell(self, command, *, copy=False, bundle=None):
        # Only public host binaries and synthetic files are visible. No host
        # home, kubeconfig, registry auth, real certificates or apps are mounted.
        args = ['bwrap', '--die-with-parent', '--unshare-all', '--uid', '10000', '--gid', '1000',
                '--cap-drop', 'ALL', '--clearenv', '--setenv', 'PATH', '/usr/bin:/bin',
                '--ro-bind', '/usr', '/usr', '--symlink', 'usr/lib', '/lib',
                '--symlink', 'usr/lib64', '/lib64', '--dir', '/bin',
                '--ro-bind', shutil.which('bash'), '/bin/sh', '--dev', '/dev',
                '--ro-bind', str(self.etc), '/etc', '--ro-bind', str(self.harbor), '/harbor',
                '--ro-bind', str(self.custom), '/harbor_cust_cert']
        if copy:
            args += ['--bind', str(self.trust), '/harbor-trust']
        if bundle is not None:
            args += ['--bind', str(bundle), TARGET]
        args += ['--remount-ro', '/', '--', '/bin/sh', '-ec',
                 'test "$(id -u)" = 10000; test "$(id -g)" = 1000; ' + command]
        return subprocess.run(args, capture_output=True, text=True, timeout=20)

    def test_original_scripts_fail_before_binaries_without_writable_bundle(self):
        for component in ('core', 'jobservice'):
            with self.subTest(component=component):
                self.component(component)
                result = self.run_shell('/harbor/entrypoint.sh', bundle=self.original)
                self.assertNotEqual(result.returncode, 0, result.stdout)
                self.assertIn('Permission denied', result.stderr)
                self.assertNotIn('binary-started:', result.stdout)
                self.assertEqual(self.original.read_bytes(), BASE)

    def test_owned_copy_preserves_roots_and_executes_both_original_entrypoints(self):
        for component in ('core', 'jobservice'):
            with self.subTest(component=component):
                self.component(component)
                # Ensure the prior component's synthetic internal root cannot
                # contaminate the next component's expected single-root append.
                for other in ('core', 'jobservice'):
                    if other != component:
                        shutil.rmtree(self.etc / 'harbor/ssl' / other, ignore_errors=True)
                init = initialization(component)
                result = self.run_shell(init['args'][0], copy=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                copied = self.trust / 'ca-bundle.crt'
                self.assertEqual(copied.read_bytes(), BASE)
                self.assertEqual(stat.S_IMODE(copied.stat().st_mode), 0o600)
                result = self.run_shell('/harbor/entrypoint.sh', bundle=copied)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn('binary-started:' + component + ':', result.stdout)
                if component == 'jobservice':
                    self.assertIn('binary-started:jobservice:-c /etc/jobservice/config.yml', result.stdout)
                self.assertEqual(copied.read_bytes(), BASE + INTERNAL + CUSTOM)
                self.assertEqual(self.local(TARGET).read_bytes(), BASE)
                self.assertEqual((self.custom / 'custom-ca.crt').read_bytes(), CUSTOM)
                # A repeated init rebuilds from the immutable image roots.
                result = self.run_shell(init['args'][0], copy=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(copied.read_bytes(), BASE)

    def test_init_refuses_missing_wrong_or_empty_trust_target(self):
        for problem in ('missing-alias', 'wrong-target', 'missing-target', 'empty-target'):
            with self.subTest(problem=problem):
                alias, target = self.local(ALIAS), self.local(TARGET)
                alias.unlink(missing_ok=True)
                alias.symlink_to('/etc/other-bundle' if problem == 'wrong-target' else TARGET)
                self.local('/etc/other-bundle').write_bytes(BASE)
                target.chmod(0o600)
                target.write_bytes(b'' if problem == 'empty-target' else BASE)
                target.chmod(0o444)
                if problem == 'missing-alias':
                    alias.unlink()
                if problem == 'missing-target':
                    target.unlink()
                for component in ('core', 'jobservice'):
                    result = self.run_shell(initialization(component)['args'][0], copy=True)
                    self.assertNotEqual(result.returncode, 0, result.stdout)
                    self.assertIn('Refusing unexpected Harbor trust-bundle layout', result.stderr)
                    self.assertFalse((self.trust / 'ca-bundle.crt').exists())
                # Restore the missing inode for the next negative case.
                if not target.exists():
                    target.write_bytes(BASE)
