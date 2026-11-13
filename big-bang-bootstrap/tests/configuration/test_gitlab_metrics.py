"""Candidate rendering/negative-input checks. No native evaluation or live events."""
import copy
import importlib.util
import json
from pathlib import Path
import re
import unittest
import jinja2
import yaml

BASE = Path(__file__).resolve().parents[2] / 'configuration/packages/gitlab/events/metrics'
spec = importlib.util.spec_from_file_location('gitlab_metric_inputs', BASE / 'verify_inputs.py')
guard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)


def fixture():
    return dict(approved=True, context_id='portal', grafana_org_id=1, prometheus_uid='synthetic-prom',
                gitlab_url='https://gitlab.example.test',
                metric_projects=[dict(id=11, path='tenants/portal', refs=['main'], environments=['test'])],
                metric_incidents=[dict(uid='portal-main', project_id=11, project_path='tenants/portal',
                     event_class='pipeline', metric='gitlab_ci_pipeline_status',
                     selectors=dict(ref='main', kind='branch', source='push'))])


def render(filename, values):
    guard.verify(values)
    env = jinja2.Environment(undefined=jinja2.StrictUndefined)
    env.filters.update(to_json=json.dumps, regex_escape=re.escape)
    return yaml.safe_load(env.from_string((BASE / filename).read_text()).render(**values))


class GitLabMetrics(unittest.TestCase):
    def test_rule_is_paused_fixed_identity_and_retains_on_missing(self):
        rule = render('rules.yaml.j2', fixture())['groups'][0]['rules'][0]
        self.assertIs(rule['isPaused'], True)
        self.assertEqual(rule['noDataState'], 'KeepLast')
        self.assertEqual(rule['execErrState'], 'KeepLast')
        self.assertEqual(set(rule['labels']), {'context', 'project_id', 'event_class', 'incident_key'})
        expr = rule['data'][0]['model']['expr']
        self.assertIn('status="failed"} == 1)', expr)
        self.assertIn('status="success"} == 1)', expr)
        self.assertIn('or (0 * max(', expr)
        self.assertNotIn('or vector(0)', expr)

    def test_exporter_no_discovery_hooks_or_variables(self):
        config = render('exporter.yaml.j2', fixture())
        self.assertFalse(config['server']['webhook']['enabled'])
        self.assertEqual(config['wildcards'], [])
        self.assertNotIn('token', config['gitlab'])
        self.assertTrue(config['gitlab']['enable_tls_verify'])
        self.assertFalse(config['project_defaults']['pull']['pipeline']['variables']['enabled'])
        self.assertFalse(config['project_defaults']['pull']['pipeline']['jobs']['from_child_pipelines']['enabled'])
        self.assertEqual(config['projects'][0]['pull']['refs']['branches']['regexp'], '^(main)$')

    def test_unreviewed_input_rejected(self):
        changes = [('project_id', 99), ('project_id', True), ('project_path', 'other/project'),
                   ('metric', 'up'), ('event_class', 'vulnerability_findings')]
        for key, value in changes:
            values = fixture()
            values['metric_incidents'][0][key] = value
            with self.assertRaises(ValueError):
                render('rules.yaml.j2', values)
        values = fixture()
        values['metric_incidents'][0]['selectors']['context'] = 'other'
        with self.assertRaises(ValueError):
            render('rules.yaml.j2', values)

    def test_execution_and_deployment_use_exact_job_or_environment(self):
        for event, metric, selectors in [
            ('security_scan_execution', 'gitlab_ci_pipeline_job_status', dict(ref='main', kind='branch', source='push', stage='test', job_name='scanner')),
            ('deployment', 'gitlab_ci_environment_deployment_status', dict(environment='test'))]:
            values = fixture()
            values['metric_incidents'][0].update(event_class=event, metric=metric, selectors=selectors)
            expr = render('rules.yaml.j2', values)['groups'][0]['rules'][0]['data'][0]['model']['expr']
            self.assertIn(metric, expr)
            self.assertIn('project="tenants/portal"', expr)

    def test_regex_metacharacters_in_ref_are_literal(self):
        values = fixture()
        values['metric_projects'][0]['refs'] = ['release.1']
        values['metric_incidents'][0]['selectors']['ref'] = 'release.1'
        self.assertEqual(render('exporter.yaml.j2', values)['projects'][0]['pull']['refs']['branches']['regexp'], r'^(release\.1)$')


if __name__ == '__main__':
    unittest.main()
