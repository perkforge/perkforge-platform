from pathlib import Path
import unittest,yaml
from fixtures.collaboration import package_render
ROOT=Path(__file__).resolve().parents[2]
class GitLabSSO(unittest.TestCase):
 def test_native_overlay_references_secret_and_blocks_unapproved_onboarding(self):
  path=ROOT/'configuration/packages/gitlab/sso-values.yaml';d=yaml.safe_load(path.read_text())['addons']['gitlab'];self.assertFalse(d['enabled']);self.assertTrue(d['flux']['suspend'])
  a=d['values']['global']['appConfig']['omniauth'];self.assertTrue(a['blockAutoCreatedUsers']);self.assertEqual(a['autoLinkUser'],[])
  hr,objects=package_render(ROOT,'gitlab',extra_values=(path,))['gitlab']
  self.assertIn('gitlab-oidc-provider',yaml.safe_dump(objects));self.assertIn('gitlab-platform-public-ca',yaml.safe_dump(objects));self.assertTrue(hr['spec']['suspend'])
  for key in ['required_groups','admin_groups','auditor_groups']:self.assertNotIn(key,yaml.safe_dump(a))
 def test_review_does_not_claim_free_group_sync_or_embed_client_secret(self):
  d=yaml.safe_load((ROOT/'configuration/packages/gitlab/sso-review.yaml').read_text());self.assertFalse(d['keycloak']['enabled'])
  self.assertNotIn('secret',d['native_provider_public_fields']['args']['client_options'])
  self.assertFalse(d['mappings']['tenant_global_admin']);self.assertIn('OIDC does not add GitLab group membership',d['limitations'])
class NamedAdminAcceptance(unittest.TestCase):
 def test_exact_named_identity_and_explicit_native_admin(self):
  import importlib.util,copy
  spec=importlib.util.spec_from_file_location('gitlab_native_access',ROOT/'configuration/packages/gitlab/verification/native_access.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
  expected={'user_id':42,'provider':'openid_connect','subject':'stable-subject'}
  user={'id':42,'username':'named-admin','state':'active','is_admin':True,'identities':[{'provider':'openid_connect','extern_uid':'stable-subject'}]}
  self.assertEqual(m.verify_platform_admin(expected,user),{'named_native_admin_verified':True,'fresh_mfa_verified':False})
  for change in ({'id':True},{'id':43},{'username':'root'},{'state':'blocked'},{'is_admin':False},{'is_admin':1},{'identities':[]},{'identities':[{'provider':'openid_connect','extern_uid':'wrong'}]},{'identities':user['identities']*2}):
   with self.subTest(change=change),self.assertRaises(ValueError):m.verify_platform_admin(expected,{**user,**change})
  for change in ({'user_id':True},{'user_id':0},{'subject':''},{'provider':'saml'}):
   with self.subTest(change=change),self.assertRaises(ValueError):m.verify_platform_admin({**expected,**change},user)

if __name__=='__main__':unittest.main()
