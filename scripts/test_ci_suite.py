"""Offline partition and required-workflow coverage checks; no fixture execution."""
from collections import Counter
import importlib.util
from pathlib import Path
import subprocess
import unittest
from unittest.mock import patch
import yaml

spec = importlib.util.spec_from_file_location('ci_suite', Path(__file__).with_name('ci_suite.py'))
ci = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ci)


class Case:
    def __init__(self, name): self.name = name
    def id(self): return self.name


class AssignmentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tests = ci.discover()

    def test_original_platform_discovery_is_exactly_partitioned(self):
        buckets = ci.partition(self.tests, 'platform')
        self.assertEqual(Counter(t.id() for t in self.tests),
                         Counter(t.id() for b in buckets.values() for t in b))
        self.assertTrue(all(buckets.values()))

    def test_original_three_sso_commands_match_without_omissions(self):
        expected = ci.original_sso_ids()
        buckets = ci.partition(self.tests, 'sso', expected)
        self.assertEqual(Counter(expected), Counter(t.id() for b in buckets.values() for t in b))

    def test_new_platform_and_app_tests_have_required_residual_owners(self):
        self.assertEqual(ci.shard_for('integration.test_future.Case.test_new', 'platform'), 'residual')
        self.assertEqual(ci.shard_for('integration.test_sso_future.Case.test_new', 'sso'), 'apps')
        self.assertEqual(ci.shard_for('bootstrap.test_sso_clients.Case.test_new', 'sso'), 'apps')

    def test_duplicate_or_missing_assignment_fails_closed(self):
        with self.assertRaisesRegex(ValueError, 'duplicate discovered'):
            ci.partition(self.tests + [self.tests[0]], 'platform')
        expected = ci.original_sso_ids()
        with self.assertRaisesRegex(ValueError, 'missing or duplicated'):
            ci.partition(self.tests, 'sso', expected + ['integration.test_sso_future.Case.test_new'])
        with patch.object(ci, 'shard_for', return_value=None):
            with self.assertRaises(ValueError): ci.partition(self.tests, 'sso', expected)

    def test_renamed_identity_bucket_or_unknown_family_requires_review(self):
        with self.assertRaisesRegex(ValueError, 'empty required shard'):
            ci.partition([Case('future.Test.test')], 'platform')
        with self.assertRaises(ValueError): ci.shard_for('future.Test.test', 'unknown')
        with self.assertRaisesRegex(ValueError, 'original discovery baseline'):
            ci.partition(self.tests, 'sso')

    def test_audit_executes_no_fixture_and_unknown_shard_is_rejected(self):
        for family in ('platform', 'sso'):
            r = subprocess.run(['python3', 'scripts/ci_suite.py', '--family', family, '--audit'],
                               text=True, capture_output=True)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn('ids_sha256', r.stdout)
        r = subprocess.run(['python3', 'scripts/ci_suite.py', '--family', 'platform', '--shard', 'unknown'],
                           text=True, capture_output=True)
        self.assertNotEqual(r.returncode, 0)

    def test_fixture_failure_is_not_hidden_and_audit_never_runs_tests(self):
        with patch.object(ci, 'discover', return_value=self.tests), \
             patch.object(ci.sys, 'argv', ['ci_suite.py', '--family', 'platform', '--shard', 'realm']), \
             patch.object(ci.unittest, 'TextTestRunner') as runner:
            runner.return_value.run.return_value.wasSuccessful.return_value = False
            self.assertEqual(ci.main(), 1)
            runner.return_value.run.assert_called_once()
        with patch.object(ci, 'discover', return_value=self.tests), \
             patch.object(ci.sys, 'argv', ['ci_suite.py', '--family', 'platform', '--audit']), \
             patch.object(ci.unittest, 'TextTestRunner') as runner:
            self.assertEqual(ci.main(), 0)
            runner.assert_not_called()

    def test_every_shard_remains_required_without_fail_fast_or_failure_suppression(self):
        w = yaml.load(Path('.github/workflows/gitops-selection.yml').read_text(), Loader=yaml.BaseLoader)
        jobs = w['jobs']
        self.assertEqual(jobs['regressions']['strategy']['matrix']['suite'],
                         ['realm', 'human', 'admin', 'infrastructure', 'pxe'])
        self.assertEqual(jobs['platform-sso']['strategy']['matrix']['suite'], ['clients', 'apps'])
        self.assertEqual(jobs['regressions']['strategy']['max-parallel'], '3')
        for name in ('regressions', 'platform-sso'):
            self.assertEqual(jobs[name]['strategy']['fail-fast'], 'false')
            self.assertEqual(jobs[name]['needs'], ['changes'])
            self.assertNotIn('continue-on-error', jobs[name])
            self.assertFalse(any('continue-on-error' in s for s in jobs[name]['steps']))
            self.assertEqual(jobs[name]['env']['KUBECONFIG'], '/dev/null')
        self.assertEqual(jobs['regressions']['if'], "needs.changes.outputs.full == 'true'")
        commands = '\n'.join(s.get('run', '') for s in jobs['selection']['steps'])
        self.assertIn('ci_suite.py --family platform --shard residual', commands)
        self.assertIn('unittest discover -s evidence/tests', commands)
        self.assertIn('go test -run TestFluxPortalAdmission', commands)
        regression_commands = '\n'.join(s.get('run', '') for s in jobs['regressions']['steps'])
        for directory in ('infrastructure/ansible/tests', 'pxe/tests'):
            self.assertIn('unittest discover -s ' + directory, regression_commands)
        release = yaml.load(Path('.github/workflows/configuration-release.yml').read_text(), Loader=yaml.BaseLoader)
        self.assertEqual(release['jobs']['release']['needs'], ['configuration', 'release-checks'])


if __name__ == '__main__': unittest.main()
