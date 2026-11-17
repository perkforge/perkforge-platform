import subprocess,unittest
from pathlib import Path
import yaml
ROOT=Path(__file__).resolve().parents[2]
class Selection(unittest.TestCase):
 def test_inheritance_and_inactive_boundaries(self):
  def build(path):return [x for x in yaml.safe_load_all(subprocess.check_output(['kubectl','kustomize',str(ROOT/path)],text=True)) if x]
  old=build('clusters/local-identity-onboarding');new=build('clusters/local-portal-runner')
  self.assertEqual(len(new),len(old)+2)
  for obj in old:self.assertIn(obj,new)
  added=[x for x in new if x not in old]
  self.assertEqual({x['metadata']['name'] for x in added},{'portal-runner-runtime','portal-runner-manager'})
  for x in added:
   s=x['spec'];self.assertTrue(s['suspend']);self.assertFalse(s['prune']);self.assertFalse(s['force'])
   if 'postBuild' in s:self.assertEqual(x['metadata']['name'],'portal-runner-runtime')
  runtime=build('configuration/tenant-runner/portal/runtime');self.assertNotIn('192.168.',str(runtime))
  for x in runtime:
   if x['kind']!='NetworkPolicy':self.assertEqual(x['metadata']['namespace'],'gitlab-tenant-portal-runner')
  ownership=list(yaml.safe_load_all((ROOT/'configuration/tenant-runner/setup/source-ownership.yaml').read_text()))
  for obj in ownership:
   if obj['kind']=='Role':
    for rule in obj['rules']:
     self.assertTrue(rule['resourceNames']);self.assertFalse(set(rule['verbs']) & {'create','delete','bind','escalate'});self.assertNotIn('secrets',rule['resources'])
  release=build('configuration/tenant-runner/portal/manager');self.assertTrue(next(x for x in release if x['kind']=='HelmRelease')['spec']['suspend'])
if __name__=='__main__':unittest.main()
