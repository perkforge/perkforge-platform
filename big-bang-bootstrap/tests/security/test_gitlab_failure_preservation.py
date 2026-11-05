"""GitLab must override Big Bang's inherited destructive failure remediation."""
import copy
import os
from pathlib import Path
import unittest
import yaml
from fixtures.render_helpers import build, helm, ordered_values

ROOT = Path(__file__).resolve().parents[2]


class GitLabFailurePreservation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        root = build(ROOT / 'clusters/local-gitlab-app')
        parent = next(o for o in root if o['kind'] == 'HelmRelease'
                      and o['metadata']['name'] == 'bigbang')
        values = ordered_values(root, parent)
        chart = Path(os.environ['PREFLIGHT_SOURCES_DIR']) / 'bigbang/chart'
        cls.current = helm(chart, 'bigbang', 'bigbang', values)
        legacy = []
        for value in values:
            document = yaml.safe_load(value)
            policy = document.get('addons', {}).get('gitlab', {}).get('flux', {})
            # Reproduce the actual released overrides: retries=0 did not clear
            # Big Bang's cleanupOnFail/remediateLastFailure defaults.
            policy.get('install', {}).get('remediation', {}).pop('remediateLastFailure', None)
            policy.get('upgrade', {}).get('remediation', {}).pop('remediateLastFailure', None)
            policy.get('upgrade', {}).pop('cleanupOnFail', None)
            legacy.append(yaml.safe_dump(document))
        cls.previous = helm(chart, 'bigbang', 'bigbang', legacy)

    @staticmethod
    def child(objects):
        return next(o for o in objects if o['kind'] == 'HelmRelease'
                    and o['metadata']['name'] == 'gitlab')

    def test_zero_retries_did_not_disable_inherited_failure_remediation(self):
        old = self.child(self.previous)['spec']
        self.assertEqual(old['upgrade']['remediation']['retries'], 0)
        self.assertTrue(old['upgrade']['remediation']['remediateLastFailure'])
        self.assertTrue(old['upgrade']['cleanupOnFail'])
        new = self.child(self.current)['spec']
        self.assertIs(new['install']['remediation']['remediateLastFailure'], False)
        self.assertIs(new['upgrade']['remediation']['remediateLastFailure'], False)
        self.assertIs(new['upgrade']['cleanupOnFail'], False)

    def test_only_three_policy_flags_change_in_full_umbrella_render(self):
        old, new = copy.deepcopy(self.previous), copy.deepcopy(self.current)
        for objects in (old, new):
            policy = self.child(objects)['spec']
            policy['install']['remediation']['remediateLastFailure'] = False
            policy['upgrade']['remediation']['remediateLastFailure'] = False
            policy['upgrade']['cleanupOnFail'] = False
        self.assertEqual(old, new)

    def test_no_retry_guard_or_ownership_bypass_is_added(self):
        child = self.child(self.current)
        policy = child['spec']
        self.assertFalse(policy['install']['createNamespace'])
        for action in ('install', 'upgrade'):
            self.assertEqual(policy[action]['remediation']['retries'], 0)
            for flag in ('replace', 'force', 'disableHooks', 'disableSchemaValidation',
                         'disableOpenAPIValidation'):
                self.assertNotIn(flag, policy[action])
        self.assertEqual(policy['serviceAccountName'], 'gitlab-installer')
        self.assertEqual(policy['targetNamespace'], 'gitlab')
        self.assertNotIn('reconcile.fluxcd.io/forceAt', child['metadata'].get('annotations', {}))
        self.assertNotIn('reconcile.fluxcd.io/resetAt', child['metadata'].get('annotations', {}))
        authored = yaml.safe_load((ROOT / 'configuration/packages/gitlab/candidate-values.yaml').read_text())
        self.assertIs(authored['addons']['gitlab']['enabled'], False)
        self.assertIs(authored['addons']['gitlab']['flux']['suspend'], True)
