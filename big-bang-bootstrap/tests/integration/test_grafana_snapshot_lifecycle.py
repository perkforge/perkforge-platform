"""Opt-in native synthetic lifecycle, not live GitLab or ntfy/MM delivery evidence.

Requires pre-cached images and PROMETHEUS_BINARY (official 3.14.0). No pulls,
ports, host networking, credentials or production changes. Production PromQL
is unchanged; only evaluation cadence and Prometheus lookback are shortened.
"""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
import uuid
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from configuration.test_gitlab_snapshot_metrics import fixture, render

GRAFANA = 'docker.io/grafana/grafana@sha256:1dec240d14e232597dce9bfa56dae55f4397b138cdc91e3ee92ac6b157e2fc49'
PYTHON = 'docker.io/library/python@sha256:e48f59cdba69a3cbd9ed2cf0f348d90d45a8d350d98134cf1070bc106ee9ed90'
PROM_SHA = '30576b9bd5fc4e4faa8bda23cb29f48a24ca27cbe9788c392ccf403f945163dc'
SERVER = r'''
import http.server,json,pathlib,subprocess,time
p=pathlib.Path('/fixture')
proc=subprocess.Popen(['/prometheus','--config.file=/fixture/prometheus.yaml','--storage.tsdb.path=/tmp/prometheus','--web.listen-address=127.0.0.1:9090','--query.lookback-delta=30s'])
class Handler(http.server.BaseHTTPRequestHandler):
 def log_message(self,*args): pass
 def do_POST(self):
  body=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
  with (p/'receipts').open('a') as f: f.write(json.dumps(body)+'\n')
  self.send_response(200);self.end_headers();self.wfile.write(b'ok')
 def do_GET(self):
  state=(p/'state').read_text().strip()
  if state=='outage': self.send_response(503);self.end_headers();return
  labels='project_id="7",project="tenants/example/proof",ref="main",source="push"'
  values={'valid':1,'observation_age_seconds':0,'last_success_timestamp_seconds':time.time(),'present':1}
  lines=['gcpe_pipeline_snapshot_'+k+'{'+labels+'} '+str(v) for k,v in values.items()]
  lines += ['gcpe_pipeline_snapshot_status{'+labels+',status="'+s+'"} '+str(int(s==state)) for s in ['failed','success','other']]
  self.send_response(200);self.send_header('Content-Type','text/plain; version=0.0.4');self.end_headers();self.wfile.write(('\n'.join(lines)+'\n').encode())
try: http.server.HTTPServer(('127.0.0.1',18080),Handler).serve_forever()
finally: proc.terminate();proc.wait(timeout=10)
'''

@unittest.skipUnless(os.environ.get('RUN_GRAFANA_SNAPSHOT_LIFECYCLE') == '1',
                     'opt-in; cached native runtimes required')
