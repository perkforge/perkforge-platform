#!/usr/bin/env python3
"""Partition existing offline unittest discovery; never infer that tests can be skipped."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys
import unittest

START = Path(__file__).resolve().parents[1] / 'big-bang-bootstrap/tests'
IDENTITY = {
    'realm': 'integration.test_realm_foundation.',
    'human': 'integration.test_human_totp.',
    'admin': 'integration.test_perkforge_admin.',
}


def flatten(suite):
    for test in suite:
        if isinstance(test, unittest.TestSuite):
            yield from flatten(test)
        else:
            yield test


def shard_for(test_id, family):
    if family == 'platform':
        return next((name for name, prefix in IDENTITY.items()
                     if test_id.startswith(prefix)), 'residual')
    if family == 'sso':
        if test_id.startswith('integration.test_sso_clients.'):
            return 'clients'
        # New app fixtures stay in apps; they are never silently omitted.
        if test_id.startswith(('bootstrap.test_sso_', 'integration.test_sso_',
                               'security.test_platform_sso.')):
            return 'apps'
        return None
    raise ValueError('unknown test family')


def partition(tests, family, expected_ids=None):
    names = ('residual', *IDENTITY) if family == 'platform' else ('clients', 'apps')
    buckets = {name: [] for name in names}
    seen = Counter(test.id() for test in tests)
    if any(count != 1 for count in seen.values()):
        raise ValueError('duplicate discovered test IDs')
    for test in tests:
        name = shard_for(test.id(), family)
        if name is not None:
            buckets[name].append(test)
    if family == 'sso' and expected_ids is None:
        raise ValueError('SSO requires the original discovery baseline')
    expected = (Counter(test.id() for test in tests) if family == 'platform'
                else Counter(expected_ids))
    assigned = Counter(test.id() for bucket in buckets.values() for test in bucket)
    if expected != assigned or any(n != 1 for n in assigned.values()):
        raise ValueError('missing or duplicated test assignment')
    if any(not bucket for bucket in buckets.values()):
        raise ValueError('empty required shard; review renamed or removed tests')
    return buckets


def discover():
    loader = unittest.TestLoader()
    tests = list(flatten(loader.discover(str(START))))
    if loader.errors:
        raise ValueError('test discovery failed:\n' + '\n'.join(loader.errors))
    return tests


def original_sso_ids():
    """Independent baseline: the three original workflow discovery commands."""
    ids = []
    for directory, pattern in (('security', 'test_platform_sso.py'),
                               ('bootstrap', 'test_sso_*.py'),
                               ('integration', 'test_sso_*.py')):
        loader = unittest.TestLoader()
        suite = loader.discover(str(START / directory), pattern=pattern,
                                top_level_dir=str(START))
        if loader.errors:
            raise ValueError('original SSO discovery failed')
        ids.extend(test.id() for test in flatten(suite))
    return ids


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--family', choices=('platform', 'sso'), required=True)
    parser.add_argument('--shard')
    parser.add_argument('--audit', action='store_true', help='list counts/digests; execute no tests')
    args = parser.parse_args()
    buckets = partition(discover(), args.family,
                        original_sso_ids() if args.family == 'sso' else None)
    if args.audit:
        report = {name: {'tests': len(tests), 'ids_sha256': hashlib.sha256(
            '\n'.join(sorted(t.id() for t in tests)).encode()).hexdigest()}
                  for name, tests in buckets.items()}
        print(json.dumps(report, sort_keys=True))
        return 0
    if args.shard not in buckets:
        parser.error('choose one of: ' + ', '.join(buckets))
    print(f'{args.family}/{args.shard}: {len(buckets[args.shard])} discovered tests', flush=True)
    return 0 if unittest.TextTestRunner(verbosity=2).run(
        unittest.TestSuite(buckets[args.shard])).wasSuccessful() else 1


if __name__ == '__main__':
    sys.exit(main())
