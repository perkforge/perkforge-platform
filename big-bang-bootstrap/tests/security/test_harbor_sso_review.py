from pathlib import Path
import unittest,yaml
ROOT=Path(__file__).resolve().parents[2]
class HarborSSO(unittest.TestCase):
 def test_public_proposal_requires_verified_idp_and_exact_admin_group(self):
  d=yaml.safe_load((ROOT/'configuration/packages/harbor/sso-review.yaml').read_text());n=d['native_configuration']
  self.assertFalse(d['enabled']);self.assertFalse(d['live_apply_implemented']);self.assertFalse(d['keycloak']['enabled'])
  self.assertEqual(n['auth_mode'],'oidc_auth');self.assertTrue(n['oidc_verify_cert']);self.assertEqual(n['oidc_admin_group'],'/platform/admins')
  self.assertNotIn('oidc_client_secret',n);self.assertEqual(n['project_creation_restriction'],'adminonly');self.assertFalse(d['mappings']['tenant_global_admin'])
 def test_migration_and_filter_limitations_cannot_be_claimed_away(self):
  d=yaml.safe_load((ROOT/'configuration/packages/harbor/sso-review.yaml').read_text());s=' '.join(d['limitations'])
  self.assertIn('not who may log in',s);self.assertIn('local non-admin users',s);self.assertIn('not implemented',s)
if __name__=='__main__':unittest.main()
