from pathlib import Path
import unittest,yaml
from fixtures.collaboration import package_render
from fixtures.render_helpers import build
ROOT=Path(__file__).resolve().parents[2]
class MattermostReview(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.render=package_render(ROOT,'mattermost',('mattermost-operator',));cls.foundation=build(ROOT/'configuration/packages/mattermost/prerequisites')
 def test_disabled_real_cr_operator_and_no_admin_or_license_values(self):
  c=yaml.safe_load((ROOT/'configuration/packages/mattermost/candidate-values.yaml').read_text())['addons'];self.assertTrue(all(not x['enabled'] and x['flux']['suspend'] for x in c.values()));ds=self.render['mattermost'][1];cr=next(x for x in ds if x['kind']=='Mattermost');self.assertNotIn('licenseSecret',cr['spec']);self.assertFalse(cr['spec']['ingress']['enabled']);self.assertEqual(cr['spec']['database']['external']['secret'],'mattermost-database')
  for x in ds:
   if x['kind']=='Secret':self.assertEqual(set(x.get('stringData',{})),{'MM_SERVICESETTINGS_SITEURL','MM_GITLABSETTINGS_SCOPE'});self.assertFalse(x.get('data'))
  self.assertEqual(len(self.render['mattermost-operator'][1]),8);self.assertEqual(sum(x['kind']=='CustomResourceDefinition' for x in self.render['mattermost-operator'][1]),3)
 def test_every_rendered_object_role_ref_and_escalation_is_explicit(self):
  mapping={'Mattermost':('installation.mattermost.com','mattermosts'),'Secret':('','secrets'),'ConfigMap':('','configmaps'),'Service':('','services'),'ServiceAccount':('','serviceaccounts'),'Job':('batch','jobs'),'NetworkPolicy':('networking.k8s.io','networkpolicies'),'Role':('rbac.authorization.k8s.io','roles'),'RoleBinding':('rbac.authorization.k8s.io','rolebindings'),'Deployment':('apps','deployments'),'ClusterRole':('rbac.authorization.k8s.io','clusterroles'),'ClusterRoleBinding':('rbac.authorization.k8s.io','clusterrolebindings'),'CustomResourceDefinition':('apiextensions.k8s.io','customresourcedefinitions')}
  for package,(hr,ds) in self.render.items():
   identity=hr['spec']['serviceAccountName']
   def allowed(kind,group,res,name,verb):return any(group in r['apiGroups'] and res in r['resources'] and verb in r['verbs'] and ('resourceNames' not in r or name in r['resourceNames']) for x in self.foundation if x['kind']==kind and x['metadata']['name']==identity for r in x['rules'])
   for x in ds:
    group,res=mapping[x['kind']];scope='ClusterRole' if x['kind'] in ['CustomResourceDefinition','ClusterRole','ClusterRoleBinding'] else 'Role'
    for verb in ['get','list','watch','create','update','patch','delete']:self.assertTrue(allowed(scope,group,res,x['metadata']['name'],verb),(package,x['kind'],verb))
    if x['kind'] in ['Role','ClusterRole']:self.assertTrue(allowed(scope,group,res,x['metadata']['name'],'escalate'))
    if x['kind'].endswith('RoleBinding'):
     ref=x['roleRef'];self.assertTrue(allowed('ClusterRole' if ref['kind']=='ClusterRole' else 'Role',group,'clusterroles' if ref['kind']=='ClusterRole' else 'roles',ref['name'],'bind'))
   self.assertFalse(allowed('ClusterRole','rbac.authorization.k8s.io','clusterroles','cluster-admin','bind'))
 def test_operator_power_and_unrestricted_wait_egress_are_not_hidden(self):
  role=next(x for x in self.render['mattermost-operator'][1] if x['kind']=='ClusterRole');self.assertTrue(any('secrets' in r['resources'] and '*' in r['verbs'] for r in role['rules']))
  self.assertTrue(any(x['kind']=='NetworkPolicy' and 'anywhere-any-port' in x['metadata']['name'] for x in self.render['mattermost'][1]))

 def test_both_installers_match_their_helmrelease_namespace(self):
  for _,(hr,_) in self.render.items():
   name=hr['spec']['serviceAccountName'];namespace=hr['metadata']['namespace'];sa=next(x for x in self.foundation if x['kind']=='ServiceAccount' and x['metadata']['name']==name);self.assertEqual(sa['metadata']['namespace'],namespace);self.assertFalse(sa['automountServiceAccountToken'])
   role=next(x for x in self.foundation if x['kind']=='Role' and x['metadata']['name']==name)
   for group,res in [('', 'pods'),('apps','replicasets')]:self.assertTrue(any(group in r['apiGroups'] and res in r['resources'] and set(['get','list','watch']).issubset(r['verbs']) and not set(['create','patch','update','delete']).intersection(r['verbs']) for r in role['rules']))
   subjects=[q for x in self.foundation if x['kind'].endswith('RoleBinding') for q in x['subjects'] if q['name']==name];self.assertTrue(subjects);self.assertTrue(all(q['namespace']==namespace for q in subjects))
