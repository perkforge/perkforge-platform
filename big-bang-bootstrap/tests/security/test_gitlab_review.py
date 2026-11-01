from pathlib import Path
import unittest,yaml
from fixtures.collaboration import package_render
from fixtures.render_helpers import build
ROOT=Path(__file__).resolve().parents[2]
class GitLabReview(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.hr,cls.objects=package_render(ROOT,'gitlab')['gitlab'];cls.foundation=build(ROOT/'configuration/packages/gitlab/prerequisites')
 def test_disabled_external_dependencies_not_hidden_installation(self):
  c=yaml.safe_load((ROOT/'configuration/packages/gitlab/candidate-values.yaml').read_text())['addons']['gitlab'];self.assertFalse(c['enabled']);self.assertTrue(self.hr['spec']['suspend']);v=c['values'];self.assertFalse(v['global']['appConfig']['omniauth']['enabled']);self.assertNotIn('license',v['global'].get('gitlab',{}));self.assertIn('UNCONFIGURED',v['global']['psql']['host']);self.assertIn('UNCONFIGURED',v['global']['redis']['host'])
  self.assertFalse(any(x['kind'] in ['Ingress','Gateway','HTTPRoute','ClusterRole','ClusterRoleBinding','CustomResourceDefinition'] for x in self.objects));self.assertEqual(len(self.objects),75)
  self.assertFalse(any('registry' in x['metadata']['name'] and x['kind']=='Deployment' for x in self.objects))
 def test_full_render_crud_binding_and_escalation_contract(self):
  kinds={'ServiceAccount':('','serviceaccounts'),'Service':('','services'),'ConfigMap':('','configmaps'),'Secret':('','secrets'),'Deployment':('apps','deployments'),'StatefulSet':('apps','statefulsets'),'Job':('batch','jobs'),'Role':('rbac.authorization.k8s.io','roles'),'RoleBinding':('rbac.authorization.k8s.io','rolebindings'),'HorizontalPodAutoscaler':('autoscaling','horizontalpodautoscalers'),'PodDisruptionBudget':('policy','poddisruptionbudgets')}
  rules=next(x for x in self.foundation if x['kind']=='Role')['rules']
  def allowed(group,res,name,verb):return any(group in r['apiGroups'] and res in r['resources'] and verb in r['verbs'] and ('resourceNames' not in r or name in r['resourceNames']) for r in rules)
  for x in self.objects:
   group,res=kinds[x['kind']]
   for verb in ['get','list','watch','create','update','patch','delete']:self.assertTrue(allowed(group,res,x['metadata']['name'],verb),(x['kind'],verb))
   if x['kind']=='Role':self.assertTrue(allowed(group,res,x['metadata']['name'],'escalate'))
   if x['kind']=='RoleBinding':self.assertTrue(allowed(group,'roles',x['roleRef']['name'],'bind'))
  self.assertFalse(allowed('rbac.authorization.k8s.io','clusterroles','cluster-admin','bind'))
 def test_no_password_objects_or_vendor_ca_trust_mounts(self):
  secrets=[x for x in self.objects if x['kind']=='Secret'];self.assertEqual(len(secrets),31);self.assertTrue(all(x['metadata']['name'].startswith('ca-certs-') for x in secrets))
  for x in self.objects:
   if x['kind'] in ['Deployment','StatefulSet','Job']:
    self.assertFalse(any(v.get('secret',{}).get('secretName','').startswith('ca-certs-') for v in x['spec']['template']['spec'].get('volumes',[])))

 def test_real_initial_and_upgrade_lookup_path(self):
  import os,subprocess,tempfile
  from fixtures.lookup_server import lookup_server
  from fixtures.render_helpers import ordered_values,helm,child_values,release_name
  src=Path(os.environ['PREFLIGHT_SOURCES_DIR']);root=build(ROOT/'clusters/local');parent=next(x for x in root if x['kind']=='HelmRelease');outer=helm(src/'bigbang/chart','bigbang','bigbang',ordered_values(root,parent)+[(ROOT/'configuration/packages/gitlab/candidate-values.yaml').read_text()],('--set','addons.gitlab.enabled=true'))
  role=next(x for x in self.foundation if x['kind']=='Role')
  for upgrade in [False,True]:
   with tempfile.TemporaryDirectory() as d,lookup_server(role,secrets={}) as (url,requests):
    p=Path(d);k=p/'kubeconfig';k.write_text(yaml.safe_dump({'apiVersion':'v1','kind':'Config','clusters':[{'name':'synthetic','cluster':{'server':url}}],'users':[{'name':'synthetic','user':{}}],'contexts':[{'name':'synthetic','context':{'cluster':'synthetic','user':'synthetic'}}],'current-context':'synthetic'}));args=[]
    for i,v in enumerate(child_values(outer,'gitlab')):
     f=p/f'{i}.yaml';f.write_text(v);args+=['-f',str(f)]
    r=subprocess.run(['helm','template',release_name(self.hr),str(src/'gitlab/chart'),'--namespace','gitlab','--kube-version','1.36.5','--kubeconfig',str(k),'--dry-run=server']+(['--is-upgrade'] if upgrade else [])+args,capture_output=True,text=True,timeout=40);self.assertEqual(r.returncode,0,r.stderr);self.assertFalse(any('/clusterroles' in x for x in requests),requests)

 def test_installer_identity_namespace_matches_flux_helmrelease(self):
  name=self.hr['spec']['serviceAccountName'];namespace=self.hr['metadata']['namespace'];sa=next(x for x in self.foundation if x['kind']=='ServiceAccount' and x['metadata']['name']==name);self.assertEqual(sa['metadata']['namespace'],namespace);self.assertFalse(sa['automountServiceAccountToken'])
  role=next(x for x in self.foundation if x['kind']=='Role' and x['metadata']['name']==name)
  for group,res in [('', 'pods'),('apps','replicasets')]:self.assertTrue(any(group in r['apiGroups'] and res in r['resources'] and set(['get','list','watch']).issubset(r['verbs']) and not set(['create','patch','update','delete']).intersection(r['verbs']) for r in role['rules']))
  subjects=[q for x in self.foundation if x['kind'].endswith('RoleBinding') for q in x['subjects'] if q['name']==name];self.assertTrue(subjects);self.assertTrue(all(q['namespace']==namespace for q in subjects))
