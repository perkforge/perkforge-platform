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
    def test_generated_runtime_is_exact_and_folder_gate_is_inert(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t);r=render(p);self.assertEqual(r.returncode,0,r.stdout+r.stderr)
            self.assertEqual((p/'out/values.yaml').read_text(),(SOURCE/'runtime/values.yaml').read_text())
            gate=yaml.safe_load((SOURCE/'prepare-folder.yaml').read_text())[0]
            self.assertFalse(gate['vars']['app_dashboard_folder_apply'])
            r=subprocess.run(['ansible-playbook','-i','localhost,',str(SOURCE/'prepare-folder.yaml')],capture_output=True,text=True,timeout=30)
            self.assertEqual(r.returncode,0,r.stdout+r.stderr)
            self.assertIn('changed=0',r.stdout)
    def test_exact_native_creator_acl_guard_rejects_other_users_and_teams(self):
        tasks=yaml.safe_load((SOURCE/'prepare-folder.yaml').read_text())[0]['tasks'][0]['block']
        guard=next(x for x in tasks if x.get('loop')=='{{ permissions.json }}')['ansible.builtin.assert']
        for item,expected in [({'userId':1,'teamId':0,'permission':4,'inherited':False},0),({'userId':1,'teamId':0,'role':None,'permission':4,'inherited':False},0),({'userId':2,'teamId':0,'role':None,'permission':4,'inherited':False},2),({'userId':1,'teamId':0,'role':None,'permission':1,'inherited':False},2),({'userId':0,'teamId':3,'role':'Viewer','permission':1,'inherited':False},2)]:
            with tempfile.TemporaryDirectory() as t:
                p=Path(t);play=[{'hosts':'localhost','connection':'local','gather_facts':False,'vars':{'item':item,'creator':{'json':{'id':1}}},'tasks':[{'ansible.builtin.assert':guard}]}]
                (p/'guard.yaml').write_text(yaml.safe_dump(play));r=subprocess.run(['ansible-playbook','-i','localhost,',str(p/'guard.yaml')],capture_output=True,text=True,timeout=30);self.assertEqual(r.returncode,expected,r.stdout+r.stderr)
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
    def test_optional_pinned_native_chart_mount_and_preservation(self):
        chart = os.environ.get('GRAFANA_CHART_DIR')
        if not chart:
            self.skipTest('Set existing Grafana BB chart path for native Helm render; no download')
        metadata = yaml.safe_load((Path(chart) / 'Chart.yaml').read_text())
        self.assertEqual(metadata['version'], '13.2.4-bb.0')
        self.assertEqual(metadata['appVersion'], '13.2.1')
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp); result = render(p)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            command = [os.environ.get('HELM_BIN', 'helm'), 'template', 'grafana', chart, '--namespace', 'monitoring']
            baseline = subprocess.run(command, capture_output=True, text=True, check=True)
            candidate = subprocess.run(command + ['-f', str(p / 'out/helm-values.yaml')], capture_output=True, text=True, check=True)
            def objects(text):
                return {(v['kind'], v['metadata']['name']): v for v in yaml.safe_load_all(text) if v}
            before, after = objects(baseline.stdout), objects(candidate.stdout)
            for key, obj in before.items():
                if key[0] not in ['Deployment', 'ConfigMap']:
                    self.assertEqual(after[key], obj)
                if key[0] == 'ConfigMap':
                    for name, data in obj.get('data', {}).items():
                        self.assertEqual(after[key]['data'][name], data)
            added = [v for k, v in after.items() if k not in before and k[0] == 'ConfigMap']
            dashboard = next(v for v in added if 'nextcloud.json' in v.get('data', {}))
            self.assertEqual(json.loads(dashboard['data']['nextcloud.json'])['panels'][-1]['datasource']['uid'], 'prometheus')
            deployment = next(v for v in after.values() if v['kind'] == 'Deployment')
            pod = deployment['spec']['template']['spec']
            self.assertTrue(any(v.get('configMap', {}).get('name') == dashboard['metadata']['name'] for v in pod['volumes']))
            old_pod = next(v for v in before.values() if v['kind'] == 'Deployment')['spec']['template']['spec']
            for volume in old_pod['volumes']:
                self.assertIn(volume, pod['volumes'])
            for old_container in old_pod['containers']:
                current = next(c for c in pod['containers'] if c['name'] == old_container['name'])
                for key, value in old_container.items():
                    if key == 'volumeMounts':
                        for mount in value:
                            self.assertIn(mount, current[key])
                    else:
                        self.assertEqual(current[key], value)
            grafana = next(c for c in pod['containers'] if c['name'] == 'grafana')
            self.assertTrue(any(v['mountPath'].endswith('/pf-app-resources/nextcloud.json') for v in grafana['volumeMounts']))


if __name__=='__main__':unittest.main()
