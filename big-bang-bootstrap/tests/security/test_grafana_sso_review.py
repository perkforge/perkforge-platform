"""Pinned Grafana payload render and admission contract, not live login proof."""
from pathlib import Path
import unittest,yaml
from fixtures.observability import metrics_render
ROOT=Path(__file__).resolve().parents[2]
OVERLAY=ROOT/'configuration/observability/grafana-sso-values.yaml'
class GrafanaSSO(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.objects=metrics_render(ROOT,[OVERLAY])['grafana'][1]
 def test_protected_client_secret_and_public_ca_refs_render_without_material(self):
  deployment=next(x for x in self.objects if x['kind']=='Deployment');spec=deployment['spec']['template']['spec']
  self.assertTrue(any(x.get('secretRef',{}).get('name')=='grafana-oidc-client' for c in spec['containers'] for x in c.get('envFrom',[])))
  self.assertTrue(any(x.get('configMap',{}).get('name')=='grafana-identity-ca' for x in spec['volumes']))
  ini='\n'.join(str(v) for x in self.objects if x['kind']=='ConfigMap' for v in x.get('data',{}).values())
  self.assertIn('$__env{GRAFANA_OIDC_CLIENT_SECRET}',ini);self.assertIn('role_attribute_strict = true',ini);self.assertIn('use_pkce = true',ini)
  self.assertNotIn('client_secret = secret',ini)
 def test_unmatched_or_tenant_groups_are_not_given_platform_admin_by_fallback(self):
  c=yaml.safe_load(OVERLAY.read_text());self.assertFalse(c['grafana']['enabled']);self.assertTrue(c['grafana']['flux']['suspend'])
  u=c['grafana']['values']['upstream'];a=u['grafana.ini']['auth.generic_oauth']
  self.assertTrue(a['role_attribute_strict']);self.assertFalse(a['tls_skip_verify_insecure']);self.assertFalse(u['grafana.ini']['auth.anonymous']['enabled'])
  self.assertIn("contains(groups[*], '/platform/admins') && 'GrafanaAdmin'",a['role_attribute_path'])
  self.assertEqual(a['role_attribute_path'], "contains(groups[*], '/platform/admins') && 'GrafanaAdmin'")
  self.assertFalse(u['grafana.ini']['auth']['oauth_allow_insecure_email_lookup']);self.assertFalse(a['auto_login'])
  self.assertNotIn('/tenants/',a['role_attribute_path']);self.assertFalse(a['role_attribute_path'].endswith("|| 'Viewer'"))
  self.assertNotIn('org_mapping',a);self.assertFalse(u['grafana.ini']['auth']['disable_login_form'])
if __name__=='__main__':unittest.main()
