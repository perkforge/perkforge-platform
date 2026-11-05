#!/usr/bin/env python3
"""TEST ONLY: isolated CLI stand-in; no subprocesses or network."""
import json, os, sys
from pathlib import Path
p = Path(os.environ['RANCHER_FIXTURE_STATE'])
state = json.loads(p.read_text())
args = sys.argv[1:]
verb = next((x for x in args if x in ('get', 'patch', 'apply', 'delete')), None)
state.setdefault('events', []).append({'tool': 'kubectl', 'verb': verb})
if verb == 'get':
    rest = args[args.index('get') + 1:]
    resource = rest[0]
    if resource == 'namespace':
        print(state.get('uid', 'fixture-cluster'))
    elif resource == 'deployment':
        print(json.dumps(state['deployment']))
    elif resource == 'secret' and rest[1] == 'tls-ca-additional':
        print(json.dumps(state['publicTrust']))
    elif resource == 'authconfigs.management.cattle.io':
        print(json.dumps({'items': state['auth']}))
    elif resource == 'authconfig.management.cattle.io':
        print(json.dumps(next((x for x in state['auth'] if x['metadata']['name'] == rest[1]))))
    elif resource == 'globalroles.management.cattle.io':
        print(json.dumps({'items': [{'metadata': {'name': x}} for x in state.get('roles', ['admin'])]}))
    elif resource == 'globalrolebindings.management.cattle.io':
        bindings=json.loads(json.dumps(state.get('bindings', [])))
        if state.get('serverMetadata'):
            for binding in bindings:
                binding['metadata'].update(uid='binding-uid', resourceVersion='binding-version')
        print(json.dumps({'items': bindings}))
    else:
        raise SystemExit('Unexpected fixture resource')
elif verb == 'patch':
    body = json.load(sys.stdin)
    current = next((x for x in state['auth'] if x['metadata']['name'] == 'genericoidc'))
    assert body['metadata']['resourceVersion'] == current['metadata']['resourceVersion']
    labels = current['metadata'].get('labels', {})
    labels.update(body['metadata'].get('labels', {}))
    current.update({k: v for k, v in body.items() if k != 'metadata'})
    current['metadata']['labels'] = labels
    state['providerWrites'] = state.get('providerWrites', 0) + 1
    print('authconfig patched')
elif verb == 'apply':
    body = json.load(sys.stdin)
    if state.get('failBinding'):
        p.write_text(json.dumps(state))
        raise SystemExit('Synthetic binding interruption')
    assert body['kind'] == 'GlobalRoleBinding'
    before = next((x for x in state.get('bindings', []) if x['metadata']['name'] == body['metadata']['name']), None)
    if before == body:
        print('globalrolebinding unchanged')
    elif before is None:
        state.setdefault('bindings', []).append(body)
        print('globalrolebinding created')
    else:
        raise SystemExit('Unexpected immutable fixture change')
elif verb == 'delete':
    assert '--raw=/apis/management.cattle.io/v3/globalrolebindings/perkforge-sso-v1-platform-admins' in args
    body=json.load(sys.stdin)
    assert body['preconditions']=={'uid':'binding-uid','resourceVersion':'binding-version'}
    state['bindings']=[b for b in state.get('bindings',[]) if b['metadata']['name']!='perkforge-sso-v1-platform-admins']
    print('{}')
else:
    raise SystemExit('Unexpected fixture command')
p.write_text(json.dumps(state))
