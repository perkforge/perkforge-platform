"""Bounded transport retries; real checksum/cache behavior, no public network."""
import hashlib
import http.client
import io
from pathlib import Path
import ssl
import tempfile
import unittest
from unittest.mock import Mock
import urllib.error

from fixtures.fetch_sources import fetch_archive


class FixtureDownloads(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.data = b'synthetic pinned archive'
        self.source = {'url': 'https://example.invalid/pinned.tgz',
                       'sha256': hashlib.sha256(self.data).hexdigest()}
        self.sleep = Mock()

    def fetch(self, opener):
        return fetch_archive('fixture', self.source, self.root,
                             open_url=opener, sleep=self.sleep)

    def assert_no_cache(self):
        self.assertEqual(list((self.root / '.archives').iterdir()), [])

    def test_504_then_valid_artifact_is_verified_and_cached(self):
        opener = Mock(side_effect=[urllib.error.HTTPError(self.source['url'], 504, 'timeout', {}, None), io.BytesIO(self.data)])
        self.assertEqual(self.fetch(opener).read_bytes(), self.data)
        self.assertEqual(opener.call_count, 2)
        self.sleep.assert_called_once_with(2)
        self.assertEqual(len(list((self.root / '.archives').iterdir())), 1)

    def test_timeout_and_incomplete_body_retry_with_bounded_backoff(self):
        opener = Mock(side_effect=[urllib.error.URLError(TimeoutError()),
                                  http.client.IncompleteRead(b'partial'), io.BytesIO(self.data)])
        self.assertEqual(self.fetch(opener).read_bytes(), self.data)
        self.assertEqual(opener.call_count, 3)
        self.assertEqual([c.args[0] for c in self.sleep.call_args_list], [2, 5])
        self.assertTrue(all(c.kwargs['timeout'] == 45 for c in opener.call_args_list))

    def test_persistent_gateway_failure_stops_after_three_attempts(self):
        opener = Mock(side_effect=lambda *a, **k: (_ for _ in ()).throw(
            urllib.error.HTTPError(self.source['url'], 504, 'timeout', {}, None)))
        with self.assertRaises(urllib.error.HTTPError): self.fetch(opener)
        self.assertEqual(opener.call_count, 3)
        self.assert_no_cache()

    def test_permanent_http_and_certificate_failures_are_not_retried(self):
        for error in [urllib.error.HTTPError(self.source['url'], 404, 'missing', {}, None),
                      urllib.error.URLError(ssl.SSLCertVerificationError('bad certificate'))]:
            opener = Mock(side_effect=error)
            with self.assertRaises(urllib.error.URLError): self.fetch(opener)
            self.assertEqual(opener.call_count, 1)
            self.assert_no_cache()
        self.sleep.assert_not_called()

    def test_wrong_checksum_is_not_retried_or_cached(self):
        opener = Mock(return_value=io.BytesIO(b'wrong bytes'))
        with self.assertRaisesRegex(ValueError, 'downloaded checksum mismatch'): self.fetch(opener)
        self.assertEqual(opener.call_count, 1)
        self.sleep.assert_not_called()
        self.assert_no_cache()

    def test_good_cache_is_reverified_without_network(self):
        self.fetch(Mock(return_value=io.BytesIO(self.data)))
        opener = Mock()
        self.assertEqual(self.fetch(opener).read_bytes(), self.data)
        opener.assert_not_called()

    def test_corrupt_cache_fails_closed_without_overwrite(self):
        archive = self.root / '.archives' / 'fixture.tgz'
        archive.parent.mkdir(); archive.write_bytes(b'corrupt')
        opener = Mock()
        with self.assertRaisesRegex(ValueError, 'cached checksum mismatch'): self.fetch(opener)
        self.assertEqual(archive.read_bytes(), b'corrupt')
        opener.assert_not_called()
