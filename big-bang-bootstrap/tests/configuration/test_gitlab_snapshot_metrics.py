"""Default-off template/schema checks plus optional installed native PromQL evaluation."""
import copy
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest
import jinja2
import yaml

BASE = Path(__file__).resolve().parents[2] / 'configuration/packages/gitlab/events/metrics'
spec = importlib.util.spec_from_file_location('snapshot_inputs', BASE / 'verify_snapshot_inputs.py')
guard = importlib.util.module_from_spec(spec); spec.loader.exec_module(guard)


def fixture(source='push'):
    return dict(snapshot_enabled=False, context_id='synthetic', grafana_org_id=1,
                prometheus_uid='synthetic-prom', gitlab_url='https://gitlab.example.test',
                interval_seconds=30, timeout_seconds=10, freshness_seconds=90,
                snapshot_targets=[dict(uid='synthetic-main', project_id=7,
                                       project='tenants/example/proof', ref='main', source=source)])


def render(name, v):
    guard.verify(v)
    env = jinja2.Environment(undefined=jinja2.StrictUndefined)
    env.filters.update(to_json=json.dumps, regex_escape=re.escape)
    return yaml.safe_load(env.from_string((BASE / name).read_text()).render(**v))


class SnapshotMetrics(unittest.TestCase):
    def test_default_off_and_paused(self):
        c = render('snapshot-exporter.yaml.j2', fixture())
        self.assertFalse(c['pipeline_snapshot']['enabled'])
        self.assertFalse(c['pull']['metrics']['on_init'])
        self.assertFalse(c['pull']['metrics']['scheduled'])
        self.assertEqual(c['wildcards'], [])
        self.assertTrue(all(not x['on_init'] and not x['scheduled'] for x in c['garbage_collect'].values()))
        self.assertNotIn('token', c['gitlab'])
        self.assertFalse(c['server']['webhook']['enabled'])
        self.assertFalse(c['server']['enable_pprof'])
        p = c['project_defaults']['pull']
        for k in ['jobs', 'variables', 'test_reports']:
            self.assertFalse(p['pipeline'][k]['enabled'])
        for k in ['tags', 'merge_requests']:
            self.assertFalse(p['refs'][k]['enabled'])
        self.assertFalse(p['environments']['enabled'])
        rules = render('snapshot-rules.yaml.j2', fixture())['groups'][0]['rules']
        self.assertEqual(len(rules), 2)
        self.assertTrue(all(r['isPaused'] for r in rules))
        self.assertEqual(rules[0]['noDataState'], 'KeepLast')
        self.assertEqual(rules[0]['execErrState'], 'KeepLast')
        self.assertEqual(rules[1]['noDataState'], 'Alerting')
        self.assertNotIn('vector(0)', rules[0]['data'][0]['model']['expr'])
        self.assertEqual(set(rules[0]['labels']), {'context', 'project_id', 'event_class', 'incident_key'})
        self.assertNotIn('proof', rules[0]['annotations']['summary'])

    def test_literal_branch_and_consistent_projects(self):
        v = fixture(); v['snapshot_targets'][0]['ref'] = 'release/v1.2'
        v['snapshot_targets'].append(dict(v['snapshot_targets'][0], uid='second', ref='main'))
        c = render('snapshot-exporter.yaml.j2', v)
        self.assertEqual(len(c['projects']), 1)
        self.assertEqual(c['projects'][0]['pull']['refs']['branches']['regexp'], r'^(release/v1\.2|main)$')

    def test_explicit_source_identity(self):
        v=fixture('web')
        config=render('snapshot-exporter.yaml.j2',v)
        self.assertEqual(config['pipeline_snapshot']['targets'][0]['source'],'web')
        rules=render('snapshot-rules.yaml.j2',v)['groups'][0]['rules']
        self.assertTrue(all('source="web"' in r['data'][0]['model']['expr'] for r in rules))
        self.assertTrue(all('source="push"' not in r['data'][0]['model']['expr'] for r in rules))
        v['snapshot_targets'].append(dict(v['snapshot_targets'][0],uid='push-scope',source='push'))
        guard.verify(v)
        self.assertEqual(len(render('snapshot-rules.yaml.j2',v)['groups'][0]['rules']),4)
        for source in ['schedule','api','trigger','parent_pipeline','pipeline','merge_request_event','*',[],True]:
            bad=fixture();bad['snapshot_targets'][0]['source']=source
            with self.assertRaises(ValueError):guard.verify(bad)

    def test_strict_inputs(self):
        mutations = [lambda v: v.update(token='not-allowed'), lambda v: v.update(snapshot_enabled=1),
                     lambda v: v.update(gitlab_url='https://user:pass@example.test'),
                     lambda v: v.update(gitlab_url='https://example.test/api'),
                     lambda v: v.update(freshness_seconds=91), lambda v: v.update(interval_seconds=True),
                     lambda v: v.update(snapshot_targets=[])]
        for key, value in [('source','merge_request_event'), ('ref','main.*'), ('ref','../main'),
                           ('ref','refs//main'), ('ref','a.lock'), ('project_id',True),
                           ('project','tenants/../proof'), ('url','https://foreign.test')]:
            mutations.append(lambda v,k=key,x=value: v['snapshot_targets'][0].update({k:x}))
        for change in mutations:
            v=fixture();change(v)
            with self.assertRaises(ValueError):guard.verify(v)
        for second in [dict(fixture()['snapshot_targets'][0],uid='other'),
                       dict(fixture()['snapshot_targets'][0],uid='other',project='foreign/proof'),
                       dict(fixture()['snapshot_targets'][0],uid='other',project_id=8)]:
            v=fixture();v['snapshot_targets'].append(second)
            with self.assertRaises(ValueError):guard.verify(v)
        v=fixture();v['interval_seconds']=300;v['timeout_seconds']=1;v['freshness_seconds']=300
        v['snapshot_targets']=[dict(v['snapshot_targets'][0],uid='target-'+str(i),ref='branch-'+str(i)) for i in range(16)]
        guard.verify(v)
        v['snapshot_targets'].append(dict(v['snapshot_targets'][0],uid='excess',ref='excess'))
        with self.assertRaises(ValueError):guard.verify(v)

    def test_native_promql_push(self):
        self._native_promql('push')

    def test_native_promql_web(self):
        self._native_promql('web')

    def _native_promql(self, source):
        promtool=os.environ.get('PROMTOOL') or shutil.which('promtool')
        if not promtool:self.skipTest('Installed promtool not selected; offline checks only')
        rules=render('snapshot-rules.yaml.j2',fixture(source))['groups'][0]['rules']
        incident,health=[r['data'][0]['model']['expr'] for r in rules]
        labels='project_id="7",project="tenants/example/proof",ref="main",source="'+source+'"'
        tests=[]
        # Each vector is the collector's atomically published snapshot, not an event ledger.
        for name,valid,present,age,stamp,status,expected in [
            ('failed',1,1,5,100,'failed',1), ('success',1,1,5,100,'success',0),
            ('running',1,1,5,100,'other',None), ('canceled',1,1,5,100,'other',None),
            ('empty',1,0,5,100,'other',None), ('poll-error',0,1,5,100,'failed',None),
            ('stale',1,1,91,100,'success',None), ('cold',0,0,-1,0,'other',None),
            ('boundary',1,1,90,100,'failed',1), ('negative-age',1,1,-1,100,'success',None)]:
            values={'valid':valid,'present':present,'observation_age_seconds':age,'last_success_timestamp_seconds':stamp}
            series=[{'series':'gcpe_pipeline_snapshot_'+k+'{'+labels+'}','values':'_ '+str(v)} for k,v in values.items()]
            series += [{'series':'gcpe_pipeline_snapshot_status{'+labels+',status="'+s+'"}','values':'_ '+str(int(s==status))} for s in ('failed','success','other')]
            ok=valid==1 and 0<=age<=90 and stamp>0
            tests.append({'name':name,'interval':'100s','input_series':series,'promql_expr_test':[
                {'expr':incident,'eval_time':'100s','exp_samples':[] if expected is None else [{'labels':'{}','value':expected}]},
                {'expr':health,'eval_time':'100s','exp_samples':[{'labels':'{}','value':0 if ok else 1}]}]})
        tests.append({'name':'missing-exporter','promql_expr_test':[{'expr':incident,'eval_time':'100s','exp_samples':[]},{'expr':health,'eval_time':'100s','exp_samples':[{'labels':'{}','value':1}]}]})
        # Missing age must not allow historical success to resolve an incident.
        missing=copy.deepcopy(tests[1]);missing['name']='missing-age';missing['input_series']=[s for s in missing['input_series'] if '_observation_age_seconds{' not in s['series']]
        missing['promql_expr_test'][0]['exp_samples']=[];missing['promql_expr_test'][1]['exp_samples']=[{'labels':'{}','value':1}];tests.append(missing)
        duplicate=copy.deepcopy(tests[1]);duplicate['name']='duplicate-scrape'
        duplicate['input_series'] += [dict(s,series=s['series'].replace('{','{replica="other",',1)) for s in duplicate['input_series'][:]]
        duplicate['promql_expr_test'][0]['exp_samples']=[];duplicate['promql_expr_test'][1]['exp_samples']=[{'labels':'{}','value':1}];tests.append(duplicate)
        foreign=copy.deepcopy(tests[0]);foreign['name']='foreign-success-cannot-resolve'
        foreign['input_series'] += [dict(s,series=s['series'].replace('project_id="7"','project_id="8"')) for s in tests[1]['input_series']]
        tests.append(foreign)
        missing_status=copy.deepcopy(tests[1]);missing_status['name']='missing-status'
        missing_status['input_series']=[s for s in missing_status['input_series'] if 'status="failed"' not in s['series']]
        missing_status['promql_expr_test'][0]['exp_samples']=[];missing_status['promql_expr_test'][1]['exp_samples']=[{'labels':'{}','value':1}];tests.append(missing_status)
        # Prometheus retains an old sample for its lookback window: bound actual scrape age too.
        for base in (0,1):
            for elapsed, healthy in [(85,True),(86,False),(120,False)]:
                t=copy.deepcopy(tests[base]);t['name']='stopped-scrape-'+str(base)+'-'+str(elapsed)
                for q in t['promql_expr_test']:q['eval_time']=str(100+elapsed)+'s'
                if not healthy:
                    t['promql_expr_test'][0]['exp_samples']=[]
                    t['promql_expr_test'][1]['exp_samples']=[{'labels':'{}','value':1}]
                tests.append(t)
        for name,metric,value in [('old-observation-plus-scrape','observation_age_seconds','80'),
                                  ('future-completion','last_success_timestamp_seconds','201'),
                                  ('fractional-presence','present','0.5'),
                                  ('incoherent-scrape','present',None),
                                  ('contradictory-status','status',None)]:
            t=copy.deepcopy(tests[1]);t['name']=name
            for item in t['input_series']:
                if ('snapshot_'+metric+'{') in item['series']:
                    if name=='incoherent-scrape':item['values']='1 _'
                    elif name=='contradictory-status':
                        if 'status="other"' in item['series']:item['values']='_ 1'
                    else:item['values']='_ '+value
            if name=='old-observation-plus-scrape':
                for q in t['promql_expr_test']:q['eval_time']='120s'
            t['promql_expr_test'][0]['exp_samples']=[]
            t['promql_expr_test'][1]['exp_samples']=[{'labels':'{}','value':1}];tests.append(t)
        foreign_source=copy.deepcopy(tests[0]);foreign_source['name']='foreign-source-success-cannot-resolve'
        other='web' if source=='push' else 'push'
        foreign_source['input_series'] += [dict(s,series=s['series'].replace('source="'+source+'"','source="'+other+'"')) for s in tests[1]['input_series']]
        tests.append(foreign_source)
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'tests.yaml';p.write_text(yaml.safe_dump({'rule_files':[],'evaluation_interval':'1s','tests':tests}))
            result=subprocess.run([promtool,'test','rules',str(p)],capture_output=True,text=True,timeout=30)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)

if __name__=='__main__':unittest.main()
