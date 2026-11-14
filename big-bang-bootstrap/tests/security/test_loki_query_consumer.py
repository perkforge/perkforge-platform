"""Offline additive Grafana Loki consumer, exact approved network scope."""
from pathlib import Path
import tempfile,subprocess,unittest,yaml
ROOT=Path(__file__).resolve().parents[2]
class LokiConsumer(unittest.TestCase):
 def test_opt_in_preserves_prometheus_and_existing_egress(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);inputs={'consumer_render_enabled':True,'gateway_namespace':'tenant-observability','gateway_service_host':'tenant-query-gateway.tenant-observability.svc','grafana_required_endpoints':[{'cidr':'192.0.2.1/32','port':443,'purpose':'identity'}]}
   def run(enabled):
    inputs.update(consumer_output_dir=d+('/on' if enabled else '/off'),grafana_loki_enabled=enabled,grafana_loki_gateway_host='logging-loki-gateway.logging.svc.cluster.local');(p/'inputs.yaml').write_text(yaml.safe_dump(inputs));subprocess.run(['ansible-playbook','-i','localhost,',str(ROOT/'configuration/observability/tenant-query/render-consumer.yaml'),'-e','@'+str(p/'inputs.yaml')],check=True,capture_output=True);q=Path(inputs['consumer_output_dir']);return yaml.safe_load((q/'grafana-consumer.yaml').read_text()),yaml.safe_load((q/'grafana-egress.yaml').read_text())
   a,ae=run(False);b,be=run(True)
   self.assertEqual(a['upstream']['datasources']['datasourcesbb.yaml'],b['upstream']['datasources']['datasourcesbb.yaml'])
   self.assertEqual(a['upstream']['envFromSecrets'],b['upstream']['envFromSecrets'])
   self.assertEqual(ae['spec']['egress'],be['spec']['egress'][:-1]);self.assertEqual(ae['spec']['podSelector'],be['spec']['podSelector'])
   self.assertEqual(be['spec']['egress'][-1],{'to':[{'namespaceSelector':{'matchLabels':{'kubernetes.io/metadata.name':'logging'}},'podSelector':{'matchLabels':{'app.kubernetes.io/component':'gateway','app.kubernetes.io/instance':'logging-loki'}}}],'ports':[{'protocol':'TCP','port':8080}]})
   self.assertEqual(b['upstream']['grafana.ini']['security']['data_source_proxy_whitelist'],a['upstream']['grafana.ini']['security']['data_source_proxy_whitelist']+' logging-loki-gateway.logging.svc.cluster.local:443')
   ds=b['upstream']['datasources']['datasources-loki.yaml']['datasources'][0];self.assertEqual(ds['url'],'https://logging-loki-gateway.logging.svc.cluster.local:443');self.assertFalse(ds['jsonData']['tlsSkipVerify']);self.assertEqual(ds['secureJsonData']['basicAuthPassword'],'$LOKI_PASSWORD');self.assertNotIn('datasources-loki.yaml',a['upstream']['datasources'])
