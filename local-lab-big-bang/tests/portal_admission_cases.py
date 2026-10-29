"""Offline synthetic requests from the proposed enrollment and real app chart."""
from copy import deepcopy
import json
import os
from pathlib import Path
import yaml
from render_helpers import build, helm, ordered_values


def fixtures():
    enrollment = Path(os.environ['PORTAL_ENROLLMENT_CHECKOUT'])
    app = Path(os.environ['PORTAL_APP_CHECKOUT'])
    foundation = build(enrollment / 'tenants/portal/foundation')
    policies = [o for o in foundation if o['kind'] == 'ValidatingAdmissionPolicy']
    roots = build(app / 'gitops/clusters/local')
    release = next(o for o in roots if o['kind'] == 'HelmRelease')
    workloads = helm(app / 'bundles/portal/chart', 'portal', 'tenant-portal',
                     ordered_values(roots, release), ['--set', 'enabled=true'])
    deployment = next(o for o in workloads if o['kind'] == 'Deployment')
    service = next(o for o in workloads if o['kind'] == 'Service')
    params = next(o for o in foundation if o['kind'] == 'ConfigMap' and o['metadata']['name'] == 'portal-runtime-contract')
    assert params['data']['image'] == deployment['spec']['template']['spec']['containers'][0]['image']
    cases = []

    def add(name, policy, obj, allowed=True, parameter=params):
        cases.append({'name': name, 'policy': policy, 'object': deepcopy(obj),
                      'allowed': allowed, 'params': deepcopy(parameter)})

    runtime = 'portal-runtime-boundary'
    add('approved portal chart', runtime, deployment)
    add('unpublished image contract', runtime, deployment, False, {'data': {'image': 'UNRELEASED'}})
    add('missing contract', runtime, deployment, False, None)
    for name, mutate in [
        ('controller identity mount', lambda p: p.update(serviceAccountName='portal-deployer')),
        ('unexpected node placement', lambda p: p.update(nodeSelector={'kubernetes.io/hostname':'cks-control'})),
        ('API token mount', lambda p: p.update(automountServiceAccountToken=True)),
        ('extra container', lambda p: p['containers'].append(deepcopy(p['containers'][0]))),
        ('init container', lambda p: p.update(initContainers=[deepcopy(p['containers'][0])])),
        ('unreviewed image', lambda p: p['containers'][0].update(image='evil.invalid/image:latest')),
        ('entrypoint override', lambda p: p['containers'][0].update(command=['sh'])),
        ('extra secret env', lambda p: p['containers'][0].update(envFrom=[{'secretRef': {'name': 'other'}}])),
        ('token volume', lambda p: p['volumes'].append({'name': 'token', 'projected': {'sources': []}})),
        ('writable CA', lambda p: p['containers'][0]['volumeMounts'][0].update(readOnly=False)),
    ]:
        obj = deepcopy(deployment); mutate(obj['spec']['template']['spec']); add(name, runtime, obj, False)
    for key, value in [('PORTAL_ACCESS_POLICY', 'home'), ('PORTAL_ACCESS_POLICY', ''),
                       ('OIDC_ISSUER', 'https://wrong.invalid'), ('OIDC_CLIENT_ID', 'headlamp-local'),
                       ('OIDC_AUDIENCE', 'headlamp-local'), ('TENANT_SOURCE', 'live')]:
        obj = deepcopy(deployment)
        next(e for e in obj['spec']['template']['spec']['containers'][0]['env'] if e['name'] == key)['value'] = value
        add(key + ' ' + value, runtime, obj, False)
    obj = deepcopy(deployment)
    obj['spec']['template']['spec']['containers'][0]['env'] = [e for e in obj['spec']['template']['spec']['containers'][0]['env'] if e['name'] != 'PORTAL_ACCESS_POLICY']
    add('missing access policy', runtime, obj, False)
    obj = deepcopy(deployment); obj['spec']['replicas'] = 2; add('overlapping replicas', runtime, obj, False)

    reconcile = 'portal-reconciliation-boundary'
    release['metadata']['namespace'] = 'tenant-portal-config'
    add('scoped release', reconcile, release)
    for key, value in [('serviceAccountName', ''), ('serviceAccountName', 'default'),
                       ('targetNamespace', 'kube-system'), ('storageNamespace', 'bigbang'),
                       ('kubeConfig', {'secretRef': {'name': 'admin'}}),
                       ('postRenderers', [{'kustomize': {}}])]:
        obj = deepcopy(release); obj['spec'][key] = value; add('release ' + key, reconcile, obj, False)
    obj = deepcopy(release); obj['spec']['chart']['spec']['sourceRef']['namespace'] = 'bigbang'
    add('cross namespace chart', reconcile, obj, False)
    obj = deepcopy(release); obj['spec']['chart']['spec']['chart'] = './other-chart'
    add('unreviewed chart path', reconcile, obj, False)
    child = next(o for o in build(enrollment / 'clusters/local') if o['kind'] == 'Kustomization')
    add('scoped child', 'portal-child-boundary', child)
    for key, value in [('serviceAccountName', ''), ('targetNamespace', 'kube-system'), ('path', './other')]:
        obj = deepcopy(child); obj['spec'][key] = value; add('child ' + key, 'portal-child-boundary', obj, False)

    add('private service', 'portal-service-boundary', service)
    for key, value in [('type', 'NodePort'), ('externalIPs', ['192.0.2.1']), ('selector', {'app': 'other'})]:
        obj = deepcopy(service); obj['spec'][key] = value; add('service ' + key, 'portal-service-boundary', obj, False)
    schemas = {}
    manifest = Path(os.environ['PREFLIGHT_SOURCES_DIR']) / 'bigbang/base/flux/gotk-components.yaml'
    for obj in yaml.safe_load_all(manifest.read_text()):
        if obj and obj.get('kind') == 'CustomResourceDefinition' and obj['spec']['names']['kind'] in ['HelmRelease','Kustomization']:
            for version in obj['spec']['versions']:
                if version.get('served'):
                    key = 'io.k8s.api.' + obj['spec']['group'] + '.' + version['name'] + '.' + obj['spec']['names']['kind']
                    schemas[key] = version['schema']['openAPIV3Schema']
    return {'policies': policies, 'cases': cases, 'fluxSchemas': schemas}


if __name__ == '__main__':
    print(json.dumps(fixtures()))
