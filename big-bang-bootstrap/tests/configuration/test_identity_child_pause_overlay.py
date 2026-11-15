import copy,pathlib,subprocess,unittest,yaml
ROOT=pathlib.Path(__file__).resolve().parents[2]
PIN='8c87378462386399ee02e08127ae138aac0353d7'
HASH='655ec3623b60d13f23f0e917ef1facdca45206d24916f7635e1b4a6ce3dea5db'
def render(path):
 return {(o['apiVersion'],o['kind'],o['metadata'].get('namespace'),o['metadata']['name']):o for o in yaml.safe_load_all(subprocess.check_output(['kubectl','kustomize',str(ROOT/'clusters'/path)],text=True)) if o}
class Pause(unittest.TestCase):
 def test_baseline_and_no_workload(self):
  a,b=render('local-app-resource-dashboards'),render('local-identity-child-pause');key=('source.toolkit.fluxcd.io/v1','GitRepository','flux-system','tenant-enrollments')
  self.assertEqual([k for k in a if a[k]!=b.get(k)],[key]);self.assertEqual(b[key]['spec']['ref'],{'commit':PIN});o=copy.deepcopy(b[key]);o['spec']['ref']=a[key]['spec']['ref'];self.assertEqual(o,a[key]);self.assertEqual({k[3] for k in set(b)-set(a)},{'identity-portal','identity-portal-foundation-root'});self.assertFalse(any(k[1] in ('Pod','Job','CronJob') for k in b))
 def test_parent_can_apply_old_child_hold(self):
  b=render('local-identity-child-pause');s=b[('kustomize.toolkit.fluxcd.io/v1','Kustomization','flux-system','identity-portal')]['spec']
  self.assertIs(s['suspend'],False);self.assertFalse(s['prune']);self.assertFalse(s['force']);self.assertFalse(s['wait']);self.assertEqual(s['serviceAccountName'],'identity-declaration-reconciler');self.assertEqual([x['name'] for x in s['healthChecks']],['identity-portal-foundation','identity-portal-attest']);self.assertEqual(s['sourceRef'],{'kind':'GitRepository','name':'tenant-enrollments'});self.assertEqual(s['path'],'./clusters/local-identity-portal');self.assertIn(HASH,s['dependsOn'][0]['readyExpr']);self.assertIn('observedGeneration',s['dependsOn'][0]['readyExpr']);self.assertNotIn('commonMetadata',s)
if __name__=='__main__':unittest.main()
