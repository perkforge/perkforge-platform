package portalcel

import (
	"encoding/json"
	"os"
	"os/exec"
	"strings"
	"testing"

	admissionv1 "k8s.io/api/admissionregistration/v1"
	"k8s.io/apimachinery/pkg/api/meta"
	"k8s.io/apimachinery/pkg/runtime/schema"
	"k8s.io/apiserver/pkg/admission/plugin/policy/validating"
	"k8s.io/apiserver/pkg/cel/openapi/resolver"
	"k8s.io/kube-openapi/pkg/validation/spec"
)

type fixtureSchemas map[string]spec.Schema

func (f fixtureSchemas) ResolveSchema(gvk schema.GroupVersionKind) (*spec.Schema, error) {
	group := gvk.Group
	if group == "" {
		group = "core"
	}
	name := "io.k8s.api." + group + "." + gvk.Version + "." + gvk.Kind
	return resolver.PopulateRefs(func(ref string) (*spec.Schema, bool) {
		s, ok := f[strings.TrimPrefix(ref, "#/definitions/")]
		return &s, ok
	}, name)
}

// Use the API server's schema-aware checker, in addition to dynamic mutation tests.
func TestPoliciesWithKubernetesSchemaTypeChecker(t *testing.T) {
	data, err := os.ReadFile("../fixtures/portal/schemas/workload-types-1.36.5.json")
	if err != nil {
		t.Fatal(err)
	}
	var source struct {
		Definitions fixtureSchemas `json:"definitions"`
	}
	if err = json.Unmarshal(data, &source); err != nil {
		t.Fatal(err)
	}
	mapper := meta.NewDefaultRESTMapper([]schema.GroupVersion{{Group: "", Version: "v1"}, {Group: "apps", Version: "v1"}})
	for _, kind := range []string{"Pod", "Service", "Secret"} {
		mapper.Add(schema.GroupVersionKind{Group: "", Version: "v1", Kind: kind}, meta.RESTScopeNamespace)
	}
	for _, kind := range []string{"Deployment", "ReplicaSet"} {
		mapper.Add(schema.GroupVersionKind{Group: "apps", Version: "v1", Kind: kind}, meta.RESTScopeNamespace)
	}
	checker := validating.TypeChecker{SchemaResolver: source.Definitions, RestMapper: mapper}
	out, err := exec.Command("python3", "-c", "import sys,json;sys.path.insert(0,'..');from portal_fleet_fixture import render;print(json.dumps([o for o in render() if o['kind']=='ValidatingAdmissionPolicy']))").Output()
	if err != nil {
		t.Fatal(err)
	}
	var policies []admissionv1.ValidatingAdmissionPolicy
	if err = json.Unmarshal(out, &policies); err != nil {
		t.Fatal(err)
	}
	if len(policies) != 4 {
		t.Fatalf("expected four policies, got %d", len(policies))
	}
	for _, policy := range policies {
		t.Run(policy.Name, func(t *testing.T) {
			if warnings := checker.Check(&policy); len(warnings) > 0 {
				t.Fatalf("API-server type warnings: %+v", warnings)
			}
		})
	}
}
