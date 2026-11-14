"""Offline platform alert provisioning; synthetic token, no infrastructure calls."""
import hashlib,json,subprocess,tempfile,unittest
from pathlib import Path
import yaml
M=Path(__file__).resolve().parents[2]/'configuration/observability/platform-alerts'
class PlatformResourceAlerts(unittest.TestCase):
 def test_render(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);t=p/'token';t.write_text('synthetic-never-log');t.chmod(0o600);ca=p/'ca';ca.write_text('synthetic-ca\n')
   v=dict(platform_alerts_render=True,platform_alerts_topic='platform-alerts',platform_alerts_url='https://ntfy.example.test/',platform_alerts_grafana_url='https://grafana.example.test/',platform_alerts_runbook_url='https://docs.example.test/platform-alerts',platform_alerts_network_device_regex='eno.*|enp.*',platform_alerts_disk_device_regex='nvme.*',platform_alerts_output_dir=str(p/'out'),platform_alerts_token_file=str(t),platform_alerts_ca_file=str(ca),platform_alerts_ca_sha256=hashlib.sha256(ca.read_bytes()).hexdigest())
   def run(x):return subprocess.run(['ansible-playbook','-i','localhost,',str(M/'render.yaml'),'-e',json.dumps(x)],capture_output=True,text=True,timeout=30)
   r=run(v);self.assertEqual(r.returncode,0,r.stdout+r.stderr);self.assertNotIn('synthetic-never-log',r.stdout+r.stderr)
   out=yaml.safe_load((p/'out/alerting.yaml').read_text());self.assertNotIn('policies',out)
   receiver=out['contactPoints'][0]['receivers'][0];self.assertFalse(receiver['settings']['tlsConfig']['insecureSkipVerify']);self.assertFalse(receiver['disableResolveMessage'])
   tpl=receiver['settings']['payload']['template'];self.assertIn('data.ToJSON',tpl);self.assertIn('.GeneratorURL',tpl);self.assertIn('"click" $$click',tpl);self.assertNotIn('.CommonAnnotations',tpl);self.assertNotIn('TruncatedAlerts',tpl);self.assertIn('up to 3 shown',tpl)
   rules=out['groups'][0]['rules'];self.assertEqual(len(rules),7)
   self.assertEqual(receiver['settings']['maxAlerts'],3)
   self.assertEqual([r['uid'] for r in rules if r['isPaused']],['pf-resource-filesystem-space','pf-resource-network'])
   self.assertEqual(run({**v,'platform_alerts_enable_host_filesystem':True,'platform_alerts_enable_physical_network':True}).returncode,0)
   self.assertFalse(any(r['isPaused'] for r in yaml.safe_load((p/'out/alerting.yaml').read_text())['groups'][0]['rules']))
   for rule in rules:
    self.assertEqual(rule['notification_settings']['receiver'],'platform-resource-ntfy');self.assertEqual(rule['notification_settings']['repeat_interval'],'6h');self.assertEqual(rule['noDataState'],'NoData');self.assertEqual(rule['execErrState'],'Error');self.assertNotIn('__NETWORK_DEVICE_REGEX__',rule['data'][0]['model']['expr']);self.assertNotIn('__DISK_DEVICE_REGEX__',rule['data'][0]['model']['expr'])
   by={r['uid']:r['data'][0]['model']['expr'] for r in rules}
   self.assertIn('MemAvailable',by['pf-resource-memory']);self.assertIn('persistentvolumeclaim',by['pf-resource-pvc-space']);self.assertIn('> bool 10',by['pf-resource-disk-latency']);self.assertNotIn('io_time_seconds',by['pf-resource-disk-latency'])
   self.assertEqual((p/'out/alerting.yaml').stat().st_mode&0o777,0o600)
   for change in ({'platform_alerts_topic':'tenant-alerts'},{'platform_alerts_url':'http://ntfy.test/'},{'platform_alerts_network_device_regex':'foo"} or vector(1)'}, {'platform_alerts_runbook_url':'javascript:alert(1)'}):self.assertNotEqual(run({**v,**change}).returncode,0)
 def test_inert(self):
  for args in ([],['--check','-e','platform_alerts_render=true']):
   r=subprocess.run(['ansible-playbook','-i','localhost,',str(M/'render.yaml'),*args],capture_output=True,text=True,timeout=20);self.assertEqual(r.returncode,0,r.stdout+r.stderr)
if __name__=='__main__':unittest.main()
