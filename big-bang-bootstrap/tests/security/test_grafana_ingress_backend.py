"""Opt-in translated RKE2 ingress destination; prior rules preserved."""
from pathlib import Path
import tempfile,subprocess,unittest,yaml
ROOT=Path(__file__).resolve().parents[2]
class GrafanaIngressBackend(unittest.TestCase):
 def test_exact_addition_preserves_existing_six_rules_and_consumer(self):
  with tempfile.TemporaryDirectory() as d:
   folder=Path(d); inputs={'consumer_render_enabled':True,'gateway_namespace':'tenant-observability','gateway_service_host':'tenant-query-gateway.tenant-observability.svc','grafana_loki_enabled':True,'grafana_loki_gateway_host':'logging-loki-gateway.logging.svc.cluster.local','grafana_required_endpoints':[{'cidr':'192.0.2.1/32','port':443,'purpose':'identity'},{'cidr':'192.0.2.2/32','port':443,'purpose':'kubernetes-api'},{'cidr':'192.0.2.3/32','port':6443,'purpose':'kubernetes-api'}]}
   def run(enabled):
    values=inputs|{'consumer_output_dir':str(folder/str(enabled)),'grafana_rke2_ingress_backend_enabled':enabled};p=folder/'input.yaml';p.write_text(yaml.safe_dump(values));subprocess.run(['ansible-playbook','-i','localhost,',str(ROOT/'configuration/observability/tenant-query/render-consumer.yaml'),'-e','@'+str(p)],check=True,capture_output=True);out=Path(values['consumer_output_dir']);return yaml.safe_load((out/'grafana-egress.yaml').read_text()),(out/'grafana-consumer.yaml').read_text()
   before,consumer=run(False);after,newconsumer=run(True)
   self.assertEqual(consumer,newconsumer);self.assertEqual(len(before['spec']['egress']),6)
   self.assertEqual(before['spec']['egress'],after['spec']['egress'][:-1]);self.assertEqual(before['spec']['podSelector'],after['spec']['podSelector'])
   self.assertEqual(after['spec']['egress'][-1],{'to':[{'namespaceSelector':{'matchLabels':{'kubernetes.io/metadata.name':'kube-system'}},'podSelector':{'matchLabels':{'app.kubernetes.io/name':'rke2-traefik','app.kubernetes.io/instance':'rke2-traefik-kube-system'}}}],'ports':[{'protocol':'TCP','port':8443}]})
