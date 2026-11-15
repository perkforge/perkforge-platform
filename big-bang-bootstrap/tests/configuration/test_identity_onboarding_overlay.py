import copy,pathlib,subprocess,unittest,yaml
ROOT=pathlib.Path(__file__).resolve().parents[2]
A='8b04be30c091eb92a2bc029945182ff0179f3e4e';B='4bd027f1b0bc8f352f56cf470786a5021536e813'
HASHES={A:'788e75e3e56e1fdcfbe7709ed7fbebcc8b80675b2b63952410d070e568268a74',B:'7a9b8e12167ef2ab03356ec993fbb08b1c95083e98168fdccc2954b732098754'}
def render(path):
 return {(o['apiVersion'],o['kind'],o['metadata'].get('namespace'),o['metadata']['name']):o for o in yaml.safe_load_all(subprocess.check_output(['kubectl','kustomize',str(ROOT/'clusters'/path)],text=True)) if o}
class Overlay(unittest.TestCase):
 def test_preserves_entire_baseline(self):
  a,b=render('local-app-resource-dashboards'),render('local-identity-onboarding');changed=[k for k in a if a[k]!=b.get(k)]
  key=('source.toolkit.fluxcd.io/v1','GitRepository','flux-system','tenant-enrollments');self.assertEqual(changed,[key]);o=copy.deepcopy(b[key]);self.assertIn(o['spec']['ref']['commit'],HASHES);o['spec']['ref']=a[key]['spec']['ref'];self.assertEqual(o,a[key]);self.assertEqual({k[3] for k in set(b)-set(a)},{'identity-portal','identity-portal-foundation-root'})
 def test_exact_readiness_and_no_receipt_metadata_injection(self):
  b=render('local-identity-onboarding');source=b[('source.toolkit.fluxcd.io/v1','GitRepository','flux-system','tenant-enrollments')]['spec']['ref']['commit'];s=b[('kustomize.toolkit.fluxcd.io/v1','Kustomization','flux-system','identity-portal')]['spec']
  self.assertNotIn('commonMetadata',s);self.assertEqual(s['serviceAccountName'],'identity-declaration-reconciler');self.assertFalse(s['prune']);self.assertFalse(s['force']);self.assertFalse(s['wait']);self.assertIs(s['suspend'],False);self.assertEqual(len(s['healthChecks']),2 if source==A else 3)
  e=s['dependsOn'][0];self.assertEqual(e['name'],'identity-portal-foundation-controls');self.assertIn(HASHES[source],e['readyExpr']);self.assertIn('observedGeneration',e['readyExpr']);self.assertIn("e.status == 'True'",e['readyExpr'])
if __name__=='__main__':unittest.main()
