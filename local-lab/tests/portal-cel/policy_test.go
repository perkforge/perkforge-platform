package portalcel

import (
	"context"
	"encoding/json"
	"os/exec"
	"testing"

	"github.com/google/cel-go/cel"
	admissionv1 "k8s.io/api/admission/v1"
	"k8s.io/apimachinery/pkg/util/version"
	admissioncel "k8s.io/apiserver/pkg/admission/plugin/cel"
	"k8s.io/apiserver/pkg/cel/environment"
)

type expression string

func (e expression) GetExpression() string    { return string(e) }
func (e expression) ReturnTypes() []*cel.Type { return []*cel.Type{cel.BoolType} }

type scenario struct {
	Name        string         `json:"name"`
	Expressions []string       `json:"expressions"`
	OldObject   map[string]any `json:"oldObject"`
	Object      map[string]any `json:"object"`
	Request     map[string]any `json:"request"`
	Allowed     bool           `json:"allowed"`
}

func TestGeneratedPoliciesWithKubernetesCEL(t *testing.T) {
	out, err := exec.Command("python3", "../portal_admission_cases.py").Output()
	if err != nil {
		if e, ok := err.(*exec.ExitError); ok {
			t.Fatalf("fixture generation: %s", e.Stderr)
		}
		t.Fatal(err)
	}
	var cases []scenario
	if err = json.Unmarshal(out, &cases); err != nil {
		t.Fatal(err)
	}
	compiler := admissioncel.NewCompiler(environment.MustBaseEnvSet(version.MajorMinor(1, 36)))
	programs := map[string]cel.Program{}
	for _, tc := range cases {
		t.Run(tc.Name, func(t *testing.T) {
			// Match API-server omitempty behavior instead of inventing empty request fields.
			rawRequest, err := json.Marshal(tc.Request)
			if err != nil {
				t.Fatal(err)
			}
			var apiRequest admissionv1.AdmissionRequest
			if err = json.Unmarshal(rawRequest, &apiRequest); err != nil {
				t.Fatal(err)
			}
			rawRequest, err = json.Marshal(apiRequest)
			if err != nil {
				t.Fatal(err)
			}
			var runtimeRequest map[string]any
			if err = json.Unmarshal(rawRequest, &runtimeRequest); err != nil {
				t.Fatal(err)
			}
			allowed := true
			for _, source := range tc.Expressions {
				program, found := programs[source]
				if !found {
					result := compiler.CompileCELExpression(expression(source), admissioncel.OptionalVariableDeclarations{}, environment.NewExpressions)
					if result.Error != nil {
						t.Fatalf("Kubernetes admission CEL compile: %v\n%s", result.Error, source)
					}
					program = result.Program
					programs[source] = program
				}
				var object, oldObject any
				if tc.Object != nil {
					object = tc.Object
				}
				if tc.OldObject != nil {
					oldObject = tc.OldObject
				}
				result, _, evalErr := program.ContextEval(context.Background(), map[string]any{"object": object, "oldObject": oldObject, "request": runtimeRequest, "namespaceObject": nil})
				if evalErr != nil || result.Value() != true {
					allowed = false
				}
			}
			if allowed != tc.Allowed {
				t.Fatalf("allowed=%v, want=%v", allowed, tc.Allowed)
			}
		})
	}
}
