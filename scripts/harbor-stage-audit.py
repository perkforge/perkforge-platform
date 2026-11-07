#!/usr/bin/env python3
"""Read-only Harbor stage/preservation audit. Never deploys, execs or reads Secrets."""
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys


class Refusal(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise Refusal(message)


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def identity(obj):
    meta = obj['metadata']
    return '/'.join((obj['kind'], meta.get('namespace', ''), meta['name']))


def healthy(obj):
    meta, status = obj['metadata'], obj.get('status', {})
    require(not meta.get('deletionTimestamp'), identity(obj) + ' is deleting')
    ready = [c for c in status.get('conditions', []) if c['type'] == 'Ready']
    require(len(ready) == 1 and ready[0]['status'] == 'True', identity(obj) + ' is not Ready')
    observed = ready[0].get('observedGeneration', status.get('observedGeneration'))
    # CNPG Cluster has no top-level observedGeneration in its pinned CRD.
    require((obj['kind'] == 'Cluster' and observed is None) or observed == meta.get('generation'), identity(obj) + ' is stale')
    require(not obj.get('spec', {}).get('suspend', False), identity(obj) + ' is suspended')


def objects(items):
    result = {identity(item): item for item in items}
    require(len(result) == len(items), 'Duplicate object identities')
    return result


def operator_identity(operator):
    healthy_deployment(operator)
    spec = copy.deepcopy(operator['spec'])
    pod = spec['template']['spec']
    require(pod['serviceAccountName'] == 'platform-cnpg', 'Unexpected operator service account')
    managers = [c for c in pod['containers'] if c['name'] == 'manager']
    require(len(pod['containers']) == len(managers) == 1, 'Unexpected operator containers')
    watch = [e for e in managers[0]['env'] if e['name'] == 'WATCH_NAMESPACE']
    require(len(watch) == 1 and 'value' in watch[0], 'Unexpected operator watch configuration')
    watched = watch[0].pop('value')
    return {'uid': operator['metadata']['uid'], 'spec_sha256_without_watch': digest(spec)}, watched


def healthy_deployment(obj):
    spec, status = obj['spec'], obj.get('status', {})
    desired = spec.get('replicas', 1)
    require(not obj['metadata'].get('deletionTimestamp') and desired == 1, identity(obj) + ' unexpected lifecycle/scale')
    require(status.get('observedGeneration') == obj['metadata']['generation'], identity(obj) + ' is stale')
    require(status.get('replicas') == desired and status.get('updatedReplicas') == desired
            and status.get('readyReplicas') == desired and status.get('availableReplicas') == desired,
            identity(obj) + ' rollout is not complete')


def snapshot(state):
    require(not any(o['metadata'].get('namespace') == 'harbor' or o['metadata']['name'] in ('harbor', 'harbor-valkey')
                    for key in ('releases', 'claims', 'databases') for o in state[key]),
            'Capture preservation evidence before Harbor data/app exists')
    result = {'format': 1, 'operator': operator_identity(state['operator'])[0]}
    require(operator_identity(state['operator'])[1] == 'gitlab,tenant-home-nextcloud', 'Unexpected baseline operator watches')
    for group in ('releases', 'claims', 'databases'):
        result[group] = {}
        for key, obj in objects(state[group]).items():
            if group == 'claims':
                require(obj.get('status', {}).get('phase') == 'Bound', key + ' is not Bound')
            else:
                healthy(obj)
            result[group][key] = {'uid': obj['metadata']['uid'], 'spec_sha256': digest(obj['spec'])}
    require(result['releases'] and result['claims'] and result['databases'], 'Baseline must include current apps, claims and databases')
    return result


def verify(state, before, mode, commit, tag, namespace_uid):
    require(before.get('format') == 1, 'Unsupported preservation evidence')
    for key in ('source', 'root'):
        healthy(state[key])
    source, root = state['source'], state['root']
    revision = tag + '@sha1:' + commit
    require(source['spec']['url'] == 'https://github.com/perkforge/perkforge-platform.git', 'Wrong source repository')
    require(source['spec']['ref'] == {'tag': tag}, 'Wrong source release selector')
    require(source['status']['artifact']['revision'] == revision, 'Source artifact is not the exact approved release')
    require(root['spec']['path'] == './big-bang-bootstrap/clusters/local-harbor-' + mode, 'Wrong Harbor stage')
    require(root['spec']['sourceRef'] == {'kind': 'GitRepository', 'name': 'cluster-config'}, 'Wrong root source')
    require(root['spec']['serviceAccountName'] == 'platform-reconciler' and not root['spec']['prune'], 'Wrong root authority/pruning')
    require(root['status']['lastAppliedRevision'] == revision, 'Root has not applied the exact release')
    namespace = state['namespace']
    require(namespace['metadata']['uid'] == namespace_uid and not namespace['metadata'].get('deletionTimestamp')
            and namespace['metadata'].get('labels', {}).get('perkforge.io/owner') == 'harbor-foundation-v1'
            and namespace.get('status', {}).get('phase') == 'Active', 'Wrong Harbor namespace identity/owner/lifecycle')
    operator, watched = operator_identity(state['operator'])
    require(operator == before['operator'] and watched == 'gitlab,tenant-home-nextcloud,harbor',
            'Operator changed beyond the reviewed additive watch')
    for group in ('releases', 'claims', 'databases'):
        current = objects(state[group])
        for key, expected in before[group].items():
            require(key in current, 'Missing existing ' + key)
            obj = current[key]
            require(obj['metadata']['uid'] == expected['uid'], 'Recreated existing ' + key)
            if key not in ('HelmRelease/bigbang/bigbang', 'HelmRelease/bigbang/platform-cnpg'):
                require(digest(obj['spec']) == expected['spec_sha256'], 'Changed existing ' + key)
            if group == 'claims':
                require(obj.get('status', {}).get('phase') == 'Bound' and not obj['metadata'].get('deletionTimestamp'), key + ' is not Bound')
            else:
                healthy(obj)
    releases = objects(state['releases'])
    required = ['HelmRelease/bigbang/harbor-valkey'] + (['HelmRelease/bigbang/harbor'] if mode == 'app' else [])
    for key in required:
        require(key in releases, 'Missing ' + key)
        healthy(releases[key])
    if mode == 'data':
        require('HelmRelease/bigbang/harbor' not in releases, 'App exists during data-only acceptance')
    database = objects(state['databases']).get('Cluster/harbor/harbor-postgres')
    require(database is not None and database['spec']['instances'] == 1, 'Missing or scaled Harbor PostgreSQL')
    healthy(database)
    require(database.get('status', {}).get('readyInstances') == 1, 'Harbor PostgreSQL instance not ready')
    claims = [p for p in state['claims'] if p['metadata'].get('namespace') == 'harbor']
    require(len(claims) == (2 if mode == 'data' else 4), 'Unexpected Harbor PVC count')
    require(all(p.get('status', {}).get('phase') == 'Bound' and not p['metadata'].get('deletionTimestamp') for p in claims), 'Harbor PVC is not Bound')
    deployments = objects(state['deployments'])
    expected_deployments = {'Deployment/harbor/harbor-valkey'}
    if mode == 'app':
        expected_deployments |= {'Deployment/harbor/harbor-' + name for name in ('core', 'jobservice', 'registry', 'portal')}
    require(set(deployments) == expected_deployments, 'Unexpected Harbor deployment set')
    for obj in deployments.values():
        healthy_deployment(obj)
    active = [p for p in state['pods'] if p.get('status', {}).get('phase') != 'Succeeded']
    require(len(active) == (2 if mode == 'data' else 6), 'Unexpected active Harbor Pod count')
    for pod in active:
        require(not pod['metadata'].get('deletionTimestamp') and pod.get('status', {}).get('phase') == 'Running', 'Harbor Pod is not Running')
        ready = [c for c in pod['status'].get('conditions', []) if c['type'] == 'Ready']
        require(len(ready) == 1 and ready[0]['status'] == 'True', 'Harbor Pod is not Ready')
    if mode == 'app':
        verify_transport(state)
    return {'stage': mode, 'release': tag, 'commit': commit, 'preserved_releases': len(before['releases']),
            'preserved_claims': len(before['claims']), 'preserved_databases': len(before['databases']),
            'readiness_only': True, 'tls_login_push_pull_restore_accepted': False}


def verify_transport(state):
    versions = [v for v in state['transport_crd']['spec']['versions'] if v['name'] == 'v1alpha1' and v['served']]
    require(len(versions) == 1, 'Installed Traefik transport version missing')
    properties = versions[0]['schema']['openAPIV3Schema']['properties']['spec']['properties']
    require(properties['serverName']['type'] == 'string' and properties['insecureSkipVerify']['type'] == 'boolean'
            and properties['rootCAs']['items']['properties']['secret']['type'] == 'string', 'Installed transport CA/hostname schema mismatch')
    services, transports = objects(state['services']), objects(state['transports'])
    for component in ('core', 'portal'):
        service = services['Service/harbor/harbor-' + component]
        annotations = service['metadata']['annotations']
        require(annotations['traefik.ingress.kubernetes.io/service.serversscheme'] == 'https'
                and annotations['traefik.ingress.kubernetes.io/service.serverstransport'] == 'harbor-harbor-' + component + '-transport@kubernetescrd', 'Wrong HTTPS backend transport reference')
        require(any(p['port'] == 443 and p['targetPort'] == 8443 for p in service['spec']['ports']), 'Wrong HTTPS backend port')
        spec = transports['ServersTransport/harbor/harbor-' + component + '-transport']['spec']
        require(spec == {'serverName': 'harbor-' + component, 'insecureSkipVerify': False, 'rootCAs': [{'secret': 'harbor-internal-ca'}]}, 'Wrong backend hostname or CA verification')
    ports = services['Service/harbor/harbor-registry']['spec']['ports']
    require(any(p['port'] == p['targetPort'] == 5443 for p in ports)
            and not any(p['port'] == 5000 for p in ports), 'Registry service does not match internal TLS port')
    ingress = state['ingress']
    require(ingress['spec']['ingressClassName'] == 'traefik'
            and ingress['spec']['tls'] == [{'hosts': ['harbor.perkforge.home.arpa'], 'secretName': 'harbor-service-tls'}], 'Wrong external ingress/TLS reference')
    require(ingress['metadata']['annotations']['traefik.ingress.kubernetes.io/router.entrypoints'] == 'websecure'
            and ingress['metadata']['annotations']['traefik.ingress.kubernetes.io/router.tls'] == 'true', 'HTTPS ingress entrypoint is not enforced')


def protected(path, *, exists=True):
    path = Path(path)
    require(path.is_absolute() and path.resolve() == path, 'Use canonical absolute paths without symlinks')
    parent = path.parent.stat()
    require(parent.st_uid == os.getuid() and stat.S_IMODE(parent.st_mode) == 0o700, 'Parent must be owned mode 0700')
    if exists:
        info = path.lstat()
        require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1 and info.st_uid == os.getuid()
                and stat.S_IMODE(info.st_mode) == 0o600, 'Input must be owned regular single-link mode 0600')
    return path


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--verify', action='store_true', help='Explicitly enable read-only cluster contact')
    parser.add_argument('--mode', choices=('snapshot', 'data', 'app'))
    for name in ('kubeconfig', 'context', 'expected-api', 'expected-cluster-uid', 'expected-namespace-uid', 'baseline', 'commit', 'release'):
        parser.add_argument('--' + name)
    args = parser.parse_args(argv)
    if not args.verify:
        print('Disabled: no files read, API contacted or local evidence written.')
        return 0
    require(args.mode and args.context and args.expected_api and args.expected_cluster_uid and args.baseline and args.kubeconfig, 'Explicit target/evidence inputs required')
    require(re.fullmatch(r'https://[A-Za-z0-9.:-]+', args.expected_api), 'HTTPS API required')
    kubeconfig = protected(args.kubeconfig)
    baseline = protected(args.baseline, exists=args.mode != 'snapshot')
    if args.mode != 'snapshot':
        require(args.expected_namespace_uid and re.fullmatch(r'[0-9a-f]{40}', args.commit or '')
                and re.fullmatch(r'v\d+\.\d+\.\d+', args.release or ''), 'Exact namespace/release/commit required')
    else:
        require(not baseline.exists(), 'Refuse overwriting preservation evidence')
    prefix = ['kubectl', '--kubeconfig', str(kubeconfig), '--context', args.context, '--request-timeout=20s']
    def call(*command):
        result = subprocess.run(prefix + list(command), capture_output=True, text=True, timeout=25, check=False)
        require(result.returncode == 0, 'Read-only kubectl request failed; output withheld')
        return result.stdout.strip()
    require(call('config', 'view', '--minify', '-o', 'jsonpath={.clusters[0].cluster.server}') == args.expected_api, 'API target mismatch')
    require(call('get', 'namespace', 'kube-system', '-o', 'jsonpath={.metadata.uid}') == args.expected_cluster_uid, 'Cluster UID mismatch')
    def get(kind, name=None, namespace=None, all_namespaces=False):
        command = ['get', kind] + ([name] if name else [])
        command += ['-A'] if all_namespaces else (['-n', namespace] if namespace else [])
        return json.loads(call(*command, '-o', 'json'))
    state = {group: get(kind, all_namespaces=True)['items'] for group, kind in
             [('releases', 'helmreleases.helm.toolkit.fluxcd.io'), ('claims', 'persistentvolumeclaims'), ('databases', 'clusters.postgresql.cnpg.io')]}
    state['operator'] = get('deployment', 'platform-cnpg', 'cnpg-system')
    if args.mode == 'snapshot':
        result = snapshot(state)
        result['cluster_uid'] = args.expected_cluster_uid
        descriptor = os.open(baseline, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, 'w') as handle:
            json.dump(result, handle, sort_keys=True, indent=2)
            handle.write('\n')
        print('Preservation evidence captured. No cluster changes or Secrets read.')
    else:
        before = json.loads(baseline.read_text())
        require(before['cluster_uid'] == args.expected_cluster_uid, 'Preservation evidence belongs to another cluster')
        state.update(source=get('gitrepository', 'cluster-config', 'flux-system'),
                     root=get('kustomization', 'cluster-root', 'flux-system'), namespace=get('namespace', 'harbor'),
                     deployments=get('deployments', namespace='harbor')['items'], pods=get('pods', namespace='harbor')['items'])
        if args.mode == 'app':
            state.update(transport_crd=get('crd', 'serverstransports.traefik.io'), services=get('services', namespace='harbor')['items'],
                         transports=get('serverstransports.traefik.io', namespace='harbor')['items'], ingress=get('ingress', 'harbor-ingress', 'harbor'))
        print(json.dumps(verify(state, before, args.mode, args.commit, args.release, args.expected_namespace_uid), sort_keys=True))
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (Refusal, KeyError, TypeError, OSError, json.JSONDecodeError, subprocess.TimeoutExpired) as exc:
        print('Harbor audit refused: ' + (str(exc) if isinstance(exc, Refusal) else type(exc).__name__), file=sys.stderr)
        sys.exit(1)
