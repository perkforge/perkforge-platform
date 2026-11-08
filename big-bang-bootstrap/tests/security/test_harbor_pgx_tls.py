"""Pinned native driver TLS, separate from Harbor/image/database acceptance."""
import os
from pathlib import Path
import shutil
import subprocess
import unittest


class HarborPGXTLS(unittest.TestCase):
    def test_native_verify_full_and_explicit_root(self):
        if not shutil.which('go'):
            if os.environ.get('REQUIRE_NATIVE_HARBOR_PGX') == '1':
                self.fail('Go is required for the explicitly requested native pgx check')
            self.skipTest('Go unavailable; native pgx TLS was not tested')
        fixture = Path(__file__).resolve().parents[1] / 'fixtures/harbor-pgx'
        # Dependencies must be prefetched explicitly. Default test discovery never
        # downloads code or contacts a service. Missing dependencies are a failure.
        result = subprocess.run(['go', 'test', '-mod=readonly', '-count=1', '-v', '.'],
                                cwd=fixture, text=True, capture_output=True, timeout=180,
                                env={**os.environ, 'GOPROXY': 'off', 'GOSUMDB': 'off',
                                     'GOTOOLCHAIN': 'local', 'GOWORK': 'off'})
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('--- PASS: TestHarborPGXTrust', result.stdout)
