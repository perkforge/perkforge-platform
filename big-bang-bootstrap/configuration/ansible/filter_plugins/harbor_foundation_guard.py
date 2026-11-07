"""Pure exact-owned Harbor foundation comparison. No generation or API access."""
def matches(actual, desired):
    if desired.get('kind') not in {'Namespace', 'ServiceAccount', 'Role', 'RoleBinding'}:
        return False
    if actual.get('kind') != desired['kind'] or actual.get('apiVersion') != desired['apiVersion']:
        return False
    found, wanted = actual.get('metadata', {}), desired['metadata']
    if found.get('name') != wanted['name'] or found.get('namespace', '') != wanted.get('namespace', ''):
        return False
    if found.get('deletionTimestamp') or actual.get('status', {}).get('phase') == 'Terminating':
        return False
    owner = wanted.get('labels', {}).get('perkforge.io/owner')
    if owner not in {'harbor-foundation-v1', 'harbor-data-foundation-v1'}:
        return False
    if any(found.get('labels', {}).get(k) != v for k, v in wanted.get('labels', {}).items()):
        return False
    if actual.get('rules', []) != desired.get('rules', []) or actual.get('roleRef', {}) != desired.get('roleRef', {}):
        return False
    def subjects(obj):
        return [{**subject, 'apiGroup': subject.get('apiGroup', '')} for subject in obj.get('subjects', [])]
    if subjects(actual) != subjects(desired):
        return False
    if desired['kind'] == 'ServiceAccount':
        if actual.get('automountServiceAccountToken') is not False:
            return False
        if actual.get('secrets') or actual.get('imagePullSecrets'):
            return False
    return True


class FilterModule:
    def filters(self):
        return {'harbor_foundation_matches': matches}
