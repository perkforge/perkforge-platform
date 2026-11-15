import copy,pathlib,subprocess,unittest,yaml
ROOT=pathlib.Path(__file__).resolve().parents[2]
A='dd675360a87bbd1df545e75f522666e9c6b22e6b'
HASH='57dcd74a31370e56fb626a23dd6c610c8baf2927837852222bd64b1fdacf54bb'
def render(path):
 return {(o['apiVersion'],o['kind'],o['metadata'].get('namespace'),o['metadata']['name']):o for o in yaml.safe_load_all(subprocess.check_output(['kubectl','kustomize',str(ROOT/'clusters'/path)],text=True)) if o}
class Hold(unittest.TestCase):
 def test_entire_baseline_and_only_two_roots(self):
  a,b=render('local-app-resource-dashboards'),render('local-identity-hold')
  self.assertEqual(len(a),106);self.assertEqual(len(b),108)
  key=('source.toolkit.fluxcd.io/v1','GitRepository','flux-system','tenant-enrollments')
  self.assertEqual([k for k in a if a[k]!=b.get(k)],[key]);self.assertEqual(b[key]['spec']['ref'],{'commit':A})
  saved=copy.deepcopy(b[key]);saved['spec']['ref']=a[key]['spec']['ref'];self.assertEqual(saved,a[key])
  self.assertEqual(set(b)-set(a),{('kustomize.toolkit.fluxcd.io/v1','Kustomization','flux-system',n) for n in ('identity-portal-foundation-root','identity-portal')})
  self.assertFalse(any(k[1] in ('Pod','Job','CronJob') for k in b))
 def test_exact_suspended_phase_and_active_foundation(self):
  b=render('local-identity-hold');key=('kustomize.toolkit.fluxcd.io/v1','Kustomization','flux-system','identity-portal')
  s=b[key]['spec'];expected={'interval':'5m','timeout':'6m','path':'./clusters/local-identity-portal','sourceRef':{'kind':'GitRepository','name':'tenant-enrollments'},'serviceAccountName':'identity-declaration-reconciler','prune':False,'force':False,'wait':False,'suspend':True,'healthChecks':[{'apiVersion':'kustomize.toolkit.fluxcd.io/v1','kind':'Kustomization','name':n,'namespace':'flux-system'} for n in ('identity-portal-foundation','identity-portal-attest')],'dependsOn':[{'name':'identity-portal-foundation-controls','readyExpr':"dep.spec.commonMetadata.annotations['platform.perkforge.io/foundation-sha256'] == '"+HASH+"' && dep.metadata.generation == dep.status.observedGeneration && dep.status.conditions.exists(e, e.type == 'Ready' && e.status == 'True')"}]}
  self.assertEqual(s,expected)
  foundation_key=key[:-1]+('identity-portal-foundation-root',)
  self.assertEqual(b[foundation_key],render('local-identity-foundation')[foundation_key])
  self.assertNotIn('suspend',b[foundation_key]['spec'])
if __name__=='__main__':unittest.main()
