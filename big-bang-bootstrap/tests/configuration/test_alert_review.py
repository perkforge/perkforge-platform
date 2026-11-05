from pathlib import Path
import unittest,yaml,base64,subprocess,tempfile,os
from fixtures.observability import metrics_render
ROOT=Path(__file__).resolve().parents[2]
class AlertReview(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.objects=metrics_render(ROOT,[ROOT/'configuration/observability/alert-values.yaml'])
 def test_native_rules_preserved_plus_three_reviewed_alerts(self):
  rules=[x for x in self.objects['monitoring'][1] if x['kind']=='PrometheusRule'];self.assertEqual(len(rules),36)
  custom=next(x for x in rules if x['metadata']['name'].endswith('perkforge-lab'));entries=custom['spec']['groups'][0]['rules'];self.assertEqual(len(entries),3)
  self.assertTrue(all(x['labels']['owner']=='platform' and x['for'] in ['5m','10m'] for x in entries))
 def test_single_builtin_manager_and_unarmed_notification(self):
  objs=self.objects['monitoring'][1]
  self.assertFalse(any(x['kind']=='Alertmanager' for x in objs))
  self.assertFalse(any(x['kind']=='Secret' and 'alertmanager.yaml' in x.get('data',{}) for x in objs))
  contract=yaml.safe_load((ROOT/'configuration/observability/notification-contract.yaml').read_text())['notification']
  self.assertEqual(contract['owner'],'grafana-built-in-alertmanager')
  for key in ['enabled','duplicate_direct_grafana_route','prometheus_notification_route','external_alertmanager']:
   self.assertFalse(contract[key],key)
  self.assertTrue(contract['send_resolved']);self.assertTrue(contract['transport']['verify_tls'])
 def test_grafana_has_builtin_alerting_without_external_forwarder(self):
  cfg=next(x for x in self.objects['grafana'][1] if x['kind']=='ConfigMap' and 'datasourcesbb.yaml' in x.get('data',{}))['data']
  self.assertFalse(any(x['type']=='alertmanager' for x in yaml.safe_load(cfg['datasourcesbb.yaml'])['datasources']))
  self.assertIn('[unified_alerting]',cfg['grafana.ini'])
  self.assertFalse(any('ntfy' in str(x).lower() for _,xs in self.objects.values() for x in xs))

 def test_verifier_defaults_never_probe_or_create_files(self):
  play=ROOT/'configuration/ansible/observability-verify.yaml';doc=yaml.safe_load(play.read_text())[0];self.assertFalse(doc['vars']['observability_verify'])
  with tempfile.TemporaryDirectory() as d:
   p=subprocess.run(['ansible-playbook','-i',str(ROOT/'configuration/ansible/inventory.yaml'),str(play),'--check'],capture_output=True,text=True,env={**os.environ,'ANSIBLE_LOCAL_TEMP':d},timeout=40);self.assertEqual(p.returncode,0,p.stdout+p.stderr);self.assertIn('changed=0',p.stdout)
