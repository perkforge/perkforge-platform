"""Read-only verification for the explicitly gated Ansible storage smoke test."""
import json
import os
import re
from pathlib import Path
import subprocess
import sys

REVISION = 'v0.11.3@sha1:84cc2b7a79fde4b3e72af093ca79a0f1de7fe7f9'
WORKERS = {'worker-1', 'worker-2'}


def require(ok, message):
    if not ok:
        raise ValueError(message)


def ready(obj):
    generation = obj['metadata']['generation']
    return obj.get('status', {}).get('observedGeneration') == generation and any(
        c['type'] == 'Ready' and c['status'] == 'True' and c.get('observedGeneration') == generation
        for c in obj.get('status', {}).get('conditions', []))


def read_policy(path):
    if not path:
        return {'revision': REVISION, 'storage_class': 'longhorn', 'disk_ids': None}
    p = Path(path)
    require(p.is_absolute() and p.resolve() == p and not p.is_symlink() and p.is_file() and
            p.stat().st_uid == os.getuid() and p.stat().st_mode & 0o777 == 0o600,
            'unsafe dedicated smoke policy file')
    require(p.parent.stat().st_uid == os.getuid() and p.parent.stat().st_mode & 0o777 == 0o700,
            'dedicated smoke policy needs a protected owner directory')
    policy = json.loads(p.read_text())
    require(isinstance(policy, dict) and set(policy) == {'revision', 'storage_class', 'disk_ids'}, 'unexpected smoke policy fields')
    require(isinstance(policy['revision'], str) and re.fullmatch(r'v[0-9]+\.[0-9]+\.[0-9]+@sha1:[a-f0-9]{40}', policy['revision']), 'pin an exact published revision')
    require(policy['storage_class'] == 'longhorn-dedicated', 'dedicated smoke requires the two-copy class')
    ids = policy['disk_ids']
    require(isinstance(ids, dict) and set(ids) == WORKERS and all(isinstance(v, str) for v in ids.values()) and len(set(ids.values())) == 2,
            'two distinct worker disk IDs are required')
    require(all(re.fullmatch(r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', v) for v in ids.values()),
            'invalid Longhorn disk IDs')
    return policy


def replica_health(volume, replicas, engines, worker, disk_ids=None):
    require(volume['spec']['numberOfReplicas'] == 2, 'replica count drift')
    status = volume.get('status', {})
    if status.get('state') != 'attached' or status.get('robustness') != 'healthy' or status.get('currentNodeID') != worker:
        return False
    replicas = [r for r in replicas if r['spec']['volumeName'] == volume['metadata']['name']]
    if len(replicas) != 2 or {r['spec'].get('nodeID') for r in replicas} != WORKERS:
        return False
    if disk_ids is not None and any(r['spec'].get('diskID') != disk_ids[r['spec']['nodeID']] for r in replicas):
        return False
    if not all(r['spec'].get('healthyAt') and not r['spec'].get('failedAt')
               and r.get('status', {}).get('currentState') == 'running' for r in replicas):
        return False
    engines = [e for e in engines if e['spec']['volumeName'] == volume['metadata']['name']
               and e.get('status', {}).get('currentState') == 'running']
    return len(engines) == 1 and len(engines[0]['status'].get('replicaModeMap', {})) == 2 and set(engines[0]['status']['replicaModeMap'].values()) == {'RW'}


def main():
    os.umask(0o077)
    mode, kubeconfig, context, uid, namespace, output, *extra = sys.argv[1:]
    policy = read_policy((extra[0] if extra else '') if mode == 'preflight' else (extra[2] if len(extra) > 2 else ''))
    revision = policy['revision']
    out = Path(output)
    require(out.is_absolute() and out.resolve() == out and out.is_dir() and not out.is_symlink() and out.stat().st_mode & 0o777 == 0o700 and out.stat().st_uid == os.getuid(), 'unsafe output directory')
    k = ['kubectl', '--kubeconfig', kubeconfig, '--context', context, '--request-timeout=30s']

    def read(args, name):
        result = subprocess.run(k + args + ['-o', 'json'], text=True, capture_output=True, timeout=35)
        require(result.returncode == 0, 'API read failed: ' + name + '; ' + result.stderr[:200])
        value = json.loads(result.stdout)
        path = out / (name + '.json')
        require(not path.is_symlink(), 'evidence path is a symlink')
        path.write_text(json.dumps(value, indent=2)); path.chmod(0o600)
        return value

    if mode == 'preflight':
        require(not any((out / name).exists() for name in ['foundation.yaml', 'namespace.json', 'initial-pod.yaml', 'summary.txt']), 'test output already contains a run; inspect instead of repeating')
    require(read(['get', 'namespace', 'kube-system'], mode + '-uid')['metadata']['uid'] == uid, 'wrong cluster UID')
    if mode == 'preflight':
        result = subprocess.run(k + ['get', 'namespace', namespace, '--ignore-not-found', '-o', 'name'], text=True, capture_output=True, timeout=35)
        require(result.returncode == 0 and not result.stdout.strip(), 'test namespace already exists or lookup failed')
        source = read(['-n', 'flux-system', 'get', 'gitrepository', 'cluster-config'], 'source-before')
        require(source['spec']['url'] == 'https://github.com/perkforge/perkforge-platform.git' and source['spec']['ref'] == {'tag': revision.split('@', 1)[0]} and not source['spec'].get('suspend', False)
                and ready(source) and source['status']['artifact']['revision'] == revision, 'source not exact Ready release')
        root = read(['-n', 'flux-system', 'get', 'kustomization', 'cluster-root'], 'root-before')
        require(ready(root) and not root['spec'].get('suspend', False) and root['status']['lastAppliedRevision'] == revision, 'root not exact Ready release')
        for name in ['bigbang', 'longhorn']:
            require(ready(read(['-n', 'bigbang', 'get', 'helmrelease', name], name + '-before')), name + ' is not Ready')
        sc = read(['get', 'storageclass', policy['storage_class']], 'class-before')
        require(sc['provisioner'] == 'driver.longhorn.io' and sc['reclaimPolicy'] == 'Retain'
                and sc['volumeBindingMode'] == 'WaitForFirstConsumer' and sc['parameters']['numberOfReplicas'] == '2'
                and sc['parameters'].get('dataEngine') == 'v1'
                and sc['metadata'].get('annotations', {}).get('storageclass.kubernetes.io/is-default-class', 'false') != 'true', 'unexpected storage class')
        if policy['disk_ids'] is not None:
            require(sc['parameters'].get('diskSelector') == 'dedicated-storage' and
                    sc['parameters'].get('replicaSoftAntiAffinity') == 'disabled', 'dedicated class selector/anti-affinity differs')
        nodes = read(['get', 'nodes'], 'nodes-before')['items']
        selected = [n for n in nodes if n['metadata'].get('labels', {}).get('storage.perkforge.io/worker') == 'true']
        require({n['metadata']['name'] for n in selected} == WORKERS, 'worker selection differs')
        for node in selected:
            require(node['metadata']['labels']['kubernetes.io/hostname'] == node['metadata']['name']
                    and any(c['type'] == 'Ready' and c['status'] == 'True' for c in node['status']['conditions']), 'worker not Ready')
        lh_nodes = read(['-n', 'longhorn-system', 'get', 'nodes.longhorn.io'], 'disks-before')['items']
        require({n['metadata']['name'] for n in lh_nodes} == WORKERS, 'Longhorn worker selection differs')
        for node in lh_nodes:
            require(node['spec']['allowScheduling'], 'node unschedulable')
            require(all(any(c['type'] == t and c['status'] == 'True' for c in node['status']['conditions']) for t in ['Ready', 'Schedulable']), 'Longhorn node unhealthy')
            disks = node['status']['diskStatus']
            if policy['disk_ids'] is None:
                require(len(disks) == 1, 'unexpected disk layout')
            else:
                disks = {k: v for k, v in disks.items() if v.get('diskUUID') == policy['disk_ids'][node['metadata']['name']]}
                require(len(disks) == 1, 'planned SSD disk ID missing or duplicated')
            for name, disk in disks.items():
                require(node['spec']['disks'][name]['allowScheduling'] and all(any(c['type'] == t and c['status'] == 'True' for c in disk['conditions']) for t in ['Ready', 'Schedulable']), 'disk unhealthy')
                if policy['disk_ids'] is not None:
                    require('dedicated-storage' in node['spec']['disks'][name]['tags'], 'planned SSD tag missing')
                require(disk['storageMaximum'] - node['spec']['disks'][name]['storageReserved'] - disk['storageScheduled'] >= 1073741824
                        and disk['storageAvailable'] - 1073741824 > disk['storageMaximum'] * .25, 'insufficient capacity')
        print('PASS: exact release/target, namespace absent, retained two-replica class and both worker disks ready')
    elif mode == 'health':
        handle, worker = extra[:2]
        volume = read(['-n', 'longhorn-system', 'get', 'volumes.longhorn.io', handle], 'volume-current')
        replicas = read(['-n', 'longhorn-system', 'get', 'replicas.longhorn.io', '-l', 'longhornvolume=' + handle], 'replicas-current')['items']
        engines = read(['-n', 'longhorn-system', 'get', 'engines.longhorn.io', '-l', 'longhornvolume=' + handle], 'engines-current')['items']
        if not replica_health(volume, replicas, engines, worker, policy['disk_ids']):
            print('WAIT: two healthy distinct-worker replicas with RW engine modes'); return 3
        print('PASS: attached on selected worker; two running healthy replicas on distinct workers, both RW')
    else:
        raise ValueError('unknown verification mode')
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (ValueError, KeyError, subprocess.SubprocessError) as exc:
        print('STOP: ' + str(exc), file=sys.stderr)
        raise SystemExit(1)
