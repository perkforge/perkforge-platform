"""Current physical candidate is token-only; historical OIDC fixtures stay separate."""
import os
from pathlib import Path
import unittest
import yaml
from fixtures.render_helpers import build, helm, ordered_values, child_values, release_name
ROOT=Path(__file__).resolve().parents[2]
class HeadlampInitial(unittest.TestCase):
 def test_actual_root_disables_oidc_without_granting_runtime_privilege(self):
  root=build(ROOT/'clusters/local-headlamp');parent=next(x for x in root if x['kind']=='HelmRelease')
  config=next(x for x in root if x['metadata']['name']=='values-headlamp')
  self.assertNotIn('oidc.yaml',config['data'])
  self.assertFalse(any(x['name']=='values-headlamp' and x['valuesKey']=='oidc.yaml' for x in parent['spec']['valuesFrom']))
  src=Path(os.environ['PREFLIGHT_SOURCES_DIR'])
  outer=helm(src/'bigbang/chart','bigbang','bigbang',ordered_values(root,parent))
  child=next(x for x in outer if x['kind']=='HelmRelease' and x['metadata']['name']=='headlamp')
  self.assertFalse(child['spec']['suspend']);self.assertNotIn('dependsOn',child['spec'])
  self.assertEqual(child['spec']['serviceAccountName'],'headlamp-installer')
  objs=helm(src/'headlamp/chart',release_name(child),'headlamp',child_values(outer,'headlamp'))
  self.assertEqual(sorted(x['kind'] for x in objs),['Deployment','Service','ServiceAccount'])
  pod=next(x for x in objs if x['kind']=='Deployment')['spec']['template']['spec']
  self.assertEqual(pod['nodeSelector'],{'storage.perkforge.io/worker':'true'})
  text=yaml.safe_dump(pod).lower()
  self.assertNotIn('oidc',text);self.assertNotIn('unsafe',text)
  self.assertEqual(next(x for x in objs if x['kind']=='Service')['spec']['type'],'ClusterIP')
  foundation=build(ROOT/'configuration/packages/headlamp/prerequisites')
  self.assertFalse(any(x['kind'].startswith('Cluster') for x in foundation))
  rules=next(x for x in foundation if x['kind']=='Role')['rules']
  for group,resource in [('', 'services'),('', 'serviceaccounts'),('apps','deployments')]:
   for verb in ['get','list','watch','create','update','patch','delete']:
    self.assertTrue(any(group in r['apiGroups'] and resource in r['resources'] and verb in r['verbs'] for r in rules))
  self.assertTrue((ROOT/'configuration/packages/headlamp/oidc.yaml').is_file())

 def test_selected_chart_has_no_object_lookup_against_synthetic_api(self):
  import tempfile,subprocess
  from fixtures.lookup_server import lookup_server
  root=build(ROOT/'clusters/local-headlamp');parent=next(x for x in root if x['kind']=='HelmRelease')
  src=Path(os.environ['PREFLIGHT_SOURCES_DIR'])
  outer=helm(src/'bigbang/chart','bigbang','bigbang',ordered_values(root,parent))
  child=next(x for x in outer if x['kind']=='HelmRelease' and x['metadata']['name']=='headlamp')
  role={'metadata':{'namespace':'headlamp'},'rules':[]}
  with tempfile.TemporaryDirectory() as directory,lookup_server(role,secrets={}) as (url,requests):
   p=Path(directory);k=p/'kubeconfig';k.write_text(yaml.safe_dump({'apiVersion':'v1','kind':'Config','clusters':[{'name':'synthetic','cluster':{'server':url}}],'users':[{'name':'synthetic','user':{}}],'contexts':[{'name':'synthetic','context':{'cluster':'synthetic','user':'synthetic'}}],'current-context':'synthetic'}))
   v=p/'values.yaml';v.write_text(child_values(outer,'headlamp')[0])
   result=subprocess.run(['helm','template',release_name(child),str(src/'headlamp/chart'),'--namespace','headlamp','--kube-version','1.36.5','--kubeconfig',str(k),'--dry-run=server','-f',str(v)],capture_output=True,text=True,timeout=30)
   self.assertEqual(result.returncode,0,result.stderr)
   self.assertFalse(any('/namespaces/' in x or '/clusterroles' in x for x in requests),requests)
