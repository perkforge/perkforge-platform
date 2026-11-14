"""Offline contract tests, not live authorization evidence."""
from copy import deepcopy
import importlib.util
from pathlib import Path
import subprocess
import tempfile
import unittest
import yaml

ROOT = Path(__file__).resolve().parents[2]
CONTEXT = ROOT / 'configuration/authorization/contexts'
spec = importlib.util.spec_from_file_location('paas_context_verify', CONTEXT / 'verify.py')
verify = importlib.util.module_from_spec(spec)
spec.loader.exec_module(verify)


class ContextContractTest(unittest.TestCase):
    def setUp(self):
        self.document = yaml.safe_load((CONTEXT / 'portal.yaml').read_text())
        self.c = self.document['paas_context']

    def test_approved_portal_is_inactive(self):
        self.assertEqual(verify.load(CONTEXT / 'portal.yaml')['id'], 'portal')
        self.assertIs(self.c['activation'], False)
        self.assertEqual(self.c['targets']['mattermost'], {'team_name': 'perkforge', 'channel_name': 'portal-alerts', 'channel_type': 'P'})
        self.assertEqual(self.c['kubernetes']['runtime_namespaces'], ['tenant-portal'])
        self.assertEqual(self.c['kubernetes']['control_namespaces'], ['tenant-portal-config', 'tenant-portal-release'])

    def test_rejects_activation_unknown_fields_and_schemas(self):
        for key, value in [('activation', True), ('activation', 'false'), ('schema_version', True), ('schema_version', 2), ('members', ['anybody'])]:
            with self.subTest(key=key, value=value):
                doc = deepcopy(self.document)
                doc['paas_context'][key] = value
                with self.assertRaises(verify.ContractError):
                    verify.validate(doc)

    def test_rejects_ambiguous_or_reserved_contexts(self):
        for value in ['', '*', '../portal', 'portal/other', True, 'platform', 'system']:
            with self.subTest(value=value):
                self.c['id'] = value
                with self.assertRaises(verify.ContractError):
                    verify.validate(self.document)

    def test_rejects_other_tenant_or_platform_groups(self):
        for value in ['/tenants/other/admins', '/platform/admins', '/tenants/portal', '*']:
            with self.subTest(value=value):
                self.c['keycloak']['groups']['tenant-admin'] = value
                with self.assertRaises(verify.ContractError):
                    verify.validate(self.document)

    def test_rejects_control_namespace_exposure_and_cross_context_names(self):
        for value in [['tenant-portal-config'], ['tenant-portal-release'], ['tenant-other'], ['kube-system'], ['tenant-portal', 'tenant-portal'], 'tenant-portal', []]:
            with self.subTest(value=value):
                self.c['kubernetes']['runtime_namespaces'] = value
                with self.assertRaises(verify.ContractError):
                    verify.validate(self.document)

    def test_rejects_namespace_overlap(self):
        self.c['kubernetes']['control_namespaces'] = ['tenant-portal']
        with self.assertRaises(verify.ContractError):
            verify.validate(self.document)

    def test_rejects_topic_and_channel_escape(self):
        cases = [('ntfy', 'topic', '*'), ('ntfy', 'topic', 'platform-alerts'), ('mattermost', 'channel_type', 'O'), ('mattermost', 'team_name', 'platform'), ('mattermost', 'team_name', None), ('mattermost', 'channel_name', 'other-alerts'), ('mattermost', 'channel_name', 'town-square')]
        for target, key, value in cases:
            with self.subTest(target=target, key=key, value=value):
                doc = deepcopy(self.document)
                doc['paas_context']['targets'][target][key] = value
                with self.assertRaises(verify.ContractError):
                    verify.validate(doc)

    def test_rejects_assumed_grafana_and_gitlab_grants(self):
        for target, key, value in [('grafana', 'access', 'viewer'), ('gitlab', 'group_id', 1), ('gitlab', 'project_ids', [1])]:
            with self.subTest(target=target):
                doc = deepcopy(self.document)
                doc['paas_context']['targets'][target][key] = value
                with self.assertRaises(verify.ContractError):
                    verify.validate(doc)

    def test_rejects_unapproved_role_escalation(self):
        for target, role in [('grafana', 'Admin'), ('gitlab', 'Owner')]:
            with self.subTest(target=target):
                doc = deepcopy(self.document)
                doc['paas_context']['targets'][target]['role_mappings']['tenant-viewer'] = role
                with self.assertRaises(verify.ContractError):
                    verify.validate(doc)

    def test_rejects_duplicate_yaml_keys(self):
        with self.assertRaises(verify.ContractError):
            yaml.load('id: portal\nid: other\n', Loader=verify.UniqueLoader)

    def test_rejects_duplicate_context_inventory(self):
        with self.assertRaises(verify.ContractError):
            verify.validate_all([CONTEXT / 'portal.yaml', CONTEXT / 'portal.yaml'])

    def test_cli_rejects_bad_input_without_traceback(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'bad.yaml'
            path.write_text('paas_context: null\n')
            result = subprocess.run(['python3', '-B', str(CONTEXT / 'verify.py'), str(path)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 1)
        self.assertIn('Invalid context:', result.stderr)
        self.assertNotIn('Traceback', result.stderr)

    def test_cli_is_offline_and_validates_checked_in_context(self):
        result = subprocess.run(['python3', '-B', str(CONTEXT / 'verify.py'), str(CONTEXT / 'portal.yaml')], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('no APIs or grants', result.stdout)


if __name__ == '__main__':
    unittest.main()
