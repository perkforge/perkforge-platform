import copy,pathlib,subprocess,unittest,yaml
ROOT=pathlib.Path(__file__).resolve().parents[2]
A='8b04be30c091eb92a2bc029945182ff0179f3e4e'
def render(path):
 return {(o['apiVersion'],o['kind'],o['metadata'].get('namespace'),o['metadata']['name']):o for o in yaml.safe_load_all(subprocess.check_output(['kubectl','kustomize',str(ROOT/'clusters'/path)],text=True)) if o}
class FoundationOnly(unittest.TestCase):
 def test_exact_baseline_and_single_root(self):
  a,b=render('local-app-resource-dashboards'),render('local-identity-foundation')
  key=('source.toolkit.fluxcd.io/v1','GitRepository','flux-system','tenant-enrollments')
  self.assertEqual([k for k in a if a[k]!=b.get(k)],[key]);self.assertEqual(b[key]['spec']['ref'],{'commit':A})
  saved=copy.deepcopy(b[key]);saved['spec']['ref']=a[key]['spec']['ref'];self.assertEqual(saved,a[key])
  self.assertEqual(set(b)-set(a),{('kustomize.toolkit.fluxcd.io/v1','Kustomization','flux-system','identity-portal-foundation-root')})
 def test_no_phase_or_workload_selection(self):
  b=render('local-identity-foundation');s=b[('kustomize.toolkit.fluxcd.io/v1','Kustomization','flux-system','identity-portal-foundation-root')]['spec']
  self.assertEqual(s,{'interval':'5m','timeout':'5m','path':'./generated/identity-foundation/portal','sourceRef':{'kind':'GitRepository','name':'tenant-enrollments'},'serviceAccountName':'platform-reconciler','prune':False,'force':False,'wait':True})
  names={k[3] for k in b if k[1]=='Kustomization'}
  self.assertFalse(names.intersection({'identity-portal','identity-portal-foundation','identity-portal-attest','identity-portal-memberships'}))
  self.assertFalse(any(k[1] in ('Job','Pod','CronJob') for k in b))
if __name__=='__main__':unittest.main()
