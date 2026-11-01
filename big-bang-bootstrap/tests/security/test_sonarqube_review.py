from pathlib import Path
import unittest,yaml,tarfile,os
from fixtures.collaboration import package_render
from fixtures.render_helpers import build
ROOT=Path(__file__).resolve().parents[2]
class SonarQubeReview(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.hr,cls.objects=package_render(ROOT,'sonarqube')['sonarqube'];cls.foundation=build(ROOT/'configuration/packages/sonarqube/prerequisites')
 def test_inactive_community_and_only_protected_password_refs(self):
  c=yaml.safe_load((ROOT/'configuration/packages/sonarqube/candidate-values.yaml').read_text())['addons']['sonarqube'];self.assertFalse(c['enabled']);self.assertTrue(self.hr['spec']['suspend']);u=c['values']['upstream'];self.assertTrue(u['community']['enabled']);self.assertNotIn('edition',u);self.assertEqual(u['setAdminPassword']['passwordSecretName'],'sonarqube-initial-admin');self.assertIsNone(u['monitoringPasscode']);self.assertIsNone(u['jdbcOverwrite']['jdbcPassword'])
  self.assertEqual(len(self.objects),9)
  for x in self.objects:
   if x['kind']=='Secret':self.assertFalse(any((x.get('data') or {}).values()));self.assertFalse(any((x.get('stringData') or {}).values()))
  self.assertFalse(any(x['kind'] in ['Ingress','Gateway','HTTPRoute','CustomResourceDefinition','Role','ClusterRole','RoleBinding','ClusterRoleBinding'] for x in self.objects))
 def test_no_privileged_host_mutation_and_explicit_namespaced_crud(self):
  mapping={'Secret':('','secrets'),'ConfigMap':('','configmaps'),'Service':('','services'),'ServiceAccount':('','serviceaccounts'),'PersistentVolumeClaim':('','persistentvolumeclaims'),'StatefulSet':('apps','statefulsets'),'Job':('batch','jobs')};rules=next(x for x in self.foundation if x['kind']=='Role')['rules']
  for x in self.objects:
   group,res=mapping[x['kind']]
   for verb in ['get','list','watch','create','update','patch','delete']:self.assertTrue(any(group in r['apiGroups'] and res in r['resources'] and verb in r['verbs'] for r in rules))
   if x['kind'] in ['Job','StatefulSet']:
    for c in x['spec']['template']['spec'].get('initContainers',[])+x['spec']['template']['spec']['containers']:
     self.assertFalse(c.get('securityContext',{}).get('privileged',False));self.assertNotIn(c['name'],['init-sysctl','init-fs'])
  self.assertFalse(any(x['kind'] in ['ClusterRole','ClusterRoleBinding'] for x in self.foundation))
 def test_selected_source_has_no_kubernetes_lookup_branch(self):
  source=Path(os.environ['PREFLIGHT_SOURCES_DIR'])/'sonarqube/chart';hits=[]
  for p in (source/'templates').rglob('*'):
   if p.is_file() and 'lookup ' in p.read_text():hits.append(str(p.relative_to(source)))
  with tarfile.open(source/'charts/sonarqube-2026.4.1.tgz') as t:
   for m in t.getmembers():
    if m.isfile() and '/templates/' in m.name and m.name.endswith(('.yaml','.tpl')) and 'lookup ' in t.extractfile(m).read().decode():hits.append(m.name)
  self.assertEqual(hits,[])

 def test_installer_identity_matches_helmrelease_namespace(self):
  name=self.hr['spec']['serviceAccountName'];namespace=self.hr['metadata']['namespace'];sa=next(x for x in self.foundation if x['kind']=='ServiceAccount' and x['metadata']['name']==name);self.assertEqual(sa['metadata']['namespace'],namespace);self.assertFalse(sa['automountServiceAccountToken'])
  subjects=[q for x in self.foundation if x['kind'].endswith('RoleBinding') for q in x['subjects'] if q['name']==name];self.assertTrue(subjects);self.assertTrue(all(q['namespace']==namespace for q in subjects))
