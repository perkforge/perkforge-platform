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
        return isinstance(actual, dict) and all(k in actual and (quantity(actual[k]) == quantity(v) if k == 'storage' and not isinstance(v, (dict,list)) else subset(actual[k], v)) for k, v in desired.items())
    if isinstance(desired, list):
        return isinstance(actual, list) and len(actual) == len(desired) and all(subset(a, b) for a, b in zip(actual, desired))
    return actual == desired


def _owned_matches(actual, desired):
    if actual.get('metadata', {}).get('labels', {}).get('perkforge.io/owner') != OWNER:
        return False
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


def storage_safe(mount, project, enforcement, quota, node, settings, longhorn_mount, disk_identity, inputs):
    try:
        data = inputs['velero_store_capacity_bytes']
        metadata = inputs['velero_metadata_budget_bytes']
        if type(data) is not int or type(metadata) is not int or min(data, metadata) <= 0:
            return False
        if data + metadata > inputs['velero_quota_bytes']:
            return False
        fs, = mount['filesystems']
        options = fs['options'].split(',')
        if fs['fstype'] != 'xfs' or 'noquota' in options or not {'prjquota', 'pquota'} & set(options):
            return False
        if fs['target'] != inputs['velero_storage_mount'] or fs['uuid'] != inputs['velero_storage_uuid']:
            return False
        lhfs, = longhorn_mount['filesystems']
        if any(lhfs.get(k) != fs.get(k) for k in ('uuid', 'source', 'target', 'fstype')):
            return False
        path = inputs['velero_storage_path']
        if not path.startswith(fs['target'].rstrip('/') + '/'):
            return False
        relative = path[len(fs['target'].rstrip('/')) + 1:]
        # Dedicated direct child, never a replica, metadata, engine or existing disk subtree.
        if not re.fullmatch(r'velero-backups[-a-z0-9]*', relative):
            return False
        for candidate in node['spec']['disks'].values():
            root = candidate['path'].rstrip('/')
            if root != fs['target'].rstrip('/') and (path == root or path.startswith(root + '/')):
                return False
        flags = int(re.search(r'fsxattr.xflags\s*=\s*(0x[0-9a-fA-F]+)', project).group(1), 16)
        project_id = int(re.search(r'fsxattr.projid\s*=\s*(\d+)', project).group(1))
        if project_id != inputs['velero_project_id'] or not flags & 0x200:
            return False
        state = enforcement.split('Project quota state', 1)[1]
        if not re.search(r'Accounting:\s+ON', state) or not re.search(r'Enforcement:\s+ON', state):
            return False
        rows = [line.split() for line in quota.splitlines() if line.lstrip().startswith('#' + str(project_id) + ' ')]
        row, = rows
        hard = int(row[3]) * 1024
        used = int(row[1]) * 1024
        if hard != inputs['velero_quota_bytes'] or used >= hard:
            return False
        disk = node['spec']['disks'][inputs['velero_longhorn_disk_name']]
        if disk['path'] != inputs['velero_longhorn_disk_path'] or not disk['allowScheduling']:
            return False
        if path == disk['path'] or path.startswith(disk['path'].rstrip('/') + '/replicas/'):
            return False
        status = node['status']['diskStatus'][inputs['velero_longhorn_disk_name']]
        if status['diskUUID'] != disk_identity['diskUUID'] or not status['diskUUID']:
            return False
        capacity = min(int(fs['size']), int(status['storageMaximum']))
        if int(status['storageScheduled']) > capacity - int(disk['storageReserved']):
            return False
        config = {x['metadata']['name']: int(x['value']) for x in settings['items']}
        if config['storage-over-provisioning-percentage'] != 100 or config['storage-minimal-available-percentage'] < 25:
            return False
        floor = int(fs['size']) * config['storage-minimal-available-percentage'] // 100
        required = hard + inputs['velero_restore_headroom_bytes'] + floor
        # Reserved capacity includes both backup allocation and original minimum-free safety.
        return disk['storageReserved'] >= required and int(fs['avail']) >= required - used
    except (KeyError, TypeError, ValueError, AttributeError, IndexError):
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


def safe_hooks(hooks, namespace, restore):
    try:
        if not isinstance(hooks, list) or not hooks:
            return False
        for hook in hooks:
            if hook['includedNamespaces'] != [namespace] or not hook.get('labelSelector'):
                return False
            groups = ['postHooks'] if restore else ['pre', 'post']
            for group in groups:
                if not hook.get(group):
                    return False
                for action in hook[group]:
                    execute = action['exec']
                    if execute['onError'] != 'Fail' or not execute['container'] or not execute['command']:
                        return False
                    if not all(isinstance(x, str) and x for x in execute['command']):
                        return False
                    if not execute.get('execTimeout' if restore else 'timeout'):
                        return False
        return True
    except (KeyError, TypeError):
        return False


def selector_specs_match(saved, source, root):
    try:
        for key, current, allowed in [('source', source, {'ref'}), ('root', root, {'path','suspend'})]:
            old = saved[key]
            if any(old['metadata'][k] != current['metadata'][k] for k in ('uid','name','namespace')):
                return False
            if {k:v for k,v in old['spec'].items() if k not in allowed} != {k:v for k,v in current['spec'].items() if k not in allowed}:
                return False
        return True
    except (KeyError, TypeError):
        return False


class FilterModule:
    def filters(self):
        return {'velero_owned_matches': owned_matches, 'velero_exact_hosts': exact_hosts,
                'velero_storage_safe': storage_safe, 'velero_copied_transfers': copied_transfers,
                'velero_safe_hooks': safe_hooks, 'velero_selector_specs_match': selector_specs_match}
