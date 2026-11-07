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
import yaml


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


# CNPG chart 0.29.1 config-template hashes, independently tested against the
# integrity-pinned chart and both source roots. Keep the old checksum in the
# normalized spec so existing pre-Harbor evidence remains valid byte-for-byte.
OPERATOR_CONFIG_CHECKSUMS = {
    'gitlab,tenant-home-nextcloud': '9a75f80da2e0bfc23a72060aa606a9e8e370955781a37870e3b1743ebfe7914e',
    'gitlab,tenant-home-nextcloud,harbor': 'c7249aa557a41afa5b02e561126d9f84f9f2b7e0d53a0ce401c3f38a3bf94598',
}


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
    annotations = spec['template'].get('metadata', {}).get('annotations', {})
    require(watched in OPERATOR_CONFIG_CHECKSUMS
            and annotations.get('checksum/config') == OPERATOR_CONFIG_CHECKSUMS[watched],
            'Unexpected operator watch/config checksum pair')
    annotations['checksum/config'] = OPERATOR_CONFIG_CHECKSUMS['gitlab,tenant-home-nextcloud']
    return {'uid': operator['metadata']['uid'], 'spec_sha256_without_watch': digest(spec)}, watched


def healthy_deployment(obj):
    spec, status = obj['spec'], obj.get('status', {})
    desired = spec.get('replicas', 1)
    require(not obj['metadata'].get('deletionTimestamp') and desired == 1, identity(obj) + ' unexpected lifecycle/scale')
    require(status.get('observedGeneration') == obj['metadata']['generation'], identity(obj) + ' is stale')
    require(status.get('replicas') == desired and status.get('updatedReplicas') == desired
            and status.get('readyReplicas') == desired and status.get('availableReplicas') == desired,
            identity(obj) + ' rollout is not complete')


def release_fingerprint(obj, *, stage='snapshot'):
    spec = copy.deepcopy(obj['spec'])
    if identity(obj) == 'HelmRelease/bigbang/bigbang' and stage == 'app':
        expected = [{'kind': 'ConfigMap', 'name': 'values-harbor-' + name, 'valuesKey': 'values.yaml'}
                    for name in ('candidate', 'data', 'application')]
        require(spec['valuesFrom'][-3:] == expected, 'Unexpected Harbor umbrella values additions')
        del spec['valuesFrom'][-3:]
        deletion = spec['postRenderers'][0]['kustomize']['patches'].pop()
        require(deletion['target'] == {'kind': 'Namespace', 'name': 'harbor'}
                and set(deletion) == {'target', 'patch'} and yaml.safe_load(deletion['patch']) ==
                {'$patch': 'delete', 'apiVersion': 'v1', 'kind': 'Namespace', 'metadata': {'name': 'harbor'}},
                'Unexpected Harbor umbrella namespace patch')
    if identity(obj) == 'HelmRelease/bigbang/platform-cnpg':
        expected_watch = 'gitlab,tenant-home-nextcloud' + ('' if stage == 'snapshot' else ',harbor')
        require(spec['values']['config']['data'].pop('WATCH_NAMESPACE') == expected_watch, 'Wrong CNPG Helm watch')
        matched = 0
        for renderer in spec['postRenderers']:
            for patch in renderer['kustomize']['patches']:
                if patch['target'] == {'kind': 'Deployment', 'name': 'platform-cnpg'}:
                    value = yaml.safe_load(patch['patch'])
                    expected = {'apiVersion': 'apps/v1', 'kind': 'Deployment', 'metadata': {'name': 'platform-cnpg', 'namespace': 'cnpg-system'},
                                'spec': {'template': {'spec': {'containers': [{'name': 'manager', 'env': [{'name': 'WATCH_NAMESPACE', 'value': expected_watch}]}]}}}}
                    require(value == expected, 'Unexpected CNPG watch post-renderer change')
                    value['spec']['template']['spec']['containers'][0]['env'][0].pop('value')
                    patch['patch'] = value
                    matched += 1
        require(matched == 1, 'Missing or duplicate CNPG watch post-renderer')
    return digest(spec)


