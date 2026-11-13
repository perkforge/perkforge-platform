"""Offline rendering and fail-closed input contract, not live delivery acceptance."""
import copy
import importlib.util
import json
from pathlib import Path
import unittest
import jinja2
import yaml

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'configuration/observability/context-alerting'
spec = importlib.util.spec_from_file_location('alert_inputs', BASE / 'verify_inputs.py')
guard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)


def fixture():
    return {'id': 'portal', 'org_id': 1, 'approved': True,
            'ntfy': {'url': 'https://ntfy.example.test', 'topic': 'portal-alerts',
                     'token': 'synthetic-fixture-token', 'publisher_permission': 'exact-topic-write-only'},
            'mattermost': {'webhook_url': 'https://chat.example.test/hooks/' + 'a' * 26,
                           'channel_id': 'b' * 26, 'channel_locked': True}}


def render(audiences):
    guard.verify(audiences)
    env = jinja2.Environment(undefined=jinja2.StrictUndefined)
    env.filters['to_json'] = json.dumps
    return yaml.safe_load(env.from_string((BASE/'contact-points.yaml.j2').read_text()).render(alert_audiences=audiences))


class ContextAlerting(unittest.TestCase):
    def test_empty_is_unarmed(self):
        self.assertFalse(render([])['contactPoints'])

    def test_one_audience_two_native_receivers(self):
        point = render([fixture()])['contactPoints'][0]
        self.assertEqual(point['name'], 'context-portal')
        self.assertEqual(point['orgId'], 1)
        self.assertEqual([r['uid'] for r in point['receivers']], ['ctx-portal-ntfy', 'ctx-portal-mattermost'])
        for r in point['receivers']:
            self.assertEqual(r['type'], 'webhook')
            self.assertIs(r['disableResolveMessage'], False)
            self.assertEqual(r['settings']['httpMethod'], 'POST')
            self.assertIs(r['settings']['tlsConfig']['insecureSkipVerify'], False)
            payload = r['settings']['payload']['template']
            for banned in ['Labels', 'Annotations', 'Values', 'URL', 'channel', 'username', 'icon_url']:
                self.assertNotIn(banned, payload)
            for status in ['firing', 'resolved', 'unknown']:
                self.assertIn(status, payload)
        ntfy, mm = [r['settings'] for r in point['receivers']]
        self.assertEqual(ntfy['authorization_credentials'], 'synthetic-fixture-token')
        self.assertEqual(ntfy['authorization_scheme'], 'Bearer')
        self.assertIn('"topic":"portal-alerts"', ntfy['payload']['template'])
        self.assertTrue(mm['payload']['template'].startswith('{"text":'))
        self.assertNotIn('authorization_credentials', mm)

    def test_ambiguous_or_unapproved_inputs_rejected(self):
        mutations = [
            lambda a: a.update(approved=False),
            lambda a: a.update(org_id=True),
            lambda a: a.update(id='{{ .Labels.tenant }}'),
            lambda a: a.update(id='portal"\\evil'),
            lambda a: a.update(id='x'*25),
            lambda a: a.update(recipients=['viewer']),
            lambda a: a['ntfy'].update(topic='*'),
            lambda a: a['ntfy'].update(topic=''),
            lambda a: a['ntfy'].update(publisher_permission='admin'),
            lambda a: a['ntfy'].update(token=''),
            lambda a: a['ntfy'].update(token='a\nb'),
            lambda a: a['ntfy'].update(url='http://ntfy.example.test'),
            lambda a: a['ntfy'].update(url='https://ntfy.example.test:notaport'),
            lambda a: a['ntfy'].update(url='https://ntfy.example.test:99999'),
            lambda a: a['ntfy'].update(url='https://ntfy.example.test:0'),
            lambda a: a['ntfy'].update(url='https://user:pass@ntfy.example.test'),
            lambda a: a['ntfy'].update(url='https://ntfy.example.test/?template=other'),
            lambda a: a['ntfy'].update(url='https://ntfy.example.test/topic'),
            lambda a: a['mattermost'].update(channel_locked=False),
            lambda a: a['mattermost'].update(channel_id='*'),
            lambda a: a['mattermost'].update(webhook_url='https://chat.example.test/api/v4/posts'),
            lambda a: a['mattermost'].update(channel_override='other-tenant'),
            lambda a: a['mattermost'].update(webhook_url='https://chat.example.test/hooks/'+ 'a'*26 + '?channel=other'),
        ]
        for mutate in mutations:
            a = fixture(); mutate(a)
            with self.subTest(audience=a['id']):
                with self.assertRaises(guard.InvalidInputs) as error:
                    render([a])
                self.assertNotIn('synthetic-fixture-token', str(error.exception))
                self.assertNotIn('hooks/', str(error.exception))

    def test_duplicate_destinations_rejected(self):
        a, b = fixture(), fixture(); b['id'] = 'other'
        for field in ['ntfy', 'mattermost']:
            different = copy.deepcopy(b)
            different['ntfy']['topic'] = 'other-alerts'
            different['mattermost']['channel_id'] = 'c'*26
            different['mattermost']['webhook_url'] = 'https://chat.example.test/hooks/'+'d'*26
            different[field] = copy.deepcopy(a[field])
            with self.subTest(field=field), self.assertRaises(guard.InvalidInputs):
                render([a, different])
        with self.assertRaises(guard.InvalidInputs):
            render([a, a])

    def test_destination_aliases_rejected(self):
        for field, key, value in [
            ('ntfy', 'url', 'https://NTFY.example.test:443/'),
            ('mattermost', 'webhook_url', 'https://CHAT.example.test:443/hooks/'+'a'*26),
        ]:
            a, b = fixture(), fixture(); b['id'] = 'other'
            if field == 'ntfy':
                b['mattermost']['channel_id'] = 'c'*26
                b['mattermost']['webhook_url'] = 'https://chat.example.test/hooks/'+'d'*26
            else:
                b['ntfy']['topic'] = 'other-alerts'
            b[field][key] = value
            with self.subTest(field=field), self.assertRaises(guard.InvalidInputs):
                render([a, b])

    def test_no_policy_or_rule_or_live_selector_added(self):
        doc = render([fixture()])
        self.assertEqual(set(doc), {'apiVersion', 'contactPoints'})
        for path in (ROOT/'clusters').rglob('*.yaml'):
            self.assertNotIn('context-alerting', path.read_text())

if __name__ == '__main__':
    unittest.main()
