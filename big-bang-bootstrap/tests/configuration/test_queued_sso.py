"""Review contract checks, not live auth/login proof or a config generator."""
from pathlib import Path
import unittest,yaml
ROOT=Path(__file__).resolve().parents[2]
class QueuedSSO(unittest.TestCase):
 def test_contracts_stay_review_only_and_preserve_recovery(self):
  files=list((ROOT/'configuration/observability').glob('*sso-review.yaml'))+list((ROOT/'configuration/packages').glob('*/sso-review.yaml'))
  self.assertTrue(files)
  for p in files:
   with self.subTest(file=p.name):
    d=yaml.safe_load(p.read_text());self.assertFalse(d['enabled']);self.assertTrue(d['review_only']);self.assertEqual(d['live_apply_implemented'], d.get('application') == 'harbor')
    if d.get('application') == 'harbor': self.assertEqual(d['guarded_adapter'], '../../authorization/sso/harbor/README.md')
    self.assertTrue(d['recovery']['independent_local_access']);self.assertTrue(d['acceptance']['positive']);self.assertTrue(d['acceptance']['negative']);self.assertTrue(d['acceptance']['rollback'])
    self.assertIn(d['protocol'],['oidc','saml','kubernetes-rbac','machine-only'])
    if d['protocol'] in ['oidc','saml']:
     self.assertEqual(d['keycloak']['realm'],'perkforge');self.assertFalse(d['keycloak']['enabled'])
     self.assertNotIn('realm-admin',str(d['mappings']));self.assertFalse(d['mappings']['tenant_global_admin'])
     self.assertTrue(d['transport']['verify_tls']);self.assertFalse(d['transport']['skip_certificate_verification'])
 def test_machine_components_do_not_get_fake_browser_logins(self):
  d=yaml.safe_load((ROOT/'configuration/observability/sso-review.yaml').read_text())
  for name in ['prometheus','loki','alloy','alertmanager','ntfy','velero']:
   c=d['machine_components'][name];self.assertFalse(c['independent_browser_client']);self.assertTrue(c['scoped_machine_credentials'])
  self.assertEqual(d['machine_components']['velero']['operator_auth'],'kubernetes-api-rbac')
 def test_no_unimplemented_client_is_silently_accepted_by_existing_adapter(self):
  for p in list((ROOT/'configuration/observability').glob('*sso-review.yaml'))+list((ROOT/'configuration/packages').glob('*/sso-review.yaml')):
   d=yaml.safe_load(p.read_text())
   if d['protocol'] in ['oidc','saml']:self.assertIn('separate reviewed client/app apply wiring',d['activation_gates'])
if __name__=='__main__':unittest.main()
