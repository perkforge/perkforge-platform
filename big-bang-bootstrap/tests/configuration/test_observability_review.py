"""Inactive native Big Bang contract; no new child-source fetch or API access."""
import os,unittest,yaml
from pathlib import Path
from fixtures.render_helpers import build,helm,ordered_values
ROOT=Path(__file__).resolve().parents[2]
class ObservabilityReview(unittest.TestCase):
 def test_inactive_pins_and_paused_outer_selection(self):
  p=ROOT/'configuration/observability';v=yaml.safe_load((p/'candidate-values.yaml').read_text());pins=yaml.safe_load((p/'sources.yaml').read_text());src=Path(os.environ['PREFLIGHT_SOURCES_DIR'])
  base=yaml.safe_load((src/'bigbang/chart/values.yaml').read_text());mapping={'prometheusOperatorCRDs':'prometheus-operator-crds','monitoring':'monitoring','grafana':'grafana','alloy':'alloy','loki':'loki'}
  for key,name in mapping.items():
   self.assertFalse(v[key]['enabled']);self.assertTrue(v[key]['flux']['suspend']);self.assertEqual(v[key]['git']['tag'],base[key]['git']['tag']);self.assertEqual(v[key]['git']['tag'],pins[name]['tag']);self.assertEqual(len(pins[name]['sha256']),64)
  root=build(ROOT/'clusters/local');parent=next(o for o in root if o['kind']=='HelmRelease');values=ordered_values(root,parent)
  current=helm(src/'bigbang/chart','bigbang','bigbang',values)
  self.assertFalse(set(mapping)&{o['metadata']['name'] for o in current if o['kind']=='HelmRelease'})
  out=helm(src/'bigbang/chart','bigbang','bigbang',values+[(p/'candidate-values.yaml').read_text()],tuple(y for key in mapping for y in ['--set',key+'.enabled=true']))
  names={o['metadata']['name']:o for o in out if o['kind']=='HelmRelease'}
  for name in mapping.values():self.assertTrue(names[name]['spec']['suspend'])
  self.assertFalse(v['monitoring']['values']['upstream']['grafana']['enabled']);self.assertTrue(v['monitoring']['values']['upstream']['alertmanager']['enabled'])
  prom=v['monitoring']['values']['upstream']['prometheus']['prometheusSpec'];self.assertEqual(prom['retention'],'7d');self.assertEqual(prom['retentionSize'],'8GB')
  graf=v['grafana']['values']['upstream'];self.assertFalse(graf['ingress']['enabled']);self.assertFalse(graf['grafana.ini']['auth.anonymous']['enabled']);self.assertFalse(graf['grafana.ini']['auth.generic_oauth']['enabled']);self.assertEqual(graf['admin']['existingSecret'],'grafana-admin')
