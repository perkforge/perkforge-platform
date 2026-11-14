"""Controlled Portal org query binding; no live permissions or tenant exposure."""
from pathlib import Path
import os,subprocess,tempfile,unittest,yaml
from fixtures.render_helpers import build,helm,ordered_values,child_values,release_name
ROOT=Path(__file__).resolve().parents[2]
SOURCE=ROOT/'configuration/observability/log-boundary'
class PortalLogQuery(unittest.TestCase):
 def test_exact_generated_profile_changes_only_portal_read_scope(self):
  with tempfile.TemporaryDirectory() as t:
   out=Path(t)/'out'
   r=subprocess.run(['ansible-playbook','-i','localhost,',str(SOURCE/'render.yaml'),'-e','@'+str(SOURCE/'phase-a/profile.yaml'),'-e','@'+str(SOURCE/'phase-b/profile.yaml'),'-e','log_boundary_render=true','-e','log_output_dir='+str(out)],capture_output=True,text=True)
   self.assertEqual(r.returncode,0,r.stdout+r.stderr)
   self.assertEqual((out/'boundary-values.yaml').read_text(),(SOURCE/'phase-b/boundary-values.yaml').read_text())
  a=yaml.safe_load((SOURCE/'phase-a/boundary-values.yaml').read_text());b=yaml.safe_load((SOURCE/'phase-b/boundary-values.yaml').read_text())
  conf=b['loki']['values']['gateway']['nginxConfig']['file']
  line='    "pf-log-portal-read" "portal-runtime-v1";\n'
  self.assertEqual(conf.count(line),1)
  b['loki']['values']['gateway']['nginxConfig']['file']=conf.replace(line,'')
  self.assertEqual(a,b)
 def test_root_keeps_mattermost_and_platform_objects(self):
  def index(name):return {(x['kind'],x.get('metadata',{}).get('namespace'),x['metadata']['name']):x for x in build(ROOT/'clusters'/name)}
  a=index('local-scoped-logging-mattermost');b=index('local-portal-log-acceptance')
  self.assertEqual(set(b)-set(a),{('ConfigMap','bigbang','values-portal-log-query'),('ConfigMap','bigbang','values-portal-log-datasource')})
  key=('HelmRelease','bigbang','bigbang');old=a.pop(key);new=b.pop(key)
  self.assertEqual(new['spec']['valuesFrom'][:-2],old['spec']['valuesFrom']);new['spec']['valuesFrom']=old['spec']['valuesFrom'];self.assertEqual(old,new)
  for key,value in a.items():self.assertEqual(value,b[key],key)
 def test_datasource_is_exact_read_only_org_binding(self):
  v=yaml.safe_load((SOURCE/'phase-b/grafana-values.yaml').read_text())['grafana']['values']['upstream']
  self.assertEqual(set(v),{'envValueFrom','datasources'})
  self.assertEqual(set(v['envValueFrom']),{'PF_PORTAL_LOKI_USERNAME','PF_PORTAL_LOKI_PASSWORD'})
  for x in v['envValueFrom'].values():self.assertEqual(x['secretKeyRef']['name'],'loki-boundary-query-portal-v1')
  self.assertEqual(set(v['datasources']),{'datasources-loki-portal.yaml'})
  d=v['datasources']['datasources-loki-portal.yaml']['datasources'];self.assertEqual(len(d),1)
  self.assertEqual((d[0]['uid'],d[0]['orgId']),('loki-portal',2));self.assertFalse(d[0]['editable']);self.assertFalse(d[0]['jsonData']['tlsSkipVerify'])
 def test_pinned_native_grafana_preserves_platform_and_oauth(self):
  sources=os.environ.get('PREFLIGHT_SOURCES_DIR')
  if not sources:self.skipTest('Exact pinned source required')
  src=Path(sources);objects=build(ROOT/'clusters/local');parent=next(x for x in objects if x['kind']=='HelmRelease')
  values=ordered_values(objects,parent)+[(ROOT/'configuration/observability/candidate-values.yaml').read_text(),(ROOT/'configuration/observability/integrated-logging/values.yaml').read_text()]
  for file in [SOURCE/'phase-a/boundary-values.yaml',SOURCE/'phase-a/grafana-values.yaml',ROOT/'configuration/authorization/sso/grafana/orgs/platform-only-values.yaml',SOURCE/'phase-a/dashboard-values.yaml',SOURCE/'phase-b/boundary-values.yaml',SOURCE/'phase-b/grafana-values.yaml']:values.append(file.read_text())
  outer=helm(src/'bigbang/chart','bigbang','bigbang',values,('--set','monitoring.enabled=true','--set','grafana.enabled=true'))
  hr=next(x for x in outer if x['kind']=='HelmRelease' and x['metadata']['name']=='grafana')
  rendered=helm(src/'grafana/chart',release_name(hr),hr['spec']['targetNamespace'],child_values(outer,'grafana'))
  data={k:v for x in rendered if x['kind']=='ConfigMap' for k,v in x.get('data',{}).items()}
  for name in ['datasources-loki-platform.yaml','datasources-loki-portal.yaml']:self.assertIn(name,data)
  self.assertIn('pf-observability-platform-viewer:1:Viewer',data['grafana.ini']);self.assertNotIn('pf-observability-portal',data['grafana.ini'])
  dep=next(x for x in rendered if x['kind']=='Deployment');env=next(c for c in dep['spec']['template']['spec']['containers'] if c['name']=='grafana')['env'];names={x['name'] for x in env}
  self.assertTrue({'PF_LOKI_USERNAME','PF_LOKI_PASSWORD','PF_LOKI_CA_CERT','PF_PORTAL_LOKI_USERNAME','PF_PORTAL_LOKI_PASSWORD'}<=names)
