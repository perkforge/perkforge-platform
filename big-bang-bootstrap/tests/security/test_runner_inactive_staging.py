import subprocess,unittest
from pathlib import Path
import yaml
R=Path(__file__).resolve().parents[2]
class Staging(unittest.TestCase):
 def test_exact_inactive_inventory(self):
  d=[x for x in yaml.safe_load_all(subprocess.check_output(['kubectl','kustomize',str(R/'configuration/tenant-runner/staging')],text=True)) if x]
  self.assertEqual(len(d),2);self.assertEqual({x['metadata']['name'] for x in d},{'portal-runner-runtime','portal-runner-manager'})
  for x in d:
   self.assertEqual(x['kind'],'Kustomization');self.assertEqual(x['apiVersion'],'kustomize.toolkit.fluxcd.io/v1');self.assertEqual(x['metadata']['namespace'],'flux-system')
   self.assertTrue(x['spec']['suspend']);self.assertFalse(x['spec']['prune']);self.assertFalse(x['spec']['force'])
  s=yaml.safe_load((R/'configuration/tenant-runner/setup/staging-root.yaml').read_text())['spec']
  self.assertFalse(s['wait']);self.assertFalse(s['suspend']);self.assertFalse(s['prune']);self.assertFalse(s['force']);self.assertEqual(s['serviceAccountName'],'platform-reconciler')
  self.assertEqual(s['path'],'./big-bang-bootstrap/configuration/tenant-runner/staging')
  self.assertNotIn('postBuild',s)
if __name__=='__main__':unittest.main()
