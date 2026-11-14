"""Offline native alerting contracts; synthetic credentials, no APIs or notifications."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
import yaml

ROOT = Path(__file__).resolve().parents[3]
MODULE = ROOT / 'big-bang-bootstrap/configuration/observability/ntfy-routing'

class GrafanaNtfyRouting(unittest.TestCase):
    def test_native_render_is_scoped_and_preserves_global_policy(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp); token=path/'publisher';token.write_text('tk_synthetic_only');token.chmod(0o600)
            ca=path/'ca.crt';ca.write_text('synthetic-public-ca\n')
            values={'grafana_ntfy_render':True,'grafana_ntfy_context':'portal',
                'grafana_ntfy_deployment':'portal','grafana_ntfy_namespace':'tenant-portal','grafana_ntfy_monitoring_namespace':'monitoring',
                'grafana_ntfy_topic':'tenant-portal-alerts','grafana_ntfy_url':'https://notify.example.test/',
                'grafana_ntfy_bao_server':'https://bao.example.test','grafana_ntfy_record':'local/ntfy/grafana-alerts',
                'grafana_ntfy_token_file':str(token),'grafana_ntfy_ca_file':str(ca),
                'grafana_ntfy_ca_sha256':hashlib.sha256(ca.read_bytes()).hexdigest(),
                'grafana_ntfy_output_dir':str(path/'rendered')}
            def run(inputs):
                return subprocess.run(['ansible-playbook','-i','localhost,',str(MODULE/'render.yaml'),'-e',json.dumps(inputs)],capture_output=True,text=True,timeout=30)
            result=run(values);self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            self.assertNotIn('tk_synthetic_only',result.stdout+result.stderr)
            config=yaml.safe_load((path/'rendered/alerting.yaml').read_text())
            self.assertNotIn('policies',config)
            receiver=config['contactPoints'][0]['receivers'][0]
            self.assertFalse(receiver['disableResolveMessage'])
            self.assertFalse(receiver['settings']['tlsConfig']['insecureSkipVerify'])
            self.assertEqual(receiver['settings']['authorization_credentials'],'tk_synthetic_only')
            self.assertIn('"topic":"tenant-portal-alerts"',receiver['settings']['payload']['template'])
            self.assertNotIn('.Labels',receiver['settings']['payload']['template'])
            rules=config['groups'][0]['rules'];self.assertEqual(len(rules),2)
            for rule in rules:
                self.assertEqual(rule['notification_settings'],{'receiver':'context-portal-ntfy','group_by':['context','namespace','alertname'],'group_wait':'30s','group_interval':'5m','repeat_interval':'4h'})
                self.assertFalse(rule['isPaused'])
                self.assertEqual(rule['execErrState'],'KeepLast')
                self.assertIn('namespace="tenant-portal"',rule['data'][0]['model']['expr'])
                self.assertNotIn('=~',rule['data'][0]['model']['expr'])
            self.assertIn('absent(',rules[0]['data'][0]['model']['expr'])
            self.assertIn('deployment="portal"',rules[0]['data'][0]['model']['expr'])
            self.assertNotIn('vector(0)',rules[0]['data'][0]['model']['expr'])
            docs=list(yaml.safe_load_all((path/'rendered/consumers.yaml').read_text()))
            role=next(x for x in docs if x['kind']=='Role')
            self.assertEqual(role['rules'],[{'apiGroups':[''],'resources':['serviceaccounts/token'],'resourceNames':['eso-grafana-alerts'],'verbs':['create']}])
            mount=yaml.safe_load((path/'rendered/values.yaml').read_text())['grafana']['values']['upstream']
            self.assertEqual(set(mount),{'extraSecretMounts'})
            self.assertEqual((path/'rendered/alerting.yaml').stat().st_mode & 0o777,0o600)
            for change in ({'grafana_ntfy_topic':'*'},{'grafana_ntfy_url':'http://notify.example.test/'},{'grafana_ntfy_namespace':'tenant-.*'}):
                rejected=run({**values,**change});self.assertNotEqual(rejected.returncode,0)

    def test_default_and_check_are_inert(self):
        for name,flag in [('render.yaml','grafana_ntfy_render'),('activate.yaml','grafana_ntfy_activate')]:
            for args in ([],['--check','-e',flag+'=true']):
                result=subprocess.run(['ansible-playbook','-i','localhost,',str(MODULE/name),*args],capture_output=True,text=True,timeout=20)
                self.assertEqual(result.returncode,0,result.stdout+result.stderr)

if __name__ == '__main__':unittest.main()
