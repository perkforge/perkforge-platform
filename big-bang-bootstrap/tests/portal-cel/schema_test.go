package portalcel

import (
 "strings"
 "k8s.io/apimachinery/pkg/runtime/schema"
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
