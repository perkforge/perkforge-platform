"""Pure fail-closed comparison for reviewed ESO foundation. No generation or I/O."""
from copy import deepcopy

OWNER = 'external-secrets-foundation-v1'
CRD_MANAGER = 'perkforge-external-secrets-crds'
HASH_ANNOTATION = 'perkforge.io/external-secrets-crd-source-sha256'
KINDS = {'Namespace', 'ServiceAccount', 'Role', 'RoleBinding', 'ClusterRole',
         'ClusterRoleBinding', 'CustomResourceDefinition'}


def matches(actual, desired):
    if desired.get('kind') not in KINDS or actual.get('kind') != desired['kind']:
        return False
    found, wanted = actual.get('metadata', {}), desired.get('metadata', {})
    if wanted.get('labels', {}).get('perkforge.io/owner') != OWNER:
        return False
    if found.get('labels', {}).get('perkforge.io/owner') != OWNER:
        return False
    if found.get('deletionTimestamp') or actual.get('status', {}).get('phase') == 'Terminating':
        return False
    if found.get('ownerReferences'):
        return False
    expected_finalizers = ['customresourcecleanup.apiextensions.k8s.io'] if desired['kind'] == 'CustomResourceDefinition' else []
    if found.get('finalizers', []) not in ([], expected_finalizers):
        return False
    if desired['kind'] == 'CustomResourceDefinition':
        expected_hash = wanted.get('annotations', {}).get(HASH_ANNOTATION)
        if not expected_hash or found.get('annotations', {}).get(HASH_ANNOTATION) != expected_hash:
            return False
        if not any(f.get('manager') == CRD_MANAGER and f.get('operation') in ('Apply', 'Update')
                   for f in found.get('managedFields', [])):
            return False
        storage = {v['name'] for v in desired['spec']['versions'] if v.get('storage')}
        if set(actual.get('status', {}).get('storedVersions', [])) - storage:
            return False
    return normalize(actual) == normalize(desired)


def normalize(obj):
    result = deepcopy(obj)
    result.pop('status', None)
    meta = result['metadata']
    for name in ('uid', 'resourceVersion', 'generation', 'creationTimestamp',
                 'managedFields', 'selfLink', 'deletionGracePeriodSeconds'):
        meta.pop(name, None)
    for name in ('annotations', 'labels'):
        values = meta.setdefault(name, {})
        if name == 'annotations':
            values.pop('kubectl.kubernetes.io/last-applied-configuration', None)
        if name == 'labels' and result['kind'] == 'Namespace':
            values.pop('kubernetes.io/metadata.name', None)
        if not values:
            meta.pop(name, None)
    if not meta.get('namespace'):
        meta.pop('namespace', None)
    if result['kind'] == 'Namespace' and result.get('spec') == {'finalizers': ['kubernetes']}:
        result.pop('spec')
    if result['kind'] in ('RoleBinding', 'ClusterRoleBinding'):
        for subject in result.get('subjects', []):
            if subject.get('kind') == 'ServiceAccount' and subject.get('apiGroup') == '':
                subject.pop('apiGroup', None)
    if result['kind'] == 'ServiceAccount':
        for field in ('secrets', 'imagePullSecrets'):
            if result.get(field) == []:
                result.pop(field)
    if result['kind'] == 'CustomResourceDefinition':
        if meta.get('finalizers') == ['customresourcecleanup.apiextensions.k8s.io']:
            meta.pop('finalizers')
        if result['spec'].get('conversion') == {'strategy': 'None'}:
            result['spec'].pop('conversion')
        if result['spec'].get('preserveUnknownFields') is False:
            result['spec'].pop('preserveUnknownFields')
    return result


class FilterModule:
    def filters(self):
        return {'external_secrets_foundation_matches': matches}
