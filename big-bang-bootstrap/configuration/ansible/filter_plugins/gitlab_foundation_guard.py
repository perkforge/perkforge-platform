"""Pure canonical checks of exact owned foundation resources; no generation/API."""
def matches(actual,desired):
 if actual.get('apiVersion')!=desired['apiVersion'] or actual.get('kind')!=desired['kind']:return False
 a=actual.get('metadata',{});d=desired['metadata']
 if a.get('name')!=d['name'] or (a.get('namespace') or '')!=(d.get('namespace') or ''):return False
 if any(a.get('labels',{}).get(k)!=v for k,v in d.get('labels',{}).items()):return False
 if actual.get('rules',[])!=desired.get('rules',[]) or actual.get('roleRef',{})!=desired.get('roleRef',{}):return False
 def subjects(obj):return [{**s,'apiGroup':s.get('apiGroup','')} for s in obj.get('subjects',[])]
 if subjects(actual)!=subjects(desired):return False
 if actual.get('automountServiceAccountToken')!=desired.get('automountServiceAccountToken'):return False
 if desired['kind']=='CustomResourceDefinition':
  a_spec=dict(actual.get('spec',{}));d_spec=dict(desired.get('spec',{}))
  for spec in (a_spec,d_spec):
   if spec.get('conversion')=={'strategy':'None'}:spec.pop('conversion')
   if spec.get('preserveUnknownFields') is False:spec.pop('preserveUnknownFields')
  if a_spec!=d_spec:return False
 elif desired['kind'] not in ('Namespace','ServiceAccount') and actual.get('spec',{})!=desired.get('spec',{}):return False
 return True
class FilterModule:
 def filters(self):return {'gitlab_foundation_matches':matches}