class NativeSnapshotLifecycle(unittest.TestCase):
    def test_failure_outage_resume_success(self):
        binary = Path(os.environ['PROMETHEUS_BINARY']).resolve()
        self.assertEqual(hashlib.sha256(binary.read_bytes()).hexdigest(), PROM_SHA)
        name = 'pf-snapshot-' + uuid.uuid4().hex[:10]
        side = name + '-source'
        def podman(*args, check=True):
            return subprocess.run(['podman', *args], check=check, capture_output=True,
                                  text=True, timeout=30)
        # Fail before creating anything if either exact image is not cached.
        for image in (GRAFANA, PYTHON): podman('image', 'exists', image)
        with tempfile.TemporaryDirectory(prefix='pf-snapshot-native-') as tmp:
            p=Path(tmp);p.chmod(0o755)
            config=render('snapshot-rules.yaml.j2', fixture())
            config['groups'][0]['interval']='10s'
            for rule in config['groups'][0]['rules']:
                rule['isPaused']=False
                rule['notification_settings']={'receiver':'synthetic-only','group_by':['incident_key'],
                    'group_wait':'0s','group_interval':'10s','repeat_interval':'1h'}
            config['contactPoints']=[{'orgId':1,'name':'synthetic-only','receivers':[{
                'uid':'synthetic-only','type':'webhook','settings':{'url':'http://127.0.0.1:18080/notifications'}}]}]
            (p/'alerts.yaml').write_text(yaml.safe_dump(config))
            (p/'datasource.yaml').write_text(yaml.safe_dump({'apiVersion':1,'datasources':[{
                'name':'synthetic-prom','uid':'synthetic-prom','type':'prometheus',
                'access':'proxy','url':'http://127.0.0.1:9090','isDefault':True}]}))
            (p/'prometheus.yaml').write_text(yaml.safe_dump({'global':{'scrape_interval':'2s'},
                'scrape_configs':[{'job_name':'synthetic','static_configs':[{'targets':['127.0.0.1:18080']}]}]}))
            (p/'server.py').write_text(SERVER)
            (p/'state').write_text('failed')
            def get(path):
                r=podman('exec',name,'wget','-qO-',
                    'http://admin:synthetic-only@127.0.0.1:3000'+path,check=False)
                return json.loads(r.stdout) if r.returncode==0 else None
            def state(kind='incident'):
                data=get('/api/prometheus/grafana/api/v1/rules')
                if not data:return None
                for group in data['data']['groups']:
                    for rule in group['rules']:
                        if rule.get('name')=='GitLab snapshot '+kind+' synthetic-main':return rule['state']
            def await_state(expected,timeout=100):
                end=time.monotonic()+timeout
                while time.monotonic()<end:
                    if state()==expected:return
                    time.sleep(2)
                self.fail('incident did not reach '+expected+'; got '+str(state()))
            def receipts():
                if not (p/'receipts').exists():return []
                return [json.loads(x) for x in (p/'receipts').read_text().split('\n')[:-1]]
            def incident_notifications(status):
                return [a for r in receipts() for a in r.get('alerts',[])
                    if a.get('labels',{}).get('incident_key')=='synthetic-main-incident' and a['status']==status]
            try:
                podman('run','-d','--name',name,'--pull=never','--network=none',
                    '--cap-drop=ALL','--security-opt=no-new-privileges',
                    '-e','GF_SECURITY_ADMIN_PASSWORD=synthetic-only',
                    '-e','GF_ANALYTICS_REPORTING_ENABLED=false','-e','GF_ANALYTICS_CHECK_FOR_UPDATES=false',
                    '-e','GF_PLUGINS_PREINSTALL_DISABLED=true',
                    '-v',f'{p}/alerts.yaml:/etc/grafana/provisioning/alerting/test.yaml:ro',
                    '-v',f'{p}/datasource.yaml:/etc/grafana/provisioning/datasources/test.yaml:ro',GRAFANA)
                podman('run','-d','--name',side,'--pull=never','--network=container:'+name,
                    '--cap-drop=ALL','--security-opt=no-new-privileges',
                    '-v',f'{p}:/fixture','-v',f'{binary}:/prometheus:ro',PYTHON,'python','/fixture/server.py')
                await_state('firing')
                self.assertEqual(get('/api/health')['version'],'13.2.1')
                end=time.monotonic()+60
                while not incident_notifications('firing') and time.monotonic()<end:time.sleep(2)
                self.assertTrue(incident_notifications('firing'))
                (p/'state').write_text('outage')
                # Beyond unchanged freshness90s AND test lookback30s, with many evaluations.
                end=time.monotonic()+110
                while time.monotonic()<end:
                    self.assertEqual(state(),'firing')
                    self.assertFalse(incident_notifications('resolved'))
                    time.sleep(5)
                self.assertEqual(state('health'),'firing')
                query=podman('exec',name,'wget','-qO-',
                    'http://127.0.0.1:9090/api/v1/query?query=up').stdout
                self.assertEqual(json.loads(query)['data']['result'][0]['value'][1],'0')
                query=podman('exec',name,'wget','-qO-',
                    'http://127.0.0.1:9090/api/v1/query?query=gcpe_pipeline_snapshot_valid').stdout
                self.assertEqual(json.loads(query)['data']['result'],[])
                (p/'state').write_text('failed')
                time.sleep(25)
                self.assertEqual(state(),'firing')
                self.assertFalse(incident_notifications('resolved'))
                (p/'state').write_text('success')
                await_state('inactive')
                end=time.monotonic()+40
                while not incident_notifications('resolved') and time.monotonic()<end:time.sleep(2)
                self.assertTrue(incident_notifications('resolved'))
                print('Native synthetic receipt: firing -> 110s collection outage retained -> fresh failed retained -> fresh success resolved; no live delivery claim.')
            finally:
                podman('rm','-f',side,check=False)
                podman('rm','-f',name,check=False)

if __name__=='__main__':unittest.main()
