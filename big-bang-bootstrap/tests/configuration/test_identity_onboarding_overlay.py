import copy,pathlib,subprocess,unittest,yaml
ROOT=pathlib.Path(__file__).resolve().parents[2]
A='cf30914f793358507c71348a3ca1bd25bd654198';B='73648e47d1fd4bb6ba901820df23db4df45a9dd6'
HASHES={A:'a8942ebe077f84fedb9d382a1e4e4f02aee40094cfb4f00a44f1cbefa1f6368c',B:'574badef224b80e42cc686dab37de7dbf448974c33f853f7f7d56fedf9f4afdb'}
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
