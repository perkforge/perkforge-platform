"""Pure fail-closed comparison for reviewed ESO foundation. No generation or I/O."""
from collections.abc import Mapping
import json

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
    if desired['kind'] == 'Namespace':
        annotations = found.get('annotations', {})
        if annotations.get('lifecycle.cattle.io/create.namespace-auth', 'true') != 'true':
            return False
        if 'cattle.io/status' in annotations:
            try:
                status = json.loads(annotations['cattle.io/status'])
                conditions = status['Conditions']
                if (set(status) != {'Conditions'} or not isinstance(conditions, list)
                        or len(conditions) != 2
                        or {c['Type'] for c in conditions} != {'ResourceQuotaInit', 'InitialRolesPopulated'}
                        or any(c['Status'] != 'True' or
                               set(c) - {'Type', 'Status', 'Message', 'LastUpdateTime'}
                               for c in conditions)):
                    return False
            except (ValueError, TypeError, KeyError):
                return False
    return normalize(actual) == normalize(desired)


def plain_structure(value):
    """Copy public manifest containers without copying Ansible's lazy context."""
    if isinstance(value, Mapping):
        return {key: plain_structure(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [plain_structure(item) for item in value]
    return value


def normalize(obj):
    result = plain_structure(obj)
    result.pop('status', None)
    meta = result['metadata']
    for name in ('uid', 'resourceVersion', 'generation', 'creationTimestamp',
                 'managedFields', 'selfLink', 'deletionGracePeriodSeconds'):
        meta.pop(name, None)
    for name in ('annotations', 'labels'):
        values = meta.setdefault(name, {})
        if name == 'annotations':
            values.pop('kubectl.kubernetes.io/last-applied-configuration', None)
            # Known Rancher namespace initialization bookkeeping only; matches()
            # validates the successful lifecycle shape before normalization.
            if result['kind'] == 'Namespace':
                values.pop('cattle.io/status', None)
                values.pop('lifecycle.cattle.io/create.namespace-auth', None)
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


def comparison_checks(results, allow_absent=False):
    """Keep assertion loop items bounded, rather than logging full CRD schemas."""
    checks = []
    for result in results:
        desired = result['item']
        raw = result.get('stdout', '').strip()
        try:
            accepted = bool(allow_absent) if not raw else matches(json.loads(raw), desired)
        except (ValueError, TypeError, KeyError, AttributeError):
            accepted = False
        checks.append({'resource': desired['kind'] + '/' + desired['metadata']['name'],
                       'matches': accepted})
    return checks


class FilterModule:
    def filters(self):
        return {'external_secrets_foundation_matches': matches,
                'external_secrets_foundation_checks': comparison_checks}
