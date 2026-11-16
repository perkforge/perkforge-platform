import copy,pathlib,subprocess,unittest,yaml
ROOT=pathlib.Path(__file__).resolve().parents[2]
A='ccfb231c3ad0e70af8682d535d320ca0449d2897';B='dd5b5c339a5aedcc8d5be0490da9f815cda113da'
HASHES={A:'402b9fe44daf08eb2a4d83eacffc474d559f5e0e079fbffb1b66289bb3b11d8f',B:'d257c2a0cc5b3f4878d19ef6e4c573ba18563410c0fb46306d13576be77966c9'}
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
