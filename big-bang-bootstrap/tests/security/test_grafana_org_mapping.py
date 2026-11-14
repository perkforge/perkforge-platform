"""Offline renderer contract. Native OAuth acceptance lives in integration fixture."""
import copy
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
import yaml
ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / 'big-bang-bootstrap/configuration/authorization/sso/grafana/orgs'
CONTEXT = ROOT / 'big-bang-bootstrap/configuration/authorization/contexts/portal.yaml'

class GrafanaOrgMapping(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.folder = Path(self.tmp.name)
        context = yaml.safe_load(CONTEXT.read_text())['paas_context']
        self.inputs = {'grafana_org_render': True, 'grafana_org_output': str(self.folder / 'out'),
                       'grafana_org_contexts': [{'context':context, 'org_id':2, 'query_identity':'pf-log-portal-read'}]}

    def render(self, inputs, check=False):
        result = subprocess.run(['ansible-playbook', '-i', 'localhost,', str(SOURCE/'render.yaml'), '-e', json.dumps(inputs)] + (['--check'] if check else []),
                                env=dict(os.environ, KUBECONFIG='/dev/null'), capture_output=True, text=True)
        return result

    def test_disabled_and_check_inert(self):
        self.assertEqual(self.render({}).returncode, 0)
        self.assertEqual(self.render(self.inputs, True).returncode, 0)
        self.assertFalse((self.folder/'out').exists())

    def test_exact_scoped_mapping(self):
        result = self.render(self.inputs); self.assertEqual(result.returncode, 0, result.stdout+result.stderr)
        oauth = yaml.safe_load((self.folder/'out/oauth.yaml').read_text())
        self.assertFalse(oauth['enabled'])
        self.assertIn("contains(groups[*], '/platform/admins') && 'GrafanaAdmin'", oauth['role_attribute_path'])
        self.assertTrue(oauth['role_attribute_path'].strip().endswith(") && 'None'"))
        self.assertIn('pf-observability-portal-tenant-admin:2:Admin', oauth['org_mapping'])
        self.assertIn('pf-observability-platform-viewer:1:Viewer', oauth['org_mapping'])
        self.assertNotIn('*', oauth['org_mapping'])
        entitlement = yaml.safe_load((self.folder/'out/entitlements.yaml').read_text())
        self.assertFalse(entitlement['activation'])
        self.assertEqual(entitlement['contexts'][0]['mappings'][0]['canonical_group'], '/tenants/portal/admins')

    def test_collisions_and_noncanonical_context_fail(self):
        variants = []
        for key, value in [('org_id',1), ('org_id','2'), ('query_identity','pf-log-platform-read')]:
            data = copy.deepcopy(self.inputs); data['grafana_org_contexts'][0][key] = value; variants.append(data)
        data = copy.deepcopy(self.inputs); data['grafana_org_contexts'] *= 2; variants.append(data)
        data = copy.deepcopy(self.inputs); data['grafana_org_contexts'][0]['context']['keycloak']['groups']['tenant-admin']='/platform/admins'; variants.append(data)
        for data in variants:
            with self.subTest(data=data): self.assertNotEqual(self.render(data).returncode, 0)
        self.assertFalse((self.folder/'out').exists())

    def test_platform_only_is_explicit_and_refuses_tenant_mappings(self):
        inputs=self.inputs | {'grafana_org_contexts':[], 'grafana_org_platform_only':True}
        result=self.render(inputs); self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        oauth=yaml.safe_load((self.folder/'out/oauth.yaml').read_text())
        self.assertEqual(oauth['org_mapping'].split(),['/platform/admins:1:Admin','pf-observability-platform-viewer:1:Viewer'])
        self.assertNotIn('tenant-',oauth['role_attribute_path'])
        overlay=yaml.safe_load((self.folder/'out/oauth-values.yaml').read_text())
        section=overlay['grafana']['values']['upstream']['grafana.ini']['auth.generic_oauth']
        self.assertEqual(set(section),{'role_attribute_path','org_attribute_path','org_mapping'})
        self.assertEqual(section,{k:oauth[k] for k in section})
        baseline={'enabled':True,'client_id':'grafana','client_secret':'existing-reference','tls_skip_verify_insecure':False,'use_pkce':True,'role_attribute_strict':True}
        self.assertEqual((baseline | section)['client_secret'],'existing-reference')
        self.assertTrue((baseline | section)['enabled'])

        self.assertNotEqual(self.render(self.inputs | {'grafana_org_platform_only':True}).returncode,0)
