"""Real pinned offline metrics render; no deployment configuration generation."""
from pathlib import Path
import os
from fixtures.render_helpers import build,helm,ordered_values,child_values,release_name

def metrics_render(root):
 src=Path(os.environ['PREFLIGHT_SOURCES_DIR']);objects=build(root/'clusters/local');parent=next(x for x in objects if x['kind']=='HelmRelease')
 values=ordered_values(objects,parent)+[(root/'configuration/observability/candidate-values.yaml').read_text()]
 outer=helm(src/'bigbang/chart','bigbang','bigbang',values,tuple(y for x in ['monitoring','grafana','prometheusOperatorCRDs'] for y in ['--set',x+'.enabled=true']))
 result={}
 for name in ['monitoring','grafana','prometheus-operator-crds']:
  hr=next(x for x in outer if x['kind']=='HelmRelease' and x['metadata']['name']==name)
  result[name]=(hr,helm(src/name/'chart',release_name(hr),hr['spec']['targetNamespace'],child_values(outer,name),('--include-crds',)))
 return result
