from pathlib import Path
import unittest
import json
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
        prometheus = values["prometheus"]["prometheusSpec"]
        self.assertEqual(prometheus["retention"], "3d")
        self.assertEqual(prometheus["retentionSize"], "1GB")
        self.assertEqual(prometheus["resources"]["requests"]["memory"], "320Mi")
        self.assertEqual(prometheus["resources"]["limits"]["memory"], "768Mi")
        self.assertEqual(prometheus["nodeSelector"]["kubernetes.io/hostname"], "cks-worker")
        self.assertEqual(values["grafana"]["nodeSelector"]["kubernetes.io/hostname"], "cks-worker")
        self.assertEqual(values["kube-state-metrics"]["nodeSelector"]["kubernetes.io/hostname"],
                         "cks-worker")
        self.assertEqual(values["prometheusOperator"]["nodeSelector"]["kubernetes.io/hostname"],
                         "cks-worker")
        self.assertEqual(prometheus["storageSpec"]["emptyDir"]["sizeLimit"], "2Gi")

    def test_platform_dashboard_is_operator_only_and_uses_tenant_labels(self):
        dashboard = self.load("local-lab/fleet/bundles/prometheus-grafana/perkforge-platform-dashboard.yaml")
        self.assertEqual(dashboard["kind"], "ConfigMap")
        self.assertEqual(dashboard["metadata"]["namespace"], "monitoring")
        self.assertEqual(dashboard["metadata"]["labels"]["grafana_dashboard"], "1")
        config = json.loads(dashboard["data"]["perkforge-platform-overview.json"])
        self.assertEqual(config["uid"], "perkforge-platform-overview")
        self.assertTrue(any("label_platform_perkforge_io_tenant" in target["expr"]
                            for panel in config["panels"] for target in panel["targets"]))

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
        self.assertEqual(values["nodeSelector"]["kubernetes.io/hostname"], "cks-worker")
        self.assertEqual(values["opencost"]["exporter"]["resources"]["limits"]["memory"], "256Mi")
        self.assertEqual(values["opencost"]["ui"]["resources"]["limits"]["memory"], "64Mi")


if __name__ == "__main__":
    unittest.main()
