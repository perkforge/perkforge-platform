"""Current candidate deployment/installer boundary, independent of pilot identity config."""
import os
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
