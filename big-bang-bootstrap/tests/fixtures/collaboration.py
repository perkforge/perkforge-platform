"""Actual pinned review-profile rendering, not a configuration generator."""
from pathlib import Path
import os
from fixtures.render_helpers import build,ordered_values,helm,child_values,release_name

def package_render(root,name,others=()):
 src=Path(os.environ['PREFLIGHT_SOURCES_DIR']);objects=build(root/'clusters/local');parent=next(x for x in objects if x['kind']=='HelmRelease')
 values=ordered_values(objects,parent)+[(root/'configuration/packages'/name/'candidate-values.yaml').read_text()]
 outer=helm(src/'bigbang/chart','bigbang','bigbang',values,tuple(y for n in [name,*others] for y in ['--set','addons.'+{'mattermost-operator':'mattermostOperator'}.get(n,n)+'.enabled=true']))
 result={}
 for n in [name,*others]:
  hr=next(x for x in outer if x['kind']=='HelmRelease' and x['metadata']['name']==n)
  result[n]=(hr,helm(src/n/'chart',release_name(hr),hr['spec']['targetNamespace'],child_values(outer,n),('--include-crds',)))
 return result
