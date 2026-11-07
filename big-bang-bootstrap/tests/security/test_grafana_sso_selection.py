"""Actual selected-root and pinned native renders; no live login/session proof."""
from copy import deepcopy
import configparser
import os
from pathlib import Path
import unittest

import yaml
from fixtures.render_helpers import build, child_values, helm, ordered_values, release_name

ROOT = Path(__file__).resolve().parents[2]
VALUES = ROOT / 'configuration/observability/grafana-sso/values.yaml'


def indexed(objects):
    return {(o['apiVersion'], o['kind'], o['metadata'].get('namespace'),
             o['metadata']['name']): o for o in objects}


class GrafanaSsoSelection(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.roots = {}
        cls.outer = {}
        cls.children = {}
        sources = Path(os.environ['PREFLIGHT_SOURCES_DIR'])
        for stage in ('local-harbor-app', 'local-grafana-sso'):
            objects = build(ROOT / 'clusters' / stage)
            cls.roots[stage] = indexed(objects)
            parent = next(o for o in objects if o['kind'] == 'HelmRelease' and o['metadata']['name'] == 'bigbang')
            outer = helm(sources / 'bigbang/chart', 'bigbang', 'bigbang', ordered_values(objects, parent))
            cls.outer[stage] = indexed(outer)
            hr = next(o for o in outer if o['kind'] == 'HelmRelease' and o['metadata']['name'] == 'grafana')
            cls.children[stage] = indexed(helm(sources / 'grafana/chart', release_name(hr),
                hr['spec']['targetNamespace'], child_values(outer, 'grafana')))

    def test_root_adds_only_public_values_and_one_final_reference(self):
        before, after = (deepcopy(x) for x in self.roots.values())
        key = ('v1', 'ConfigMap', 'bigbang', 'values-grafana-sso')
        self.assertEqual(set(after) - set(before), {key})
        self.assertEqual(yaml.safe_load(after.pop(key)['data']['values.yaml']), yaml.safe_load(VALUES.read_text()))
        parent = after[('helm.toolkit.fluxcd.io/v2', 'HelmRelease', 'bigbang', 'bigbang')]
        self.assertEqual(parent['spec']['valuesFrom'].pop(),
            {'kind': 'ConfigMap', 'name': 'values-grafana-sso', 'valuesKey': 'values.yaml'})
        self.assertEqual(before, after)
        payload = yaml.safe_load(VALUES.read_text())
        self.assertEqual(set(payload), {'grafana'})
        self.assertEqual(set(payload['grafana']), {'values'})

    def test_pinned_umbrella_preserves_every_other_app_and_grafana_lifecycle(self):
        before, after = (deepcopy(x) for x in self.outer.values())
        self.assertEqual(before.keys(), after.keys())
        changed = {key for key in before if before[key] != after[key]}
        self.assertEqual({k[3] for k in changed}, {'bigbang-grafana-values', 'grafana'})
        key = ('helm.toolkit.fluxcd.io/v2', 'HelmRelease', 'bigbang', 'grafana')
        for objects in (before, after):
            self.assertFalse(objects[key]['spec']['suspend'])
            objects[key]['metadata']['annotations'].pop('checksum/bigbang-values')
        self.assertEqual(before[key], after[key])

    def test_pinned_child_changes_only_configuration_mount_and_rollout_checksum(self):
        before, after = (deepcopy(x) for x in self.children.values())
        self.assertEqual(before.keys(), after.keys())
        changed = {key for key in before if before[key] != after[key]}
        self.assertEqual({k[1] for k in changed}, {'Deployment', 'ConfigMap'})
        for key in changed:
            if key[1] == 'ConfigMap':
                self.assertEqual(before[key]['data'].keys(), after[key]['data'].keys())
                before[key]['data'].pop('grafana.ini')
                after[key]['data'].pop('grafana.ini')
                continue
            old, new = before[key]['spec']['template'], after[key]['spec']['template']
            for template in (old, new):
                template['metadata']['annotations'].pop('checksum/config')
            volume = {'name': 'identity-ca', 'configMap': {'name': 'grafana-identity-ca'}}
            self.assertIn(volume, new['spec']['volumes'])
            new['spec']['volumes'].remove(volume)
            old_main = next(c for c in old['spec']['containers'] if c['name'] == 'grafana')
            main = next(c for c in new['spec']['containers'] if c['name'] == 'grafana')
            self.assertEqual(main.pop('envFrom'), [{'secretRef': {'name': 'grafana-oidc-client'}}])
            main['volumeMounts'].remove({'name': 'identity-ca', 'mountPath': '/etc/grafana/identity', 'subPath': None, 'readOnly': True})
            self.assertEqual(main, old_main)
        self.assertEqual(before, after)

    def test_native_configuration_and_source_rollback_keep_local_recovery(self):
        for stage, objects in self.children.items():
            ini = next(o['data']['grafana.ini'] for o in objects.values()
                       if o['kind'] == 'ConfigMap' and 'grafana.ini' in o.get('data', {}))
            config = configparser.ConfigParser(interpolation=None)
            config.read_string(ini)
            self.assertEqual(config['server']['root_url'], 'https://grafana.perkforge.home.arpa/')
            self.assertEqual(config['security']['cookie_secure'], 'true')
            self.assertEqual(config['auth.anonymous']['enabled'], 'false')
            if stage == 'local-harbor-app':
                self.assertEqual(config['auth.generic_oauth']['enabled'], 'false')
                self.assertNotIn('GRAFANA_OIDC_CLIENT_SECRET', ini)
                continue
            auth = config['auth.generic_oauth']
            self.assertEqual(auth['enabled'], 'true')
            self.assertEqual(auth['auto_login'], 'false')
            self.assertEqual(config['auth']['disable_login_form'], 'false')
            self.assertEqual(config['auth']['oauth_allow_insecure_email_lookup'], 'false')
            self.assertEqual(config['auth.basic']['enabled'], 'true')
            self.assertEqual(auth['client_id'], 'grafana')
            self.assertEqual(auth['client_secret'], '$__env{GRAFANA_OIDC_CLIENT_SECRET}')
            issuer = 'https://keycloak.perkforge.home.arpa/auth/realms/perkforge'
            for key, endpoint in [('auth_url', 'auth'), ('token_url', 'token'), ('api_url', 'userinfo')]:
                self.assertEqual(auth[key], issuer + '/protocol/openid-connect/' + endpoint)
            self.assertEqual(auth['tls_client_ca'], '/etc/grafana/identity/ca.crt')
            self.assertEqual(auth['tls_skip_verify_insecure'], 'false')
            self.assertEqual(auth['use_pkce'], 'true')
            self.assertEqual(auth['role_attribute_strict'], 'true')
            self.assertEqual(auth['skip_org_role_sync'], 'false')
            self.assertEqual(auth['allow_assign_grafana_admin'], 'true')
            self.assertNotIn('org_mapping', auth)

    def test_only_exact_own_client_admin_claim_maps_to_role(self):
        # Required at execution, not during CI impact/discovery-only audits.
        import jmespath

        auth = yaml.safe_load(VALUES.read_text())['grafana']['values']['upstream']['grafana.ini']['auth.generic_oauth']
        expression = auth['role_attribute_path']
        self.assertEqual(expression, "contains(groups[*], '/platform/admins') && 'GrafanaAdmin'")
        self.assertEqual(jmespath.search(expression, {'groups': ['/platform/admins']}), 'GrafanaAdmin')
        self.assertEqual(jmespath.search(expression, {'groups': ['/platform/admins', '/platform/viewers']}), 'GrafanaAdmin')
        for groups in ([], ['/platform/viewers'], ['/platform/engineers'], ['/tenants/a/admins'],
                       ['/platform/admins-extra'], ['admins'], ['/Platform/admins'], [None], None, '/platform/admins', {'role': '/platform/admins'}):
            with self.subTest(groups=groups):
                try:
                    result = jmespath.search(expression, {'groups': groups})
                except jmespath.exceptions.JMESPathTypeError:
                    result = None  # Strict native role extraction rejects malformed claims.
                self.assertNotIn(result, ('GrafanaAdmin', 'Admin', 'Editor', 'Viewer'))
        with self.assertRaises(jmespath.exceptions.JMESPathTypeError):
            jmespath.search(expression, {})
        review = yaml.safe_load((ROOT / 'configuration/observability/grafana-sso-values.yaml').read_text())
        self.assertEqual(review['grafana']['values']['upstream']['grafana.ini']['auth.generic_oauth']['role_attribute_path'], expression)


if __name__ == '__main__':
    unittest.main()
