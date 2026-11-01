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
 def test_single_manager_no_unconfigured_notification_or_credentials(self):
  objs=self.objects['monitoring'][1];self.assertEqual(sum(x['kind']=='Alertmanager' for x in objs),1)
  secret=next(x for x in objs if x['kind']=='Secret' and 'alertmanager.yaml' in x.get('data',{}));c=yaml.safe_load(base64.b64decode(secret['data']['alertmanager.yaml']))
  self.assertEqual(c['route']['receiver'],'null');self.assertEqual(c['receivers'],[{'name':'null'}]);self.assertEqual(c['route']['group_by'],['alertname','namespace','severity'])
  contract=yaml.safe_load((ROOT/'configuration/observability/notification-contract.yaml').read_text())['notification'];self.assertFalse(contract['enabled']);self.assertFalse(contract['duplicate_direct_grafana_route']);self.assertEqual(contract['adapter'],'UNDECIDED');self.assertTrue(contract['transport']['verify_tls'])
 def test_grafana_is_external_alertmanager_client_not_duplicate_router(self):
  cfg=next(x for x in self.objects['grafana'][1] if x['kind']=='ConfigMap' and 'datasourcesbb.yaml' in x.get('data',{}))['data'];a=next(x for x in yaml.safe_load(cfg['datasourcesbb.yaml'])['datasources'] if x['uid']=='alertmanager');self.assertFalse(a['jsonData']['handleGrafanaManagedAlerts']);self.assertEqual(a['jsonData']['implementation'],'prometheus');self.assertFalse(any('ntfy' in str(x).lower() for _,xs in self.objects.values() for x in xs))

 def test_verifier_defaults_never_probe_or_create_files(self):
  play=ROOT/'configuration/ansible/observability-verify.yaml';doc=yaml.safe_load(play.read_text())[0];self.assertFalse(doc['vars']['observability_verify'])
  with tempfile.TemporaryDirectory() as d:
   p=subprocess.run(['ansible-playbook','-i',str(ROOT/'configuration/ansible/inventory.yaml'),str(play),'--check'],capture_output=True,text=True,env={**os.environ,'ANSIBLE_LOCAL_TEMP':d},timeout=40);self.assertEqual(p.returncode,0,p.stdout+p.stderr);self.assertIn('changed=0',p.stdout)
