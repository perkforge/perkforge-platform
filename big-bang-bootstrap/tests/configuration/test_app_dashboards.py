"""Default-off native app dashboards; no live infrastructure changes."""
import json,os,subprocess,tempfile,unittest
from pathlib import Path
import yaml
ROOT=Path(__file__).resolve().parents[2]
SOURCE=ROOT/'configuration/observability/app-dashboards'
def render(folder, **changes):
    v=yaml.safe_load((SOURCE/'platform-profile.yaml').read_text());v.update(app_dashboards_render=True,app_dashboards_output=str(folder/'out'));v.update(changes)
    (folder/'inputs.yaml').write_text(yaml.safe_dump(v))
    return subprocess.run(['ansible-playbook','-i','localhost,',str(SOURCE/'render.yaml'),'-e','@'+str(folder/'inputs.yaml')],capture_output=True,text=True,timeout=90,env={**os.environ,'ANSIBLE_LOCAL_TEMP':str(folder/'ansible')})
class AppDashboards(unittest.TestCase):
    def test_default_off(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t);r=render(p,app_dashboards_render=False);self.assertEqual(r.returncode,0,r.stdout+r.stderr);self.assertFalse((p/'out').exists())
    def test_render_native_additive_maps_and_no_zero_fallback(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t);r=render(p);self.assertEqual(r.returncode,0,r.stdout+r.stderr)
            v=yaml.safe_load((p/'out/helm-values.yaml').read_text())['upstream'];self.assertEqual(set(v),{'dashboardProviders','dashboards'})
            self.assertEqual(v['dashboardProviders']['perkforge-app-resources.yaml']['providers'][0]['orgId'],1)
            self.assertEqual(len(v['dashboards']['pf-app-resources']),19)
            for key,value in v['dashboards']['pf-app-resources'].items():
                d=json.loads(value['json']);self.assertEqual(d,json.loads((p/'out'/f'{key}.json').read_text()));self.assertFalse(d['editable']);self.assertEqual(d['refresh'],'1m')
                for panel in d['panels'][1:]:
                    self.assertEqual(panel['fieldConfig']['defaults']['noValue'],'Unavailable');expr=panel['targets'][0]['expr'];self.assertNotIn('or vector(0)',expr)
                    self.assertIn('namespace=~',expr)
                    if 'container_network_' in expr:
                        self.assertIn('max by(namespace,pod,interface)',expr);self.assertIn('container=""',expr);self.assertIn('host_network="false"',expr);self.assertIn('interface!="lo"',expr)
    def test_boundary_rejects_tenant_org_and_regex_namespace(self):
        for changes in [dict(app_dashboards_org_id=2),dict(app_dashboards_org_id=True),dict(app_dashboards_apps=[dict(id='a',title='A',namespaces=['.*'])])]:
            with tempfile.TemporaryDirectory() as t:
                p=Path(t);r=render(p,**changes);self.assertNotEqual(r.returncode,0);self.assertFalse((p/'out').exists())
    def test_native_promql_network_dedup_host_exclusion_and_absent(self):
        binary=os.environ.get('PROMTOOL_VALIDATE_BIN')
        if not binary:self.skipTest('Set existing pinned promtool; no download')
        with tempfile.TemporaryDirectory() as t:
            p=Path(t);r=render(p,app_dashboards_apps=[dict(id='fixture',title='Fixture',namespaces=['fixture'])]);self.assertEqual(r.returncode,0,r.stdout+r.stderr)
            d=json.loads((p/'out/fixture.json').read_text());q=next(x['targets'][0]['expr'] for x in d['panels'] if x['title']=='Pod network receive (not HTTP)')
            labels='namespace="fixture",pod="p",interface="eth0",job="kubelet",metrics_path="/metrics/cadvisor"'
            data={'evaluation_interval':'1m','tests':[{'interval':'1m','input_series':[
                {'series':'container_network_receive_bytes_total{'+labels+',instance="a"}','values':'0+600x10'},
                {'series':'container_network_receive_bytes_total{'+labels+',instance="duplicate"}','values':'0+600x10'},
                {'series':'container_network_receive_bytes_total{'+labels.replace('pod="p"','pod="host"')+'}','values':'0+60000x10'},
                {'series':'kube_pod_info{namespace="fixture",pod="p",job="kube-state-metrics",host_network="false"}','values':'1x10'},
                {'series':'kube_pod_info{namespace="fixture",pod="host",job="kube-state-metrics",host_network="true"}','values':'1x10'}],
                'promql_expr_test':[{'expr':q,'eval_time':'5m','exp_samples':[{'labels':'{}','value':10}]},{'expr':q.replace('fixture','absent'),'eval_time':'5m','exp_samples':[]}]}]}
            (p/'prom.yaml').write_text(yaml.safe_dump(data));r=subprocess.run([binary,'test','rules',str(p/'prom.yaml')],capture_output=True,text=True);self.assertEqual(r.returncode,0,r.stdout+r.stderr)
if __name__=='__main__':unittest.main()
