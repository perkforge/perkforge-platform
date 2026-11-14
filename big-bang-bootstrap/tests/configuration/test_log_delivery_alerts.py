"""Rules-only provisioning, exact metric scrape, preserved receiver/group state."""
import hashlib,json,os,subprocess,tempfile,unittest
from pathlib import Path
import yaml
M=Path(__file__).resolve().parents[2]/'configuration/observability/log-delivery-alerts'
class DeliveryAlerts(unittest.TestCase):
 def test_default_and_check_are_inert(self):
  for file,flag in [('render.yaml','log_delivery_render'),('update.yaml','log_delivery_update')]:
   for args in [[],['--check','-e',flag+'=true']]:
    r=subprocess.run(['ansible-playbook','-i','localhost,',str(M/file),*args],capture_output=True,text=True)
    self.assertEqual(r.returncode,0,r.stdout+r.stderr)
 def test_render_and_exact_scrape(self):
  with tempfile.TemporaryDirectory() as t:
   values={'log_delivery_render':True,'log_delivery_output':t,'log_delivery_grafana_url':'https://grafana.example.test/','log_delivery_runbook_url':'https://docs.example.test/log-delivery'}
   r=subprocess.run(['ansible-playbook','-i','localhost,',str(M/'render.yaml'),'-e',json.dumps(values)],capture_output=True,text=True);self.assertEqual(r.returncode,0,r.stdout+r.stderr)
   doc=yaml.safe_load((Path(t)/'groups.yaml').read_text());self.assertEqual(set(doc),{'apiVersion','groups'});rules=doc['groups'][0]['rules'];self.assertEqual(len(rules),3)
   self.assertEqual({x['uid'] for x in rules},{'pf-log-delivery-drops','pf-log-delivery-retries','pf-log-delivery-telemetry'})
   for rule in rules:
    self.assertEqual(rule['notification_settings']['receiver'],'platform-resource-ntfy');self.assertEqual(rule['noDataState'],'KeepLast');self.assertEqual(rule['execErrState'],'Error');self.assertEqual(rule['annotations']['dashboard_url'],'https://grafana.example.test/d/pf-pod-logs')
   sm=yaml.safe_load((M/'servicemonitor.yaml').read_text());self.assertEqual(sm['kind'],'ServiceMonitor');self.assertEqual(sm['metadata']['namespace'],'alloy');self.assertEqual(sm['spec']['namespaceSelector'],{'matchNames':['alloy']});self.assertEqual(sm['spec']['endpoints'][0]['port'],'http-metrics');self.assertEqual(sm['spec']['selector']['matchLabels']['app.kubernetes.io/instance'],'alloy-alloy-logs');self.assertIn('loki_process_dropped_lines_total',sm['spec']['endpoints'][0]['metricRelabelings'][0]['regex'])
 def test_update_preserves_ntfy_mattermost_and_other_groups(self):
  play=yaml.safe_load((M/'update.yaml').read_text())[0];inner=next(t['block'] for t in play['tasks'][0]['block'] if t.get('no_log'))
  start=next(i for i,t in enumerate(inner) if 'authored' in t.get('ansible.builtin.set_fact',{}));end=next(i for i,t in enumerate(inner) if t.get('when')=='prior != desired');checks=inner[start+1:end]
  authored={'groups':[{'name':'platform-log-delivery','orgId':1,'folder':'PerkForge platform resources','rules':[{'uid':'pf-log-delivery-drops'},{'uid':'pf-log-delivery-retries'},{'uid':'pf-log-delivery-telemetry'}]}]}
  base={'apiVersion':1,'contactPoints':[{'name':'platform-resource-ntfy','receivers':[{'uid':'ntfy','secret':'synthetic'}, {'uid':'mattermost','secret':'synthetic2'}]}],'groups':[{'name':'platform-resources','rules':[{'uid':'existing'}]}]}
  for prior,ok in [(base,True),({**base,'groups':base['groups']+authored['groups']},True),({**base,'groups':base['groups']+[{'name':'platform-log-delivery','orgId':1,'folder':'PerkForge platform resources','rules':[{'uid':'unrelated'}]}]},False),({**base,'groups':base['groups']+[{**authored['groups'][0],'orgId':2}]},False),({**base,'groups':base['groups']+[{**authored['groups'][0],'folder':'Foreign folder'}]},False)]:
   text=yaml.safe_dump(prior)
   with tempfile.TemporaryDirectory() as t:
    path=Path(t)/'check.yaml';path.write_text(yaml.safe_dump([{'hosts':'localhost','connection':'local','gather_facts':False,'vars':{'prior':prior,'prior_text':text,'authored':authored,'log_delivery_org_id':1,'grafana_ntfy_previous_sha256':hashlib.sha256(text.encode()).hexdigest()},'tasks':[{'no_log':True,'block':checks}]}]))
    r=subprocess.run(['ansible-playbook','-i','localhost,',str(path)],capture_output=True,text=True);self.assertEqual(r.returncode==0,ok,r.stdout+r.stderr);self.assertNotIn('synthetic2',r.stdout+r.stderr)
 def test_native_prometheus_sustained_and_missing_semantics(self):
  binary=os.environ.get('PROMTOOL_TEST_BINARY')
  if not binary:self.skipTest('Explicit native promtool required')
  rules=yaml.safe_load((M/'rules.yaml').read_text())['log_delivery_rules'];labels='{namespace="alloy",service="alloy-alloy-logs"}'
  def series(name,values):return {'series':name+labels,'values':values}
  def case(drops,retries,up,when,firing):
   return {'interval':'1m','input_series':[series('loki_write_dropped_entries_total',drops),series('loki_write_batch_retries_total',retries),series('up',up)],'alert_rule_test':[{'eval_time':when,'alertname':x['id'],'exp_alerts':[{'exp_labels':{},'exp_annotations':{}}] if x['id'] in firing else []} for x in rules]}
  tests=[case('0+0x4 10+0x30','0+0x40','1+0x40','20m',[]),case('0+10x40','0+1x40','1+0x40','25m',['drops','retries']),case('0+10x12 0+10x30','0+0x50','1+0x50','25m',['drops']),case('0+0x4 stale','0+0x4 stale','1+0x4 stale','8m',[]),case('0+0x4 stale','0+0x4 stale','1+0x4 stale','20m',['telemetry']),case('0+0x4 stale','0+0x4 stale','1+0x40','20m',['telemetry']),case('0+0x40','0+0x40','1+0x4 0+0x30','20m',['telemetry'])]
  with tempfile.TemporaryDirectory() as t:
   p=Path(t);(p/'rules.yaml').write_text(yaml.safe_dump({'groups':[{'name':'test','rules':[{'alert':x['id'],'expr':'('+x['expr']+') > 0','for':x['for']} for x in rules]}]}));(p/'tests.yaml').write_text(yaml.safe_dump({'rule_files':[str(p/'rules.yaml')],'evaluation_interval':'1m','tests':tests}));r=subprocess.run([binary,'test','rules',str(p/'tests.yaml')],capture_output=True,text=True);self.assertEqual(r.returncode,0,r.stdout+r.stderr)

 def test_native_grafana_paused_import(self):
  binary=os.environ.get('GRAFANA_VALIDATE_BIN')
  if not binary:self.skipTest('Explicit checksum-pinned native Grafana required')
  import base64,socket,time,urllib.request
  pins=yaml.safe_load((M.parent/'tenant-query/sources.yaml').read_text());self.assertEqual(hashlib.sha256(Path(binary).read_bytes()).hexdigest(),pins['grafana']['linux_amd64_binary_sha256'])
  with tempfile.TemporaryDirectory() as t:
   p=Path(t);prov=p/'provisioning';alerts=prov/'alerting';alerts.mkdir(parents=True);(prov/'datasources').mkdir()
   values={'log_delivery_render':True,'log_delivery_output':str(alerts),'log_delivery_grafana_url':'https://grafana.example.test/','log_delivery_runbook_url':'https://docs.example.test/log-delivery'}
   r=subprocess.run(['ansible-playbook','-i','localhost,',str(M/'render.yaml'),'-e',json.dumps(values)],capture_output=True,text=True);self.assertEqual(r.returncode,0,r.stdout+r.stderr)
   doc=yaml.safe_load((alerts/'groups.yaml').read_text())
   for rule in doc['groups'][0]['rules']:rule['isPaused']=True
   doc['contactPoints']=[{'orgId':1,'name':'platform-resource-ntfy','receivers':[{'uid':'synthetic-local','type':'webhook','settings':{'url':'http://127.0.0.1:9/'}}]}];(alerts/'groups.yaml').write_text(yaml.safe_dump(doc));(prov/'datasources/prom.yaml').write_text(yaml.safe_dump({'apiVersion':1,'datasources':[{'name':'Prometheus','uid':'prometheus','type':'prometheus','url':'http://127.0.0.1:9','access':'proxy'}]}))
   with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
   cfg=p/'grafana.ini';cfg.write_text(f'[server]\nhttp_addr=127.0.0.1\nhttp_port={port}\n[paths]\ndata={t}/data\nlogs={t}/logs\nplugins={t}/plugins\nprovisioning={prov}\n[security]\nadmin_user=fixture\nadmin_password=synthetic\n[analytics]\nreporting_enabled=false\ncheck_for_updates=false\ncheck_for_plugin_updates=false\n[plugins]\npreinstall_disabled=true\n')
   with (p/'log').open('w') as log:
    process=subprocess.Popen([binary,'server','--homepath',str(Path(binary).parents[1]),'--config',str(cfg)],stdout=log,stderr=log)
    try:
     for _ in range(200):
      if process.poll() is not None:self.fail((p/'log').read_text()[-3000:])
      try:
       req=urllib.request.Request(f'http://127.0.0.1:{port}/api/v1/provisioning/alert-rules',headers={'Authorization':'Basic '+base64.b64encode(b'fixture:synthetic').decode()})
       with urllib.request.urlopen(req,timeout=1) as response:actual=json.load(response)
       break
      except OSError:time.sleep(.1)
     else:self.fail('Native Grafana provisioning unavailable')
     self.assertEqual(len(actual),3)
     for rule in actual:self.assertEqual(rule['noDataState'],'KeepLast');self.assertEqual(rule['execErrState'],'Error');self.assertTrue(rule['isPaused']);self.assertEqual(rule['provenance'],'file')
    finally:process.terminate();process.wait(timeout=15)
