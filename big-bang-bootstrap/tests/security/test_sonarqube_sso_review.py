from pathlib import Path
import unittest,yaml
from fixtures.collaboration import package_render
ROOT=Path(__file__).resolve().parents[2]
class SonarSSO(unittest.TestCase):
 def test_native_saml_and_external_certificate_ref_without_metadata_hook_or_rbac(self):
  path=ROOT/'configuration/packages/sonarqube/sso-values.yaml';d=yaml.safe_load(path.read_text())['addons']['sonarqube'];self.assertFalse(d['enabled']);self.assertTrue(d['flux']['suspend']);self.assertFalse(d['values']['sso']['enabled'])
  hr,objects=package_render(ROOT,'sonarqube',extra_values=(path,))['sonarqube'];self.assertTrue(hr['spec']['suspend'])
  properties='\n'.join(str(v) for x in objects if x['kind']=='ConfigMap' for v in x.get('data',{}).values());self.assertIn('sonar.auth.saml.enabled=true',properties)
  pod=next(x for x in objects if x['kind']=='StatefulSet')['spec']['template']['spec']
  self.assertTrue(any(x.get('secret',{}).get('secretName')=='sonarqube-saml-identity' for x in pod['volumes']))
  self.assertFalse(any(x['kind'] in ['Role','ClusterRole','RoleBinding','ClusterRoleBinding'] for x in objects))
  self.assertFalse(any(x['kind']=='Job' and 'sso' in x['metadata']['name'] for x in objects))
 def test_saml_limits_and_explicit_project_permissions_are_not_overstated(self):
  d=yaml.safe_load((ROOT/'configuration/packages/sonarqube/sso-review.yaml').read_text());self.assertEqual(d['protocol'],'saml')
  self.assertFalse(d['keycloak']['enabled']);self.assertTrue(d['keycloak']['sp_initiated']);self.assertFalse(d['keycloak']['idp_initiated']);self.assertFalse(d['keycloak']['single_logout'])
  self.assertFalse(d['mappings']['tenant_global_admin']);self.assertFalse(d['live_apply_implemented'])
if __name__=='__main__':unittest.main()
