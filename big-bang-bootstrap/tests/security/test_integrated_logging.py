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
  self.assertEqual(v,{'alloy':{'enabled':True,'flux':{'suspend':False}},'loki':{'enabled':True,'flux':{'suspend':False}}})
  self.assertNotIn('grafana',v)
