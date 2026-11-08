"""Pure input/state verification. Ansible/YAML owns all configuration and mutations."""
from decimal import Decimal, InvalidOperation
import ipaddress
import re

OWNER = 'velero-platform-v1'


def quantity(value):
    match = re.fullmatch(r'([0-9]+(?:\.[0-9]+)?)([KMGTPE]i|[kMGTPE]|m)?', str(value))
    if not match:
        raise ValueError('invalid quantity')
    suffix = match[2] or ''
    factors = {'':1, 'm':Decimal('0.001'), 'k':1000, 'M':1000**2, 'G':1000**3,
               'T':1000**4, 'P':1000**5, 'E':1000**6,
               **{x+'i':1024**(i+1) for i,x in enumerate('KMGTPE')}}
    return Decimal(match[1]) * factors[suffix]


def subset(actual, desired):
    if isinstance(desired, dict):
        return isinstance(actual, dict) and all(k in actual and (quantity(actual[k]) == quantity(v) if k == 'storage' and not isinstance(v, (dict,list,bool)) else subset(actual[k], v)) for k, v in desired.items())
    if isinstance(desired, list):
        return isinstance(actual, list) and len(actual) == len(desired) and all(subset(a, b) for a, b in zip(actual, desired))
    return actual == desired


def _owned_matches(actual, desired):
    if actual.get('metadata', {}).get('labels', {}).get('perkforge.io/owner') != OWNER:
        return False
    if desired.get('kind') == 'NetworkPolicy':
        # Kubernetes omits empty deny-rule arrays. Preserve exact policy semantics.
        policy = dict(actual.get('spec', {}))
        for direction in ('ingress', 'egress'):
            if desired.get('spec', {}).get(direction) == []:
                policy.setdefault(direction, [])
        if policy != desired.get('spec'):
            return False
        actual = {**actual, 'spec': policy}
    for key in desired:
        if key != 'metadata' and not subset(actual.get(key), desired[key]):
            return False
    if not subset(actual.get('metadata', {}), desired['metadata']):
        return False
    if 'data' in desired and actual.get('data') != desired['data']:
        return False
    if 'rules' in desired and actual.get('rules') != desired['rules']:
        return False
    return True


def owned_matches(actual, desired):
    try:
        return _owned_matches(actual, desired)
    except (ValueError, TypeError, InvalidOperation):
        return False


def exact_hosts(values):
    try:
        return isinstance(values, list) and 0 < len(values) <= 6 and len(set(values)) == len(values) and all(
            (n.prefixlen == n.max_prefixlen and not (n.is_multicast or n.is_unspecified or n.is_loopback or n.is_link_local))
            for n in [ipaddress.ip_network(x, strict=True) for x in values])
    except (ValueError, TypeError):
        return False


def copied_transfers(operation, transfers, source_pvcs, target_pvcs=None, uploads=None):
    """Reject name/count-only success: exact operation/PVC UIDs and copied repository snapshots."""
    try:
        kind = operation['kind']
        if kind not in ('Backup', 'Restore') or operation['status']['phase'] != 'Completed':
            return False
        if operation['status'].get('errors', 0) or operation['status'].get('warnings', 0):
            return False
        uid = operation['metadata']['uid']
        name = operation['metadata']['name']
        label = 'velero.io/' + kind.lower() + '-uid'
        expected = {(p['metadata']['namespace'], p['metadata']['name']): p for p in source_pvcs}
        if not expected or len(expected) != len(source_pvcs) or len(transfers) != len(expected):
            return False
        seen = set()
        target = {(p['metadata']['namespace'], p['metadata']['name']): p for p in (target_pvcs or [])}
        upload_by_pvc = {(x['spec']['sourceNamespace'], x['spec']['sourcePVC']): x for x in (uploads or [])}
        for transfer in transfers:
            meta, spec, status = transfer['metadata'], transfer['spec'], transfer['status']
            if meta['namespace'] != 'velero' or meta['labels'].get(label) != uid:
                return False
            owners = [x for x in meta['ownerReferences'] if x['uid'] == uid and x['name'] == name and x['kind'] == kind and x['apiVersion'] == 'velero.io/v1']
            if len(owners) != 1 or status['phase'] != 'Completed' or spec.get('datamover', '') not in ('', 'velero'):
                return False
            progress = status['progress']
            if progress['bytesDone'] <= 0 or progress['bytesDone'] != progress['totalBytes']:
                return False
            if kind == 'Backup':
                key = (spec['sourceNamespace'], spec['sourcePVC'])
                pvc = expected[key]
                if meta['labels'].get('velero.io/pvc-uid') != pvc['metadata']['uid'] or not status.get('snapshotID'):
                    return False
                if spec['snapshotType'] != 'CSI' or spec['csiSnapshot']['driver'] != 'driver.longhorn.io':
                    return False
            else:
                volume = spec['targetVolume']
                key = (spec['sourceNamespace'], volume['pvc'])
                pvc = expected[key]
                restored = target[(volume['namespace'], volume['pvc'])]
                if restored['metadata']['uid'] == pvc['metadata']['uid'] or restored['spec']['volumeName'] == pvc['spec']['volumeName']:
                    return False
                #1.18.4 leaves targetVolume.pv empty; resolve the exact new PVC binding instead.
                if not restored['spec']['volumeName'] or restored['status']['phase'] != 'Bound':
                    return False
                if spec['snapshotID'] != upload_by_pvc[key]['status']['snapshotID']:
                    return False
                if volume['namespace'] != operation['spec']['namespaceMapping'][key[0]]:
                    return False
            if key in seen or spec['backupStorageLocation'] != 'local':
                return False
            seen.add(key)
        return seen == set(expected) and (kind == 'Backup' or len(target) == len(expected))
    except (KeyError, TypeError, ValueError):
        return False


class FilterModule:
    def filters(self):
        return {'velero_owned_matches': owned_matches, 'velero_exact_hosts': exact_hosts,
                'velero_copied_transfers': copied_transfers}
