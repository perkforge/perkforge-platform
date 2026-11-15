import copy,pathlib,subprocess,unittest,yaml
ROOT=pathlib.Path(__file__).resolve().parents[2]
A='dd675360a87bbd1df545e75f522666e9c6b22e6b';B='aba4d7caaeca1b81eeab0d74ed9d9a1bbcc7b711'
HASHES={A:'57dcd74a31370e56fb626a23dd6c610c8baf2927837852222bd64b1fdacf54bb',B:'aa1dbc2afc7248d7bac296c489f5ee21abf14bcdcdab121181580d32a6317adc'}
def render(path):
 return {(o['apiVersion'],o['kind'],o['metadata'].get('namespace'),o['metadata']['name']):o for o in yaml.safe_load_all(subprocess.check_output(['kubectl','kustomize',str(ROOT/'clusters'/path)],text=True)) if o}
class Overlay(unittest.TestCase):
 def test_preserves_entire_baseline(self):
  a,b=render('local-app-resource-dashboards'),render('local-identity-onboarding');changed=[k for k in a if a[k]!=b.get(k)]
  key=('source.toolkit.fluxcd.io/v1','GitRepository','flux-system','tenant-enrollments');self.assertEqual(changed,[key]);o=copy.deepcopy(b[key]);self.assertIn(o['spec']['ref']['commit'],HASHES);o['spec']['ref']=a[key]['spec']['ref'];self.assertEqual(o,a[key]);self.assertEqual({k[3] for k in set(b)-set(a)},{'identity-portal','identity-portal-foundation-root'})
 def test_exact_readiness_and_no_receipt_metadata_injection(self):
  b=render('local-identity-onboarding');source=b[('source.toolkit.fluxcd.io/v1','GitRepository','flux-system','tenant-enrollments')]['spec']['ref']['commit'];s=b[('kustomize.toolkit.fluxcd.io/v1','Kustomization','flux-system','identity-portal')]['spec']
  self.assertNotIn('commonMetadata',s);self.assertEqual(s['serviceAccountName'],'identity-declaration-reconciler');self.assertFalse(s['prune']);self.assertFalse(s['force']);self.assertFalse(s['wait']);self.assertEqual(len(s['healthChecks']),2 if source==A else 3)
  e=s['dependsOn'][0];self.assertEqual(e['name'],'identity-portal-foundation-controls');self.assertIn(HASHES[source],e['readyExpr']);self.assertIn('observedGeneration',e['readyExpr']);self.assertIn("e.status == 'True'",e['readyExpr'])
if __name__=='__main__':unittest.main()