def data_checkpoint(state, before, commit, tag, namespace_uid):
    def record(obj):
        return {'uid': obj['metadata']['uid'], 'spec_sha256': digest(obj['spec'])}
    databases = objects(state['databases'])
    releases = objects(state['releases'])
    claims = objects([p for p in state['claims'] if p['metadata'].get('namespace') == 'harbor'])
    require(len(claims) == 2, 'Capture checkpoint only during the data-only stage')
    return {'format': 1, 'cluster_uid': before['cluster_uid'], 'namespace_uid': namespace_uid,
            'release': tag, 'commit': commit, 'baseline_sha256': digest(before),
            'database': record(databases['Cluster/harbor/harbor-postgres']),
            'valkey': record(releases['HelmRelease/bigbang/harbor-valkey']),
            'claims': {key: record(value) for key, value in claims.items()}}


def verify_checkpoint(state, before, checkpoint, commit, tag, namespace_uid):
    expected_binding = {'format': 1, 'cluster_uid': before['cluster_uid'], 'namespace_uid': namespace_uid,
                        'release': tag, 'commit': commit, 'baseline_sha256': digest(before)}
    require(all(checkpoint.get(k) == v for k, v in expected_binding.items()), 'Wrong data-checkpoint identity/release/baseline')
    require(set(checkpoint['claims']) <= set(objects(state['claims'])) and len(checkpoint['claims']) == 2, 'Missing data checkpoint claims')
    for obj, expected in [(objects(state['databases'])['Cluster/harbor/harbor-postgres'], checkpoint['database']),
                          (objects(state['releases'])['HelmRelease/bigbang/harbor-valkey'], checkpoint['valkey'])] + [
                              (objects(state['claims'])[key], value) for key, value in checkpoint['claims'].items()]:
        require(obj['metadata']['uid'] == expected['uid'] and digest(obj['spec']) == expected['spec_sha256'],
                'Harbor data identity/spec changed after accepted data stage: ' + identity(obj))


def snapshot(state):
    require(not any(o['metadata'].get('namespace') == 'harbor' or o['metadata']['name'] in ('harbor', 'harbor-valkey')
                    for key in ('releases', 'claims', 'databases') for o in state[key]),
            'Capture preservation evidence before Harbor data/app exists')
    result = {'format': 1, 'operator': operator_identity(state['operator'])[0]}
    require(operator_identity(state['operator'])[1] == 'gitlab,tenant-home-nextcloud', 'Unexpected baseline operator watches')
    for kind, changed_field in [('source', 'ref'), ('root', 'path')]:
        healthy(state[kind])
        stable_spec = copy.deepcopy(state[kind]['spec'])
        stable_spec.pop(changed_field)
        result[kind] = {'uid': state[kind]['metadata']['uid'], 'stable_spec_sha256': digest(stable_spec)}
    for group in ('releases', 'claims', 'databases'):
        result[group] = {}
        for key, obj in objects(state[group]).items():
            if group == 'claims':
                require(obj.get('status', {}).get('phase') == 'Bound', key + ' is not Bound')
            else:
                healthy(obj)
            result[group][key] = {'uid': obj['metadata']['uid'], 'spec_sha256': release_fingerprint(obj) if group == 'releases' else digest(obj['spec'])}
    require(result['releases'] and result['claims'] and result['databases'], 'Baseline must include current apps, claims and databases')
    return result


