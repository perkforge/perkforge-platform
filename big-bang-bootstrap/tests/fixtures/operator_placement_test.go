// Copied into the integrity-pinned v0.94.0 operator source for offline tests.
package prometheus

import (
	"encoding/json"
	monitoringv1 "github.com/prometheus-operator/prometheus-operator/pkg/apis/monitoring/v1"
	"github.com/prometheus-operator/prometheus-operator/pkg/operator"
	"k8s.io/apimachinery/pkg/labels"
	"os"
	"reflect"
	"testing"
)

func TestPerkforgeWorkerPlacement(t *testing.T) {
	raw, err := os.ReadFile(os.Getenv("PLACEMENT_PROMETHEUS_JSON"))
	if err != nil {
		t.Fatal(err)
	}
	var p monitoringv1.Prometheus
	if err = json.Unmarshal(raw, &p); err != nil {
		t.Fatal(err)
	}
	// Match the chart's zero-request/limit reloader, not upstream test defaults.
	defaultTestConfig.ReloaderConfig = operator.DefaultConfig("0", "0").ReloaderConfig
	current, err := makeStatefulSetFromPrometheus(p)
	if err != nil {
		t.Fatal(err)
	}
	if !reflect.DeepEqual(current.Spec.Template.Spec.NodeSelector, map[string]string{"storage.perkforge.io/worker": "true"}) {
		t.Fatal("worker selector not propagated")
	}
	selector := labels.SelectorFromSet(current.Spec.Template.Spec.NodeSelector)
	for _, worker := range []labels.Set{{"storage.perkforge.io/worker": "true"}, {"storage.perkforge.io/worker": "true", "kubernetes.io/hostname": "second-worker"}} {
		if !selector.Matches(worker) {
			t.Fatal("eligible worker rejected")
		}
	}
	if selector.Matches(labels.Set{"node-role.kubernetes.io/control-plane": "true"}) {
		t.Fatal("control plane admitted")
	}
	p.Spec.NodeSelector = nil
	legacy, err := makeStatefulSetFromPrometheus(p)
	if err != nil {
		t.Fatal(err)
	}
	current.Spec.Template.Spec.NodeSelector = nil
	if !reflect.DeepEqual(current, legacy) {
		t.Fatal("generated StatefulSet changed beyond worker selector")
	}
}

func TestPerkforgeRegistryPullReferences(t *testing.T) {
	raw, err := os.ReadFile(os.Getenv("PLACEMENT_PROMETHEUS_JSON"))
	if err != nil {
		t.Fatal(err)
	}
	var p monitoringv1.Prometheus
	if err = json.Unmarshal(raw, &p); err != nil {
		t.Fatal(err)
	}
	if len(p.Spec.ImagePullSecrets) != 1 || p.Spec.ImagePullSecrets[0].Name != "private-registry" {
		t.Fatal("rendered Prometheus lacks existing registry reference")
	}
	defaultTestConfig.ReloaderConfig = operator.DefaultConfig("0", "0").ReloaderConfig
	current, err := makeStatefulSetFromPrometheus(p)
	if err != nil {
		t.Fatal(err)
	}
	refs := current.Spec.Template.Spec.ImagePullSecrets
	if len(refs) != 1 || refs[0].Name != "private-registry" {
		t.Fatal("operator lost registry reference for Prometheus/reloader Pod")
	}
	p.Spec.ImagePullSecrets = nil
	legacy, err := makeStatefulSetFromPrometheus(p)
	if err != nil {
		t.Fatal(err)
	}
	current.Spec.Template.Spec.ImagePullSecrets = nil
	if !reflect.DeepEqual(current, legacy) {
		t.Fatal("generated StatefulSet changed beyond registry reference")
	}
}
