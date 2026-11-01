"""Current candidate deployment/installer boundary, independent of pilot identity config."""
import os
import json
import copy
from pathlib import Path
import unittest
import yaml
from fixtures.render_helpers import build,helm,ordered_values,child_values,release_name
ROOT=Path(__file__).resolve().parents[2]
class KeycloakInitial(unittest.TestCase):
 def test_actual_selected_chart_uses_external_credentials_and_no_realm_import(self):
  root=build(ROOT/'clusters/local');parent=next(x for x in root if x['kind']=='HelmRelease');src=Path(os.environ['PREFLIGHT_SOURCES_DIR'])
  outer=helm(src/'bigbang/chart','bigbang','bigbang',ordered_values(root,parent))
  hr=next(x for x in outer if x['kind']=='HelmRelease' and x['metadata']['name']=='keycloak')
  self.assertFalse(hr['spec']['suspend']);self.assertEqual(hr['spec']['dependsOn'],[{'name':'longhorn','namespace':'bigbang'}])
  self.assertEqual(hr['spec']['serviceAccountName'],'keycloak-installer')
  objects=helm(src/'keycloak/chart',release_name(hr),'keycloak',child_values(outer,'keycloak'))
  self.assertFalse(any(x['kind'] in ['Secret','Role','RoleBinding','ClusterRole','ClusterRoleBinding','Ingress'] for x in objects))
  foundation=build(ROOT/'configuration/packages/keycloak/prerequisites-longhorn')
  self.assertFalse(any(x['kind'] in ['StorageClass','PersistentVolume','ClusterRole','ClusterRoleBinding'] for x in foundation))
  pvc=next(x for x in foundation if x['kind']=='PersistentVolumeClaim')
  self.assertEqual(pvc['spec']['storageClassName'],'longhorn');self.assertNotIn('volumeName',pvc['spec'])
  rules=next(x for x in foundation if x['kind']=='Role')['rules']
  resource={'StatefulSet':('apps','statefulsets'),'Service':('','services'),'ServiceAccount':('','serviceaccounts'),'PodDisruptionBudget':('policy','poddisruptionbudgets')}
  for obj in objects:
   group,plural=resource[obj['kind']]
   for verb in ['get','list','watch','create','update','patch','delete']:
    self.assertTrue(any(group in r['apiGroups'] and plural in r['resources'] and verb in r['verbs'] for r in rules),(obj['kind'],verb))
   if obj['kind']=='StatefulSet':
    pod=obj['spec']['template']['spec'];self.assertEqual(pod['nodeSelector'],{'storage.perkforge.io/worker':'true'})
    self.assertEqual(obj['spec']['replicas'],1)
    self.assertNotIn('--import-realm',yaml.safe_dump(pod));self.assertNotIn('realm.yaml',yaml.safe_dump(pod))
  app=next(x for x in objects if x['kind']=='StatefulSet' and x['metadata']['name']=='keycloak-keycloak')
  pod=app['spec']['template']['spec'];sa=next(x for x in objects if x['kind']=='ServiceAccount' and x['metadata']['name']==pod['serviceAccountName']);self.assertFalse(sa['automountServiceAccountToken'])
  self.assertEqual(pod['containers'][0]['envFrom'],[{'secretRef':{'name':'keycloak-bootstrap-existing'}}])
  play=yaml.safe_load((ROOT/'configuration/ansible/keycloak-prerequisites.yaml').read_text())[0]
  self.assertFalse(play['vars']['keycloak_routing_apply']);self.assertFalse(play['vars']['identity_access_apply'])
  self.assertFalse(play['vars']['identity_routing_apply']);self.assertFalse(play['vars']['identity_foundation_apply'])

 def test_fixed_image_override_is_immutable_and_changes_only_image_and_version_labels(self):
  evidence=json.loads((ROOT/'tests/fixtures/keycloak-image-evidence.json').read_text())
  self.assertEqual(evidence['tag'],'26.8.1')
  self.assertRegex(evidence['indexDigest'],r'^sha256:[0-9a-f]{64}$')
  self.assertEqual(evidence['chart']['version'],'7.3.2-bb.1')
  self.assertEqual(evidence['chart']['appVersionMetadata'],'26.8.0')
  self.assertEqual({x['platform']['architecture'] for x in evidence['platforms']},{'amd64','arm64'})
  # The staged root becomes canonical when the separately reviewed stage MR lands.
  selected=ROOT/'clusters/local-keycloak'
  if not selected.is_dir():selected=ROOT/'clusters/local'
  root=build(selected);baseline=copy.deepcopy(root);src=Path(os.environ['PREFLIGHT_SOURCES_DIR'])
  config=next(x for x in root if x['metadata']['name']=='values-keycloak')
  values=yaml.safe_load(config['data']['values.yaml'])
  image=values['addons']['keycloak']['values']['upstream']['image']
  self.assertEqual(image,{'tag':'26.8.1','digest':evidence['indexDigest']})
  previous=next(x for x in baseline if x['metadata']['name']=='values-keycloak')
  old=yaml.safe_load(previous['data']['values.yaml'])
  old['addons']['keycloak']['values']['upstream']['image']={'tag':'26.8.0','digest':''}
  previous['data']['values.yaml']=yaml.safe_dump(old)
  def render(objects):
   parent=next(x for x in objects if x['kind']=='HelmRelease')
   outer=helm(src/'bigbang/chart','bigbang','bigbang',ordered_values(objects,parent))
   hr=next(x for x in outer if x['kind']=='HelmRelease' and x['metadata']['name']=='keycloak')
   self.assertEqual(hr['spec']['chart']['spec']['sourceRef']['name'],'keycloak')
   source=next(x for x in outer if x['kind']=='GitRepository' and x['metadata']['name']=='keycloak')
   self.assertEqual(source['spec']['ref']['tag'],'7.3.2-bb.1')
   return helm(src/'keycloak/chart',release_name(hr),'keycloak',child_values(outer,'keycloak'))
  before=render(baseline);after=render(root);changes=[]
  def diff(a,b,path=''):
   self.assertIs(type(a),type(b),path)
   if isinstance(a,dict):
    self.assertEqual(a.keys(),b.keys(),path)
    for key in a:diff(a[key],b[key],path+'/'+str(key))
   elif isinstance(a,list):
    self.assertEqual(len(a),len(b),path)
    for i,(x,y) in enumerate(zip(a,b)):diff(x,y,path+'/'+str(i))
   elif a!=b:changes.append((path,a,b))
  diff(before,after)
  self.assertEqual(sum(path.endswith('/image') for path,_,_ in changes),1)
  for path,old,new in changes:
   if path.endswith('/image'):
    self.assertEqual(old,evidence['repository']+':26.8.0')
    self.assertEqual(new,evidence['repository']+'@'+evidence['indexDigest'])
   else:
    self.assertTrue(path.endswith('/app.kubernetes.io/version'),path)
    self.assertEqual(old,'26.8.0');self.assertEqual(new,'26.8.1')
