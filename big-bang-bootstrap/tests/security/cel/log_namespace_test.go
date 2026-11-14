package portalcel

import (
 "context"
 "encoding/json"
 "os"
 "os/exec"
 "testing"
 "k8s.io/apimachinery/pkg/util/version"
 admissioncel "k8s.io/apiserver/pkg/admission/plugin/cel"
 "k8s.io/apiserver/pkg/cel/environment"
)

// Actual Kubernetes admission CEL compiler/evaluator, no server or policy writes.
func TestLogNamespaceGuard(t *testing.T) {
 script := os.Getenv("LOG_NAMESPACE_CASE_SCRIPT")
 if script == "" { t.Skip("set LOG_NAMESPACE_CASE_SCRIPT for explicit offline render") }
 raw, err := exec.Command("python3", script).CombinedOutput()
 if err != nil { t.Fatalf("fixture: %v %s", err,raw) }
 var fixture struct {
  Expression string `json:"expression"`
  Cases []struct {
   Name string `json:"name"`
   Operation string `json:"operation"`
   Object map[string]any `json:"object"`
   OldObject map[string]any `json:"oldObject"`
   Allowed bool `json:"allowed"`
  } `json:"cases"`
 }
 if err=json.Unmarshal(raw,&fixture);err!=nil {t.Fatal(err)}
 if len(fixture.Cases)<11 {t.Fatal("missing lifecycle mutations")}
 compiler:=admissioncel.NewCompiler(environment.MustBaseEnvSet(version.MajorMinor(1,36)))
 compiled:=compiler.CompileCELExpression(fluxExpression{source:fixture.Expression},admissioncel.OptionalVariableDeclarations{},environment.NewExpressions)
 if compiled.Error!=nil {t.Fatal(compiled.Error)}
 for _,tc:=range fixture.Cases {t.Run(tc.Name,func(t *testing.T){
  var object,old any
  if tc.Object!=nil {object=tc.Object};if tc.OldObject!=nil {old=tc.OldObject}
  value,_,err:=compiled.Program.ContextEval(context.Background(),map[string]any{"object":object,"oldObject":old,"request":map[string]any{"operation":tc.Operation},"namespaceObject":nil})
  allowed:=err==nil && value.Value()==true
  if allowed!=tc.Allowed {t.Fatalf("allowed %v want %v, CEL error %v",allowed,tc.Allowed,err)}
 })}
}
