#!/usr/bin/env python3
"""Operator-only delivery of approved portal credentials; no namespace or grant creation."""
import argparse
import base64
import json
import os
from pathlib import Path
import stat
import subprocess

OWNER = 'portal-operator'
LABEL = 'platform.perkforge.io/managed-by'
NAMESPACE = 'tenant-home-portal'


def private_file(path):
    parent = path.parent.lstat()
    if stat.S_ISLNK(parent.st_mode) or parent.st_uid != os.getuid() or stat.S_IMODE(parent.st_mode) != 0o700:
        raise RuntimeError('Credential directory must be owner-only and not a symlink')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(fd) as handle:
        info = os.fstat(handle.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) != 0o600:
            raise RuntimeError('Credential file must be an owner-only regular file')
        return handle.read()


def owned_resource(kind, name, namespace, data, secret_type=None):
    obj = {'apiVersion':'v1', 'kind':kind, 'metadata':{'name':name, 'namespace':namespace,
           'labels':{LABEL:OWNER}}, 'data':data}
    if secret_type:
        obj['type'] = secret_type
    return obj


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--kubectl', type=Path, required=True)
    parser.add_argument('--kubeconfig', type=Path, required=True)
    parser.add_argument('--registry-authfile', type=Path, required=True)
    parser.add_argument('--oidc-secret-file', type=Path, required=True)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    if not args.apply:
        print('Plan only: verify existing controls; deliver issued leaf TLS, public CA, OIDC and pull credentials; remove staged registry file after success.')
        return
    prefix = [str(args.kubectl), '--kubeconfig', str(args.kubeconfig), '--context', 'default', '--request-timeout=20s']
    def call(*command, payload=None):
        result = subprocess.run(prefix + list(command), input=json.dumps(payload) if payload else None,
                                text=True, capture_output=True)
        if result.returncode:
            raise RuntimeError('Kubernetes operation failed; credential-bearing output suppressed')
        return result.stdout
    def get(kind, name, namespace=None):
        flags = ['-n',namespace] if namespace else []
        raw = call('get',kind,name,*flags,'--ignore-not-found','-o','json')
        return json.loads(raw) if raw.strip() else None
    # Require installed controls; do not manufacture a namespace or bypass the staging gate.
    if not get('namespace',NAMESPACE):
        raise RuntimeError('Reviewed portal namespace must exist first')
    for name in ('portal-template-contract','portal-pod-contract','portal-deployer-surface','portal-service-contract'):
        policy = get('validatingadmissionpolicy',name)
        binding = get('validatingadmissionpolicybinding',name)
        if not policy or policy['spec'].get('failurePolicy') != 'Fail' or not binding or binding['spec'].get('validationActions') != ['Deny']:
            raise RuntimeError('Reviewed fail-closed portal admission must exist first')
    registry_text = private_file(args.registry_authfile)
    registry = json.loads(registry_text)
    if set(registry) != {'auths'} or set(registry['auths']) != {'ghcr.io'} or set(registry['auths']['ghcr.io']) != {'auth'}:
        raise RuntimeError('Only the reviewed GHCR credential is accepted')
    oidc = private_file(args.oidc_secret_file).strip()
    if not oidc:
        raise RuntimeError('OIDC credential is empty')
    resources = []
    public_ca = None
    for certificate, namespace, destination in [('keycloak-lan','keycloak','keycloak-tls'),('portal-lan',NAMESPACE,'portal-tls')]:
        cert = get('certificate',certificate,'cattle-system')
        if not cert or not any(c.get('type')=='Ready' and c.get('status')=='True' for c in cert.get('status',{}).get('conditions',[])):
            raise RuntimeError('Reviewed leaf certificate is not Ready')
        source = get('secret',cert['spec']['secretName'],'cattle-system')
        issuer = cert['spec'].get('issuerRef', {})
        if source.get('type') != 'kubernetes.io/tls' or issuer.get('name') != 'rancher' or issuer.get('kind', 'Issuer') != 'Issuer' or issuer.get('group', 'cert-manager.io') != 'cert-manager.io':
            raise RuntimeError('Unexpected leaf certificate source')
        data = source['data']
        resources.append(owned_resource('Secret',destination,namespace,{k:data[k] for k in ('tls.crt','tls.key')},'kubernetes.io/tls'))
        ca = base64.b64decode(data['ca.crt']).decode()
        if public_ca is not None and ca != public_ca:
            raise RuntimeError('Leaf certificates have inconsistent CA roots')
        public_ca = ca
    resources += [owned_resource('ConfigMap','portal-identity-ca',NAMESPACE,{'ca.crt':public_ca}),
        owned_resource('Secret','portal-oidc',NAMESPACE,{'client-secret':base64.b64encode(oidc.encode()).decode()},'Opaque'),
        owned_resource('Secret','portal-ghcr',NAMESPACE,{'.dockerconfigjson':base64.b64encode(registry_text.encode()).decode()},'kubernetes.io/dockerconfigjson')]
    # Check every existing destination before writing any: no silent credential adoption.
    for obj in resources:
        old = get(obj['kind'],obj['metadata']['name'],obj['metadata']['namespace'])
        if old:
            if old['metadata'].get('labels',{}).get(LABEL) != OWNER or old.get('type') != obj.get('type'):
                raise RuntimeError('Existing destination has different ownership/type; refusing overwrite')
            obj['metadata']['resourceVersion'] = old['metadata']['resourceVersion']
        obj['_operation'] = 'replace' if old else 'create'
    for obj in resources:
        operation = obj.pop('_operation')
        call(operation,'-f','-',payload=obj)
        saved = get(obj['kind'],obj['metadata']['name'],obj['metadata']['namespace'])
        if saved.get('data') != obj['data']:
            raise RuntimeError('Credential delivery postcondition failed')
    args.registry_authfile.unlink()
    args.registry_authfile.parent.rmdir()
    print('Verified portal credential and leaf certificate delivery; staged registry credential removed. No credential values printed.')


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        print('Portal credential preparation stopped safely (' + type(exc).__name__ + '): ' + (str(exc) if isinstance(exc,RuntimeError) else 'sensitive diagnostic output suppressed'))
        raise SystemExit(1)
