"""Offline hook contract tests, not runtime delivery or native authorization proof."""
import copy
import importlib.util
import json
from pathlib import Path
import unittest
import jinja2
import yaml

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'configuration/packages/gitlab/events'
spec = importlib.util.spec_from_file_location('gitlab_hook_inputs', BASE / 'verify_inputs.py')
guard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)


class GitLabEvents(unittest.TestCase):
    def setUp(self):
        self.context = {'id': 'portal', 'targets': {'gitlab': {'group_id': 10, 'project_ids': [11]}}}
        self.hook = {'approved': True, 'context': 'portal', 'project_id': 11,
                     'receiver_url': 'https://events.example.test/gitlab/events/portal',
                     'token': 'synthetic-not-real-token-' + 'x' * 32}

    def test_native_hook_filters_and_tls(self):
        guard.verify(self.hook, self.context)
        env = jinja2.Environment(undefined=jinja2.StrictUndefined)
        env.filters['to_json'] = json.dumps
        body = json.loads(env.from_string((BASE / 'project-hook.json.j2').read_text()).render(gitlab_event_hook=self.hook))
        self.assertEqual({k for k, v in body.items() if k.endswith('_events') and v},
                         {'job_events', 'pipeline_events', 'deployment_events'})
        self.assertIs(body['enable_ssl_verification'], True)
        self.assertEqual(body['url'], self.hook['receiver_url'])
        self.assertEqual(body['token'], self.hook['token'])
        self.assertNotIn('channel', body)

    def test_reject_unapproved_wrong_project_and_override_fields(self):
        mutations = [{'approved': False}, {'project_id': 12}, {'project_id': True},
                     {'context': 'other'}, {'channel': 'arbitrary'}, {'token': 'short'}]
        for patch in mutations:
            with self.subTest(patch=patch):
                with self.assertRaises(ValueError):
                    guard.verify(self.hook | patch, self.context)

    def test_reject_redirect_target_and_secret_url(self):
        for url in ['http://events.example.test/gitlab/events/portal',
                    'https://user:secret@events.example.test/gitlab/events/portal',
                    'https://events.example.test/gitlab/events/other',
                    self.hook['receiver_url'] + '?channel=other',
                    self.hook['receiver_url'] + '#secret',
                    'https://events.example.test:bad/gitlab/events/portal']:
            with self.assertRaises(ValueError) as error:
                guard.verify(self.hook | {'receiver_url': url}, self.context)
            self.assertNotIn(url, str(error.exception))

    def test_actual_unresolved_context_refuses_activation(self):
        context = yaml.safe_load((ROOT / 'configuration/authorization/contexts/portal.yaml').read_text())['paas_context']
        with self.assertRaises(ValueError):
            guard.verify(self.hook, context)
        for ids in [[], [11, 11], [True], ['11']]:
            context = copy.deepcopy(self.context)
            context['targets']['gitlab']['project_ids'] = ids
            with self.assertRaises(ValueError):
                guard.verify(self.hook, context)

    def test_selected_policy_is_inactive_and_viewer_safe(self):
        policy = yaml.safe_load((BASE / 'policy.yaml').read_text())['gitlab_events']
        self.assertIs(policy['enabled'], False)
        self.assertIsNone(policy['receiver'])
        self.assertIsNone(policy['security_findings_threshold'])
        self.assertEqual(policy['security_scan_jobs'], [])
        self.assertEqual(policy['events'], {'pipeline': {'failed': 'firing', 'recovered': 'resolved'},
                         'security_scan_execution': {'failed': 'firing'}, 'deployment': {'failed': 'firing'}})
        self.assertEqual(policy['viewer_delivery'], 'mattermost-channel-only')
        self.assertEqual(policy['repeat'], 'unresolved-only')
        self.assertIs(policy['raw_payload_forwarding'], False)


if __name__ == '__main__':
    unittest.main()
