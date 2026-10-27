"""Equivalence to the pre-template f864817 renderer, plus template safety checks."""
import hashlib
import json
from pathlib import Path
import subprocess
import os
import unittest

import yaml
import test_portal_catalog_lifecycle as lifecycle
import portal_application
import tenant_templates

FIXTURE = Path(__file__).parent / 'fixtures/portal/template-baseline.json'


def canonical_documents(text):
    objects = list(yaml.safe_load_all(text))
    for obj in objects:
        if obj.get('kind') == 'ConfigMap' and 'values.yaml' in obj.get('data', {}):
            obj['data']['values.yaml'] = yaml.safe_load(obj['data']['values.yaml'])
    return sorted(objects, key=lambda o: (o.get('apiVersion', ''), o.get('kind', ''),
                  o.get('metadata', {}).get('namespace', ''), o.get('metadata', {}).get('name', '')))


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=True).encode()).hexdigest()


class SharedTemplateTests(unittest.TestCase):
    def test_all_lifecycle_outputs_match_pre_refactor_semantics(self):
        # Frozen before moving resource construction to Helm. Only document order
        # and the embedded values YAML's presentation are normalized; CEL is exact.
        cases = lifecycle.PortalCatalogLifecycleTests()
        cases.setUp()
        expected = json.loads(FIXTURE.read_text())
        for state in ('disabled', 'active', 'paused'):
            with self.subTest(state=state):
                catalog = cases.catalog if state == 'disabled' else cases.provisioned(state)
                self.assertEqual(digest(canonical_documents(lifecycle.foundation.render(catalog))), expected[state]['foundation'])
                for name, text in portal_application.outputs(portal_application.contract_for(catalog)).items():
                    value = canonical_documents(text) if name == 'resources.yaml' else yaml.safe_load(text)
                    self.assertEqual(digest(value), expected[state]['portal'][name], name)

    def test_chart_defaults_emit_nothing(self):
        result = subprocess.run([os.environ.get('HELM', 'helm'), 'template', 'review', str(tenant_templates.CHART)],
                                check=True, capture_output=True, text=True)
        self.assertEqual(list(yaml.safe_load_all(result.stdout)), [])

    def test_template_inputs_are_data_not_template_code_or_yaml(self):
        contract = portal_application.load_contract()
        # Exercise quoting without trusting validation as an escaping mechanism.
        value = 'https://example.test/"\nextra: {{ fail "do not evaluate values" }}'
        contract['identity']['issuer'] = value
        contract['identity']['clientId'] = 'null'
        values = portal_application.helm_values(contract)
        self.assertEqual(values['identity']['issuer'], value)
        self.assertEqual(values['identity']['clientId'], 'null')
        self.assertNotIn('extra', values)
        plan = portal_application.identity_plan(contract)
        self.assertEqual(plan['clients'][0]['clientId'], 'null')
