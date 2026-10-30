package portalcel

import (
	"context"
	"encoding/json"
	"os"
	"os/exec"
	"testing"

	"github.com/google/cel-go/cel"
	admissionv1 "k8s.io/api/admissionregistration/v1"
	"k8s.io/apimachinery/pkg/api/meta"
	"k8s.io/apimachinery/pkg/runtime/schema"
	"k8s.io/apimachinery/pkg/util/version"
	admissioncel "k8s.io/apiserver/pkg/admission/plugin/cel"
	"k8s.io/apiserver/pkg/admission/plugin/policy/validating"
	"k8s.io/apiserver/pkg/cel/environment"
)

type fluxExpression struct {
	source   string
	variable bool
}

func (e fluxExpression) GetExpression() string { return e.source }
func (e fluxExpression) ReturnTypes() []*cel.Type {
	if e.variable {
		return []*cel.Type{cel.DynType}
	}
	return []*cel.Type{cel.BoolType}
}

// Reuse the existing pinned Kubernetes CEL test dependencies; no controller is installed.
func TestFluxPortalAdmission(t *testing.T) {
	script := os.Getenv("FLUX_PORTAL_CASE_SCRIPT")
	if script == "" {
		t.Skip("proposal check requires explicit external enrollment/app checkouts")
	}
	data, err := exec.Command("python3", script).Output()
	if err != nil {
		if e, ok := err.(*exec.ExitError); ok {
			t.Fatalf("fixtures: %s", e.Stderr)
		}
		t.Fatal(err)
	}
	var fixture struct {
		Policies    []admissionv1.ValidatingAdmissionPolicy `json:"policies"`
		FluxSchemas fixtureSchemas                          `json:"fluxSchemas"`
		Cases       []struct {
			Name    string         `json:"name"`
			Policy  string         `json:"policy"`
			Object  map[string]any `json:"object"`
			Params  any            `json:"params"`
			Allowed bool           `json:"allowed"`
		} `json:"cases"`
	}
	if err = json.Unmarshal(data, &fixture); err != nil {
		t.Fatal(err)
	}
	if len(fixture.Policies) != 4 || len(fixture.Cases) < 30 {
		t.Fatal("missing policy/mutation coverage")
	}
	raw, err := os.ReadFile(os.Getenv("FLUX_PORTAL_OPENAPI"))
	if err != nil {
		t.Fatal(err)
	}
	var schemas struct {
		Definitions fixtureSchemas `json:"definitions"`
	}
	if err = json.Unmarshal(raw, &schemas); err != nil {
		t.Fatal(err)
	}
	for key, value := range fixture.FluxSchemas {
		schemas.Definitions[key] = value
	}
	mapper := meta.NewDefaultRESTMapper([]schema.GroupVersion{{Group: "", Version: "v1"}, {Group: "apps", Version: "v1"}})
	for _, kind := range []string{"Service", "ConfigMap"} {
		mapper.Add(schema.GroupVersionKind{Group: "", Version: "v1", Kind: kind}, meta.RESTScopeNamespace)
	}
	mapper.Add(schema.GroupVersionKind{Group: "apps", Version: "v1", Kind: "Deployment"}, meta.RESTScopeNamespace)
	mapper.Add(schema.GroupVersionKind{Group: "helm.toolkit.fluxcd.io", Version: "v2", Kind: "HelmRelease"}, meta.RESTScopeNamespace)
	mapper.Add(schema.GroupVersionKind{Group: "kustomize.toolkit.fluxcd.io", Version: "v1", Kind: "Kustomization"}, meta.RESTScopeNamespace)
	checker := validating.TypeChecker{SchemaResolver: schemas.Definitions, RestMapper: mapper}
	policies := map[string]admissionv1.ValidatingAdmissionPolicy{}
	for _, p := range fixture.Policies {
		policies[p.Name] = p
		if warnings := checker.Check(&p); len(warnings) > 0 {
			t.Fatalf("%s type warnings: %+v", p.Name, warnings)
		}
		broken := p.DeepCopy()
		broken.Spec.Validations = append(broken.Spec.Validations, admissionv1.Validation{Expression: "object.spec.definitelyNotARealField == true"})
		if len(checker.Check(broken)) == 0 {
			t.Fatalf("%s schema checker did not reject an invalid field", p.Name)
		}
	}
	base := environment.MustBaseEnvSet(version.MajorMinor(1, 36))
	env, err := base.Extend(environment.VersionedOptions{IntroducedVersion: version.MajorMinor(1, 36), EnvOptions: []cel.EnvOption{cel.Variable("variables", cel.DynType)}})
	if err != nil {
		t.Fatal(err)
	}
	compiler := admissioncel.NewCompiler(env)
	for _, tc := range fixture.Cases {
		t.Run(tc.Name, func(t *testing.T) {
			p, ok := policies[tc.Policy]
			if !ok {
				t.Fatal("unknown policy")
			}
			options := admissioncel.OptionalVariableDeclarations{HasParams: p.Spec.ParamKind != nil}
			variables := map[string]any{}
			bindings := map[string]any{"object": tc.Object, "oldObject": nil, "request": map[string]any{"operation": "CREATE"}, "namespaceObject": nil, "params": tc.Params, "variables": variables}
			for _, v := range p.Spec.Variables {
				result := compiler.CompileCELExpression(fluxExpression{source: v.Expression, variable: true}, options, environment.NewExpressions)
				if result.Error != nil {
					t.Fatal(result.Error)
				}
				val, _, e := result.Program.ContextEval(context.Background(), bindings)
				if e != nil {
					t.Fatal(e)
				}
				variables[v.Name] = val
			}
			allowed := true
			for _, v := range p.Spec.Validations {
				result := compiler.CompileCELExpression(fluxExpression{source: v.Expression}, options, environment.NewExpressions)
				if result.Error != nil {
					t.Fatal(result.Error)
				}
				val, _, e := result.Program.ContextEval(context.Background(), bindings)
				if e != nil || val.Value() != true {
					allowed = false
				}
			}
			if allowed != tc.Allowed {
				t.Fatalf("allowed=%v want=%v", allowed, tc.Allowed)
			}
		})
	}
}
