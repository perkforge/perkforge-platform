"""Platform-only activation preservation; no cluster credentials or mutations."""
from pathlib import Path
import subprocess,tempfile,unittest,yaml
from fixtures.render_helpers import build
ROOT=Path(__file__).resolve().parents[2]
SOURCE=ROOT/'configuration/observability/log-boundary'
class ScopedLoggingPhaseA(unittest.TestCase):
 def test_current_root_preserved_with_only_explicit_additions(self):
  def index(name):return {(x['kind'],x.get('metadata',{}).get('namespace'),x['metadata']['name']):x for x in build(ROOT/'clusters'/name)}
  old=index('local-integrated-logging');new=index('local-scoped-logging')
  extra=set(new)-set(old)
  self.assertEqual(extra,{('ConfigMap','bigbang','values-scoped-logging'),('ConfigMap','bigbang','values-scoped-logging-grafana'),('ConfigMap','bigbang','values-platform-log-oauth'),('ConfigMap','bigbang','values-platform-log-dashboard')})
  key=('HelmRelease','bigbang','bigbang');a=old.pop(key);b=new.pop(key)
  self.assertEqual(b['spec']['valuesFrom'][:-4],a['spec']['valuesFrom']);b['spec']['valuesFrom']=a['spec']['valuesFrom'];self.assertEqual(a,b)
  for key,obj in old.items():self.assertEqual(obj,new[key],key)
 def test_selected_values_are_exact_profile_output(self):
  with tempfile.TemporaryDirectory() as t:
   p=Path(t)/'out'
   r=subprocess.run(['ansible-playbook','-i','localhost,',str(SOURCE/'render.yaml'),'-e','@'+str(SOURCE/'phase-a/profile.yaml'),'-e','log_boundary_render=true','-e','log_output_dir='+str(p)],capture_output=True,text=True)
   self.assertEqual(r.returncode,0,r.stdout+r.stderr)
   for name in ['boundary-values.yaml','collector-rbac.yaml']:self.assertEqual((p/name).read_text(),(SOURCE/'phase-a'/name).read_text())
  v=yaml.safe_load((SOURCE/'phase-a/boundary-values.yaml').read_text())
  conf=v['loki']['values']['gateway']['nginxConfig']['file']
  self.assertIn('"platform-pilot" "platform-pilot";',conf);self.assertNotIn('"pf-log-portal-read"',conf)
  ds=yaml.safe_load((SOURCE/'phase-a/grafana-values.yaml').read_text())['grafana']['values']['upstream']
  self.assertEqual(set(ds['envValueFrom']),{'PF_LOKI_USERNAME','PF_LOKI_PASSWORD','PF_LOKI_CA_CERT'})
  self.assertEqual(set(ds['datasources']),{'datasources-loki-platform.yaml'})
  d=ds['datasources']['datasources-loki-platform.yaml']['datasources'][0]
  self.assertEqual((d['uid'],d['orgId']),('loki-platform',1));self.assertFalse(d['jsonData']['tlsSkipVerify'])
 def test_pinned_native_grafana_keeps_existing_maps_and_adds_only_platform_binding(self):
  import os
  from fixtures.render_helpers import helm,ordered_values,child_values,release_name
  sources=os.environ.get('PREFLIGHT_SOURCES_DIR')
  if not sources:self.skipTest('Exact pinned chart fixtures required')
  src=Path(sources);objects=build(ROOT/'clusters/local');parent=next(x for x in objects if x['kind']=='HelmRelease')
  values=ordered_values(objects,parent)+[(ROOT/'configuration/observability/candidate-values.yaml').read_text(),(ROOT/'configuration/observability/integrated-logging/values.yaml').read_text()]
  for file in [SOURCE/'phase-a/boundary-values.yaml',SOURCE/'phase-a/grafana-values.yaml',ROOT/'configuration/authorization/sso/grafana/orgs/platform-only-values.yaml',SOURCE/'phase-a/dashboard-values.yaml']:values.append(file.read_text())
  outer=helm(src/'bigbang/chart','bigbang','bigbang',values,('--set','monitoring.enabled=true','--set','grafana.enabled=true'))
  hr=next(x for x in outer if x['kind']=='HelmRelease' and x['metadata']['name']=='grafana')
  # Simulate the already verified later protected child-values maps, no secrets.
  previous={'upstream':{'envValueFrom':{'LOKI_USERNAME':{'secretKeyRef':{'name':'loki-query-auth','key':'username'}}},'datasources':{'datasourcesbb.yaml':{'apiVersion':1,'datasources':[{'name':'Prometheus','uid':'prometheus','type':'prometheus','url':'https://query.example.invalid'}]},'datasources-loki.yaml':{'apiVersion':1,'datasources':[{'name':'Loki pilot','uid':'loki-pilot','type':'loki','url':'https://pilot.example.invalid'}]}}}}
  rendered=helm(src/'grafana/chart',release_name(hr),hr['spec']['targetNamespace'],child_values(outer,'grafana')+[yaml.safe_dump(previous)])
  dep=next(x for x in rendered if x['kind']=='Deployment');env=next(c for c in dep['spec']['template']['spec']['containers'] if c['name']=='grafana')['env']
  self.assertTrue({'LOKI_USERNAME','PF_LOKI_USERNAME','PF_LOKI_PASSWORD','PF_LOKI_CA_CERT'} <= {x['name'] for x in env})
  data={k:v for x in rendered if x['kind']=='ConfigMap' for k,v in x.get('data',{}).items()}
  for name in ['datasourcesbb.yaml','datasources-loki.yaml','datasources-loki-platform.yaml']:self.assertIn(name,data)
  self.assertIn('pf-observability-platform-viewer:1:Viewer',data['grafana.ini'])
  dashboard=next(value for value in data.values() if '"uid": "pf-pod-logs"' in value)
  self.assertIn('loki-platform',dashboard);self.assertNotIn('loki-pilot',dashboard)
