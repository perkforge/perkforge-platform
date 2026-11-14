"""Current-root preservation, no live API or deployment authority."""
from pathlib import Path
import unittest
import yaml
from fixtures.render_helpers import build
ROOT = Path(__file__).resolve().parents[2]
class IntegratedLogging(unittest.TestCase):
 def test_only_additive_backend_activation_preserves_current_root(self):
  def indexed(path):
   return {(x['kind'],x.get('metadata',{}).get('namespace'),x['metadata']['name']):x for x in build(ROOT/'clusters'/path)}
  old=indexed('local-mattermost-pilot');new=indexed('local-integrated-logging')
  self.assertEqual(set(new)-set(old),{('ConfigMap','bigbang','values-integrated-logging')})
  k=('HelmRelease','bigbang','bigbang');a=old.pop(k);b=new.pop(k)
  for key,value in old.items():self.assertEqual(value,new[key],key)
  self.assertEqual(b['spec']['valuesFrom'][:-1],a['spec']['valuesFrom'])
  self.assertEqual(b['spec']['valuesFrom'][-1]['name'],'values-integrated-logging')
  self.assertEqual(b['spec']['postRenderers'][0]['kustomize']['patches'][:-2],a['spec']['postRenderers'][0]['kustomize']['patches'])
  b['spec']['valuesFrom']=a['spec']['valuesFrom'];b['spec']['postRenderers']=a['spec']['postRenderers'];self.assertEqual(a,b)
  v=yaml.safe_load(new[('ConfigMap','bigbang','values-integrated-logging')]['data']['values.yaml'])
  self.assertEqual(v['alloy']['flux'],{'suspend':False});self.assertFalse(v['alloy']['values']['monitoring']['enabled']);self.assertEqual(v['alloy']['values']['serviceMonitors'],[])
  self.assertEqual(v['loki']['values']['singleBinary']['nodeSelector'],{'storage.perkforge.io/worker':'true'});self.assertEqual(v['loki']['values']['gateway']['basicAuth']['existingSecret'],'loki-gateway-auth-v2')
  for key in ['dashboards','serviceMonitor','rules']:self.assertFalse(v['loki']['values']['monitoring'][key]['enabled'])
  self.assertNotIn('grafana',v)
 def test_actual_umbrella_monitoring_does_not_expand_logging_installer_scope(self):
  import os
  from fixtures.render_helpers import helm,ordered_values,child_values,release_name
  sources=os.environ.get('PREFLIGHT_SOURCES_DIR')
  if not sources:self.skipTest('Exact pinned source fixtures required')
  src=Path(sources);objects=build(ROOT/'clusters/local');parent=next(x for x in objects if x['kind']=='HelmRelease')
  values=ordered_values(objects,parent)+[(ROOT/'configuration/observability/candidate-values.yaml').read_text(),(ROOT/'configuration/observability/integrated-logging/values.yaml').read_text()]
  outer=helm(src/'bigbang/chart','bigbang','bigbang',values,('--set','monitoring.enabled=true','--set','grafana.enabled=true'))
  for name in ['loki','alloy']:
   hr=next(x for x in outer if x['kind']=='HelmRelease' and x['metadata']['name']==name)
   rendered=helm(src/name/'chart',release_name(hr),hr['spec']['targetNamespace'],child_values(outer,name),('--include-crds',))
   self.assertFalse(any(x['kind'] in ['PrometheusRule','ServiceMonitor','ClusterRole','ClusterRoleBinding'] for x in rendered),name)
   if name=='loki':
    pod=next(x for x in rendered if x['kind']=='StatefulSet')['spec']['template']['spec']
    self.assertEqual(pod['nodeSelector']['storage.perkforge.io/worker'],'true')
    gateway=next(x for x in rendered if x['kind']=='Deployment')['spec']['template']['spec']
    self.assertIn('loki-gateway-auth-v2',[v.get('secret',{}).get('secretName') for v in gateway['volumes']])
