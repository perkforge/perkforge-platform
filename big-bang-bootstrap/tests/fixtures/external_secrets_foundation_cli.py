#!/usr/bin/env python3
"""Synthetic CLI for real Ansible tests. No network, real credentials or cluster."""
import base64
import copy
import json
import os
from pathlib import Path
import sys

name = Path(sys.argv[0]).name
args = sys.argv[1:]
root = Path(os.environ['ESO_FIXTURE'])
mode = (root / 'mode').read_text().strip()
with (root / 'calls.jsonl').open('a') as log:
    log.write(json.dumps({'tool': name, 'args': args}) + '\n')
if name == 'git':
    if 'rev-parse' in args:
        print(('b' if mode == 'wrong_checkout' else 'a') * 40)
    elif 'status' in args:
        print(' M unreviewed.yaml' if mode == 'dirty' else '')
    else:
        sys.exit(90)
elif name == 'bash':
    assert args[0].endswith('verify-release-ref.sh')
    sys.exit(91 if mode == 'wrong_release' else 0)
elif name == 'gh':
    payload = {'commonAnnotations': {'platform.perkforge.io/cluster': 'local',
               'platform.perkforge.io/environment': 'local', 'platform.perkforge.io/profile': 'il2'}}
    print(base64.b64encode(json.dumps(payload).encode()).decode())
elif name == 'kubectl':
    state_path = root / 'state.json'
    state = json.loads(state_path.read_text())
    if args[0] == 'kustomize':
        print((root / 'foundation.yaml').read_text())
    elif 'get' in args:
        i = args.index('get')
        kind, object_name = args[i + 1:i + 3]
        if kind == 'namespace' and object_name == 'kube-system':
            print('wrong-cluster' if mode == 'wrong_cluster' else 'cluster-fixture')
        else:
            namespace = args[args.index('--namespace') + 1] if '--namespace' in args else ''
            obj = state.get('|'.join([kind, namespace, object_name]))
            if obj is not None:
                obj = copy.deepcopy(obj)
                if '--show-managed-fields=true' not in args:
                    obj['metadata'].pop('managedFields', None)
                print(json.dumps(obj))
    elif 'create' in args:
        obj = json.load(sys.stdin)
        assert not any('force' in a for a in args)
        manager = next(a.split('=', 1)[1] for a in args if a.startswith('--field-manager='))
        meta = obj['metadata']
        object_key = '|'.join([obj['kind'], meta.get('namespace', ''), meta['name']])
        # Refuse test-side updates too: intended procedure creates only absent objects.
        assert object_key not in state
        if mode == 'create_race':
            print('AlreadyExists: concurrent object is not adopted', file=sys.stderr)
            sys.exit(1)
        meta.update({'uid': 'fixture-' + meta['name'], 'resourceVersion': '1',
                     'managedFields': [{'manager': manager, 'operation': 'Update'}]})
        if obj['kind'] == 'CustomResourceDefinition':
            obj['status'] = {'storedVersions': [v['name'] for v in obj['spec']['versions'] if v['storage']]}
            obj['spec']['conversion'] = {'strategy': 'None'}
            obj['spec']['preserveUnknownFields'] = False
            meta['finalizers'] = ['customresourcecleanup.apiextensions.k8s.io']
        if obj['kind'] == 'Namespace':
            obj['spec'] = {'finalizers': ['kubernetes']}
            meta['labels']['kubernetes.io/metadata.name'] = meta['name']
            meta.setdefault('annotations', {}).update({
                'lifecycle.cattle.io/create.namespace-auth': 'true',
                'cattle.io/status': json.dumps({'Conditions': [
                    {'Type': t, 'Status': 'True', 'Message': '',
                     'LastUpdateTime': '2026-11-11T01:13:42Z'}
                    for t in ('ResourceQuotaInit', 'InitialRolesPopulated')]})})
        if mode == 'readback_drift' and obj['kind'] == 'ClusterRole':
            obj['rules'][0]['verbs'].append('delete')
        state[object_key] = obj
        state_path.write_text(json.dumps(state))
        print('created')
    elif 'wait' in args:
        print('condition met')
    else:
        sys.exit(92)
else:
    sys.exit(93)