def verify(state, before, mode, commit, tag, namespace_uid, checkpoint=None):
    require(before.get('format') == 1, 'Unsupported preservation evidence')
    for key in ('source', 'root'):
        healthy(state[key])
    for kind, changed_field in [('source', 'ref'), ('root', 'path')]:
        stable_spec = copy.deepcopy(state[kind]['spec'])
        stable_spec.pop(changed_field)
        require(state[kind]['metadata']['uid'] == before[kind]['uid']
                and digest(stable_spec) == before[kind]['stable_spec_sha256'], 'Existing Flux ' + kind + ' changed beyond approved selection')
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
            actual_spec = release_fingerprint(obj, stage=mode) if group == 'releases' else digest(obj['spec'])
            require(actual_spec == expected['spec_sha256'], 'Changed existing ' + key)
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
        require(isinstance(checkpoint, dict), 'Approved data checkpoint required before app acceptance')
        verify_checkpoint(state, before, checkpoint, commit, tag, namespace_uid)
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
    rules = ingress['spec']['rules']
    require(len(rules) == 1 and rules[0]['host'] == 'harbor.perkforge.home.arpa' and 'defaultBackend' not in ingress['spec'], 'Wrong Ingress host/default backend')
    paths = rules[0]['http']['paths']
    require(len(paths) == 5 and {p['path'] for p in paths} == {'/', '/api/', '/service/', '/v2/', '/c/'}, 'Wrong Ingress path set')
    for path in paths:
        require(path['pathType'] == 'Prefix' and path['backend'] == {'service': {'name': 'harbor-portal' if path['path'] == '/' else 'harbor-core', 'port': {'number': 443}}}, 'Wrong Ingress route/backend')
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
    for name in ('kubeconfig', 'context', 'expected-api', 'expected-cluster-uid', 'expected-namespace-uid', 'baseline', 'data-checkpoint', 'commit', 'release'):
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
        require(args.data_checkpoint, 'Data checkpoint path required')
        checkpoint_path = protected(args.data_checkpoint, exists=args.mode == 'app' or Path(args.data_checkpoint).exists())
        require(args.expected_namespace_uid and re.fullmatch(r'[0-9a-f]{40}', args.commit or '')
                and re.fullmatch(r'v\d+\.\d+\.\d+', args.release or ''), 'Exact namespace/release/commit required')
    else:
        require(not baseline.exists(), 'Refuse overwriting preservation evidence')
    prefix = ['kubectl', '--kubeconfig', str(kubeconfig), '--context', args.context, '--request-timeout=20s']
    def call(*command):
        result = subprocess.run(prefix + list(command), capture_output=True, text=True, timeout=25, check=False)
        require(result.returncode == 0, 'Read-only kubectl request failed; output withheld')
        return result.stdout.strip()
    config = json.loads(call('config', 'view', '--minify', '-o', 'json'))
    require(config['current-context'] == args.context and len(config['contexts']) == len(config['clusters']) == 1, 'Unexpected kubeconfig context')
    context, cluster = config['contexts'][0], config['clusters'][0]
    require(context['name'] == args.context and context['context']['cluster'] == cluster['name'], 'Kubeconfig cluster reference mismatch')
    endpoint = cluster['cluster']
    require(endpoint['server'] == args.expected_api, 'API target mismatch')
    require(not endpoint.get('insecure-skip-tls-verify') and not endpoint.get('proxy-url') and not endpoint.get('tls-server-name')
            and bool(endpoint.get('certificate-authority-data') or endpoint.get('certificate-authority')), 'Verified pinned API TLS required without proxy or hostname override')
    require(call('get', 'namespace', 'kube-system', '-o', 'jsonpath={.metadata.uid}') == args.expected_cluster_uid, 'Cluster UID mismatch')
    def get(kind, name=None, namespace=None, all_namespaces=False):
        command = ['get', kind] + ([name] if name else [])
        command += ['-A'] if all_namespaces else (['-n', namespace] if namespace else [])
        return json.loads(call(*command, '-o', 'json'))
    state = {group: get(kind, all_namespaces=True)['items'] for group, kind in
             [('releases', 'helmreleases.helm.toolkit.fluxcd.io'), ('claims', 'persistentvolumeclaims'), ('databases', 'clusters.postgresql.cnpg.io')]}
    state['operator'] = get('deployment', 'platform-cnpg', 'cnpg-system')
    state.update(source=get('gitrepository', 'cluster-config', 'flux-system'), root=get('kustomization', 'cluster-root', 'flux-system'))
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
        state.update(namespace=get('namespace', 'harbor'),
                     deployments=get('deployments', namespace='harbor')['items'], pods=get('pods', namespace='harbor')['items'])
        if args.mode == 'app':
            state.update(transport_crd=get('crd', 'serverstransports.traefik.io'), services=get('services', namespace='harbor')['items'],
                         transports=get('serverstransports.traefik.io', namespace='harbor')['items'], ingress=get('ingress', 'harbor-ingress', 'harbor'))
        checkpoint = json.loads(checkpoint_path.read_text()) if checkpoint_path.exists() else None
        report = verify(state, before, args.mode, args.commit, args.release, args.expected_namespace_uid, checkpoint)
        if args.mode == 'data':
            expected_checkpoint = data_checkpoint(state, before, args.commit, args.release, args.expected_namespace_uid)
            if checkpoint is not None:
                require(checkpoint == expected_checkpoint, 'Refuse replacing different data checkpoint')
            else:
                descriptor = os.open(checkpoint_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                with os.fdopen(descriptor, 'w') as handle:
                    json.dump(expected_checkpoint, handle, sort_keys=True, indent=2)
                    handle.write('\n')
        print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (Refusal, KeyError, TypeError, OSError, json.JSONDecodeError, yaml.YAMLError, subprocess.TimeoutExpired) as exc:
        print('Harbor audit refused: ' + (str(exc) if isinstance(exc, Refusal) else type(exc).__name__), file=sys.stderr)
        sys.exit(1)
