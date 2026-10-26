from pathlib import Path
import unittest
import yaml

ROOT = Path(__file__).resolve().parents[2]


class ObservabilityProfileTests(unittest.TestCase):
    def load(self, relative):
        return yaml.safe_load((ROOT / relative).read_text())

    def test_monitoring_chart_is_pinned_small_and_not_exposed(self):
        fleet = self.load("local-lab/fleet/bundles/prometheus-grafana/fleet.yaml")
        values = self.load("local-lab/fleet/bundles/prometheus-grafana/values.yaml")
        self.assertEqual(fleet["helm"]["version"], "92.11.0")
        self.assertFalse(values["grafana"]["ingress"]["enabled"])
        self.assertFalse(values["prometheus"]["ingress"]["enabled"])
        self.assertFalse(values["alertmanager"]["enabled"])
        self.assertEqual(values["prometheus"]["prometheusSpec"]["replicas"], 1)
        self.assertEqual(values["prometheus"]["prometheusSpec"]["retention"], "7d")

    def test_metrics_export_only_approved_tenant_labels(self):
        values = self.load("local-lab/fleet/bundles/prometheus-grafana/values.yaml")
        allowlist = values["kube-state-metrics"]["metricLabelsAllowlist"]
        self.assertEqual(allowlist, [
            "namespaces=[platform.perkforge.io/tenant,platform.perkforge.io/environment,platform.perkforge.io/isolation-tier]"
        ])

    def test_opencost_reuses_prometheus_and_has_no_cloud_or_ingress(self):
        fleet = self.load("local-lab/fleet/bundles/opencost/fleet.yaml")
        values = self.load("local-lab/fleet/bundles/opencost/values.yaml")
        self.assertEqual(fleet["helm"]["version"], "2.5.33")
        self.assertEqual(fleet["dependsOn"][0]["selector"]["matchLabels"]
                         ["local-lab.homelab/component"], "tenant-observability")
        self.assertFalse(values["opencost"]["cloudCost"]["enabled"])
        self.assertFalse(values["opencost"]["exporter"]["apiIngress"]["enabled"])
        self.assertFalse(values["opencost"]["ui"]["ingress"]["enabled"])
        self.assertEqual(values["opencost"]["prometheus"]["internal"]["serviceName"],
                         "kube-prometheus-stack-prometheus")


if __name__ == "__main__":
    unittest.main()
