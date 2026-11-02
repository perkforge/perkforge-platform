"""Render the selected SSO stage offline, including actual pinned child templates."""
from copy import deepcopy
import os
from pathlib import Path
import unittest

import yaml
from fixtures.render_helpers import build, child_values, helm, ordered_values, release_name

ROOT = Path(__file__).resolve().parents[2]


def indexed(objects):
    return {(o['apiVersion'], o['kind'], o['metadata'].get('namespace'),
             o['metadata']['name']): o for o in objects}


class HeadlampSsoSelection(unittest.TestCase):
    def test_only_final_headlamp_values_change_and_match_reviewed_adapter(self):
        before = indexed(build(ROOT / 'clusters/local-keycloak'))
        after = indexed(build(ROOT / 'clusters/local-headlamp-sso'))
        self.assertEqual(before.keys(), after.keys())
        changed = [k for k in before if before[k] != after[k]]
        self.assertEqual(changed, [('v1', 'ConfigMap', 'bigbang', 'values-app-stage')])
        prior = yaml.safe_load(before[changed[0]]['data']['values.yaml'])
        selected = yaml.safe_load(after[changed[0]]['data']['values.yaml'])
        # The Jinja template's gitops_values fragment contains no substitutions.
        template = (ROOT / 'configuration/authorization/sso/templates/headlamp.yaml.j2').read_text()
        contract = yaml.safe_load(template.split('\ngitops_values:\n', 1)[1])
        expected = deepcopy(prior)
        expected['addons']['headlamp']['values'] = contract['addons']['headlamp']['values']
        self.assertEqual(selected, expected)
        self.assertTrue(selected['addons']['keycloak']['enabled'])
        self.assertTrue(selected['addons']['headlamp']['enabled'])
        for stage in ('local', 'local-headlamp', 'local-keycloak'):
            values = yaml.safe_load((ROOT / 'clusters' / stage / 'values.yaml').read_text())
            self.assertNotIn('oidc', values.get('addons', {}).get('headlamp', {}).get('values', {}).get('upstream', {}).get('config', {}))
        # Source addition does not repin the seed or authorize a rollout.
        defaults = yaml.safe_load((ROOT / 'configuration/ansible/inventory.yaml').read_text())
        self.assertFalse(defaults['all']['children']['bootstrap_clusters']['vars']['bootstrap_apply'])

    def test_pinned_child_uses_only_external_credentials_and_public_trust(self):
        sources = Path(os.environ['PREFLIGHT_SOURCES_DIR'])
        outputs = {}
        for stage in ('local-keycloak', 'local-headlamp-sso'):
            objects = build(ROOT / 'clusters' / stage)
            parent = next(o for o in objects if o['kind'] == 'HelmRelease')
            self.assertEqual(parent['spec']['valuesFrom'][-1]['name'], 'values-app-stage')
            outer = helm(sources / 'bigbang/chart', 'bigbang', 'bigbang', ordered_values(objects, parent))
            outputs[stage] = indexed(outer)
            if stage == 'local-keycloak':
                continue
            hr = next(o for o in outer if o['kind'] == 'HelmRelease' and o['metadata']['name'] == 'headlamp')
            child = helm(sources / 'headlamp/chart', release_name(hr), 'headlamp', child_values(outer, 'headlamp'))
            self.assertFalse(any(o['kind'] in ('Secret', 'ClusterRoleBinding') for o in child))
            pod = next(o for o in child if o['kind'] == 'Deployment')['spec']['template']['spec']
            container = pod['containers'][0]
            self.assertIn({'secretRef': {'name': 'perkforge-headlamp-sso-v1'}}, container['envFrom'])
            self.assertIn({'name': 'SSL_CERT_FILE', 'value': '/identity-ca/ca.crt'}, container['env'])
            self.assertIn('-oidc-ca-file=/identity-ca/ca.crt', container['args'])
            self.assertIn({'name': 'identity-ca', 'configMap': {'name': 'perkforge-headlamp-sso-v1-ca'}}, pod['volumes'])
            self.assertIn({'name': 'identity-ca', 'mountPath': '/identity-ca', 'readOnly': True}, container['volumeMounts'])
            self.assertFalse(any('unsafe-use-service-account-token' in x for x in container['args']))
        before, after = outputs.values()
        self.assertEqual(before.keys(), after.keys())
        changed = {k[3] for k in before if before[k] != after[k]}
        self.assertEqual(changed, {'bigbang-headlamp-values', 'headlamp'})
        key = ('helm.toolkit.fluxcd.io/v2', 'HelmRelease', 'bigbang', 'headlamp')
        old_hr, new_hr = deepcopy(before[key]), deepcopy(after[key])
        for hr in (old_hr, new_hr):
            hr['metadata']['annotations'].pop('checksum/bigbang-values')
        self.assertEqual(old_hr, new_hr)
