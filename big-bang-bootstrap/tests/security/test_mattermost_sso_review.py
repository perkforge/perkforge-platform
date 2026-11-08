from pathlib import Path
import unittest,yaml
from fixtures.collaboration import package_render
ROOT=Path(__file__).resolve().parents[2]
class MattermostSSO(unittest.TestCase):
 def test_other_oidc_reference_renders_without_gitlab_shortcut_or_license(self):
  path=ROOT/'configuration/packages/mattermost/sso-values.yaml';d=yaml.safe_load(path.read_text())['addons']['mattermost'];self.assertFalse(d['enabled']);self.assertTrue(d['flux']['suspend']);self.assertFalse(d['values']['sso']['enabled'])
  _,objects=package_render(ROOT,'mattermost',('mattermost-operator',),extra_values=(path,))['mattermost']
  cr=next(x for x in objects if x['kind']=='Mattermost');env={x['name']:x for x in cr['spec']['mattermostEnv']}
  self.assertEqual(env['MM_GITLABSETTINGS_ENABLE']['value'],'false');self.assertEqual(env['MM_OPENIDSETTINGS_ENABLE']['value'],'true')
  self.assertEqual(env['MM_OPENIDSETTINGS_SECRET']['valueFrom']['secretKeyRef']['name'],'mattermost-oidc-client')
  self.assertEqual(env['SSL_CERT_FILE']['value'],'/etc/mattermost-identity-ca/ca.crt')
  self.assertEqual(cr['spec']['volumes'],[{'name':'identity-ca','configMap':{'name':'mattermost-identity-ca'}}])
  self.assertEqual(cr['spec']['volumeMounts'],[{'name':'identity-ca','mountPath':'/etc/mattermost-identity-ca','readOnly':True}])
  self.assertEqual(env['MM_SERVICESETTINGS_ENABLEUSERCREATION']['value'],'false');self.assertNotIn('licenseSecret',cr['spec'])
 def test_entry_edition_and_membership_are_not_claimed_live_or_verified(self):
  d=yaml.safe_load((ROOT/'configuration/packages/mattermost/sso-review.yaml').read_text());self.assertFalse(d['edition_verified']);self.assertFalse(d['live_apply_implemented'])
  self.assertEqual(d['pinned_image_version'],'11.11.0');self.assertIn('own Team Admin',d['mappings']['tenant_admin']);self.assertFalse(d['mappings']['tenant_global_admin'])
 def test_pinned_source_evidence_matches_rendered_image_without_runtime_claim(self):
  p=ROOT/'configuration/packages/mattermost';e=yaml.safe_load((p/'ironbank-11.11.0-source.yaml').read_text())
  d=yaml.safe_load((p/'sso-review.yaml').read_text())
  self.assertTrue(d['source_edition_verified']);self.assertFalse(d['runtime_edition_verified'])
  self.assertEqual(e['tags'],[d['pinned_image_version']])
  archive=next(x for x in e['resources'] if x['filename']=='mattermost.tar.gz')
  self.assertEqual(archive['url'],'https://releases.mattermost.com/11.11.0/mattermost-11.11.0-linux-amd64.tar.gz')
  self.assertEqual(archive['validation']['value'],'03dfa47063849fe9e799c9523c56c74ec19852948e6fc42d9fc3e10cc5d95bc9')
  _,objects=package_render(ROOT,'mattermost',('mattermost-operator',))['mattermost']
  cr=next(x for x in objects if x['kind']=='Mattermost')
  self.assertEqual(cr['spec']['version'],d['pinned_image_version'])
  self.assertNotIn('licenseSecret',cr['spec'])
if __name__=='__main__':unittest.main()
