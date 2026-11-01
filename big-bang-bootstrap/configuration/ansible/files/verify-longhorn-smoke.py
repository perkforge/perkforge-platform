"""Read-only verification for the explicitly gated Ansible storage smoke test."""
import json
import os
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


def replica_health(volume, replicas, engines, worker):
    require(volume['spec']['numberOfReplicas'] == 2, 'replica count drift')
    status = volume.get('status', {})
    if status.get('state') != 'attached' or status.get('robustness') != 'healthy' or status.get('currentNodeID') != worker:
        return False
    replicas = [r for r in replicas if r['spec']['volumeName'] == volume['metadata']['name']]
    if len(replicas) != 2 or {r['spec'].get('nodeID') for r in replicas} != WORKERS:
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
        require(source['spec']['url'] == 'https://github.com/perkforge/perkforge-platform.git' and source['spec']['ref'] == {'tag': 'v0.11.3'} and not source['spec'].get('suspend', False)
                and ready(source) and source['status']['artifact']['revision'] == REVISION, 'source not exact Ready release')
        root = read(['-n', 'flux-system', 'get', 'kustomization', 'cluster-root'], 'root-before')
        require(ready(root) and not root['spec'].get('suspend', False) and root['status']['lastAppliedRevision'] == REVISION, 'root not exact Ready release')
        for name in ['bigbang', 'longhorn']:
            require(ready(read(['-n', 'bigbang', 'get', 'helmrelease', name], name + '-before')), name + ' is not Ready')
        sc = read(['get', 'storageclass', 'longhorn'], 'class-before')
        require(sc['provisioner'] == 'driver.longhorn.io' and sc['reclaimPolicy'] == 'Retain'
                and sc['volumeBindingMode'] == 'WaitForFirstConsumer' and sc['parameters']['numberOfReplicas'] == '2'
                and sc['parameters'].get('dataEngine') == 'v1'
                and sc['metadata'].get('annotations', {}).get('storageclass.kubernetes.io/is-default-class', 'false') != 'true', 'unexpected storage class')
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
            disks = node['status']['diskStatus']; require(len(disks) == 1, 'unexpected disk layout')
            for name, disk in disks.items():
                require(node['spec']['disks'][name]['allowScheduling'] and all(any(c['type'] == t and c['status'] == 'True' for c in disk['conditions']) for t in ['Ready', 'Schedulable']), 'disk unhealthy')
                require(disk['storageMaximum'] - node['spec']['disks'][name]['storageReserved'] - disk['storageScheduled'] >= 1073741824
                        and disk['storageAvailable'] - 1073741824 > disk['storageMaximum'] * .25, 'insufficient capacity')
        print('PASS: exact release/target, namespace absent, retained two-replica class and both worker disks ready')
    elif mode == 'health':
        handle, worker = extra
        volume = read(['-n', 'longhorn-system', 'get', 'volumes.longhorn.io', handle], 'volume-current')
        replicas = read(['-n', 'longhorn-system', 'get', 'replicas.longhorn.io', '-l', 'longhornvolume=' + handle], 'replicas-current')['items']
        engines = read(['-n', 'longhorn-system', 'get', 'engines.longhorn.io', '-l', 'longhornvolume=' + handle], 'engines-current')['items']
        if not replica_health(volume, replicas, engines, worker):
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
