from pathlib import Path
import unittest,yaml,os,subprocess,tempfile
from fixtures.collaboration import package_render
from fixtures.render_helpers import build,ordered_values,helm,child_values,release_name
ROOT=Path(__file__).resolve().parents[2]
class HarborReview(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.hr,cls.objects=package_render(ROOT,'harbor')['harbor'];cls.foundation=build(ROOT/'configuration/packages/harbor/prerequisites')
 def test_inactive_secret_refs_and_no_sample_credentials(self):
  c=yaml.safe_load((ROOT/'configuration/packages/harbor/candidate-values.yaml').read_text())['addons']['harbor'];self.assertFalse(c['enabled']);self.assertTrue(self.hr['spec']['suspend']);self.assertFalse(c['values']['upstream']['trivy']['enabled'])
  self.assertEqual(len(self.objects),23);self.assertFalse(any(x['kind'] in ['Ingress','Gateway','HTTPRoute','Role','ClusterRole','RoleBinding','ClusterRoleBinding','CustomResourceDefinition'] for x in self.objects))
  for x in self.objects:
   if x['kind']=='Secret':self.assertFalse(x.get('data'));self.assertFalse(x.get('stringData'))
  self.assertNotIn('harborPW',yaml.safe_dump(self.objects));self.assertNotIn('changeit',yaml.safe_dump(self.objects))
 def test_all_rendered_crud_with_no_cluster_or_bind_authority(self):
  rules=next(x for x in self.foundation if x['kind']=='Role')['rules'];mapping={'Secret':('','secrets'),'ConfigMap':('','configmaps'),'Service':('','services'),'PersistentVolumeClaim':('','persistentvolumeclaims'),'Deployment':('apps','deployments')}
  for x in self.objects:
   group,res=mapping[x['kind']]
   for verb in ['get','list','watch','create','update','patch','delete']:self.assertTrue(any(group in r['apiGroups'] and res in r['resources'] and verb in r['verbs'] for r in rules))
  self.assertFalse(any(x['kind'] in ['ClusterRole','ClusterRoleBinding'] for x in self.foundation));self.assertFalse(any('bind' in x['verbs'] or 'escalate' in x['verbs'] for x in rules))
 def test_real_initial_and_upgrade_lookups_without_secret_output(self):
  from fixtures.lookup_server import lookup_server
  src=Path(os.environ['PREFLIGHT_SOURCES_DIR']);root=build(ROOT/'clusters/local');parent=next(x for x in root if x['kind']=='HelmRelease');outer=helm(src/'bigbang/chart','bigbang','bigbang',ordered_values(root,parent)+[(ROOT/'configuration/packages/harbor/candidate-values.yaml').read_text()],('--set','addons.harbor.enabled=true'));role=next(x for x in self.foundation if x['kind']=='Role')
  for upgrade in [False,True]:
   with tempfile.TemporaryDirectory() as d,lookup_server(role,secrets={}) as (url,requests):
    p=Path(d);k=p/'kubeconfig';k.write_text(yaml.safe_dump({'apiVersion':'v1','kind':'Config','clusters':[{'name':'synthetic','cluster':{'server':url}}],'users':[{'name':'synthetic','user':{}}],'contexts':[{'name':'synthetic','context':{'cluster':'synthetic','user':'synthetic'}}],'current-context':'synthetic'}));args=[]
    for i,v in enumerate(child_values(outer,'harbor')):
     f=p/f'{i}.yaml';f.write_text(v);args+=['-f',str(f)]
    r=subprocess.run(['helm','template',release_name(self.hr),str(src/'harbor/chart'),'--namespace','harbor','--kube-version','1.36.5','--kubeconfig',str(k),'--dry-run=server']+(['--is-upgrade'] if upgrade else [])+args,capture_output=True,text=True,timeout=40);self.assertEqual(r.returncode,0,r.stderr);self.assertFalse(any('/clusterroles' in x for x in requests),requests)
