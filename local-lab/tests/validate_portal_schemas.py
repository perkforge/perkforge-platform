#!/usr/bin/env python3
"""Validate generated native/Fleet objects against pinned upstream offline schemas."""
import json
from pathlib import Path
from jsonschema import Draft4Validator
import yaml
ROOT = Path(__file__).resolve().parents[2]
DIRECTORY = ROOT/'local-lab/tests/fixtures/portal/schemas'
native=json.loads((DIRECTORY/'kubernetes-1.36.5.json').read_text())
fleet=json.loads((DIRECTORY/'fleet-0.16.0.json').read_text())
def normalize(schema):
    # Kubernetes OpenAPI v2's IntOrString format is a union, not plain string.
    if isinstance(schema,dict):
        if schema.get('format')=='int-or-string' or schema.get('x-kubernetes-int-or-string'):
            schema['type']=['integer','string']
        if 'properties' in schema and not schema.get('x-kubernetes-preserve-unknown-fields'):
            schema.setdefault('additionalProperties',False)
        for value in schema.values(): normalize(value)
    elif isinstance(schema,list):
        for value in schema: normalize(value)
normalize(native)
normalize(fleet)
from portal_fleet_fixture import provisioned, render
objects=render(provisioned())
count=0
for obj in objects:
    if obj['kind']=='FleetWorkspace':
        continue  # Rancher management API, explicitly outside these schema checks.
    if obj['kind'] in fleet:
        schema=fleet[obj['kind']]
    else:
        prefix={'admissionregistration.k8s.io/v1':'admissionregistration.v1','rbac.authorization.k8s.io/v1':'rbac.v1','networking.k8s.io/v1':'networking.v1','v1':'core.v1'}[obj['apiVersion']]
        schema={'$ref':f'#/definitions/io.k8s.api.{prefix}.{obj["kind"]}',**native}
    Draft4Validator(schema).validate(obj)
    count+=1
print(f'{count} generated Kubernetes/Fleet objects passed pinned upstream schema validation')
