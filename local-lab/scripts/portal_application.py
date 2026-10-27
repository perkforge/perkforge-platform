#!/usr/bin/env python3
"""Portal application rendering helpers for the existing tenant foundation renderer."""
from __future__ import annotations
import json
from pathlib import Path
import re
from urllib.parse import urlsplit
import yaml
import tenant_templates

ROOT = Path(__file__).resolve().parents[2]
PREVIEW = ROOT / 'local-lab/tenant-config/generated/home/portal'


def validate(c):
    expected = {'lifecycle', 'kubernetesVersion', 'namespace',
                'runtimeServiceAccount', 'deployerServiceAccount', 'fleetAgentNamespace',
                'portalOrigin', 'identity', 'tenantRevision', 'imageRepository', 'imageDigest'}
    if set(c) != expected:
        raise ValueError('Unexpected or missing contract fields')
    if c['lifecycle'] not in ({'state':'disabled'}, {'state':'paused'}, {'state':'active'}):
        raise ValueError('Application lifecycle.state must be disabled, paused, or active; decommission is separate')
    if c['lifecycle']['state'] != 'disabled' and c['imageDigest'] is None:
        raise ValueError('Provisioned application requires a reviewed image digest')
    fixed = {'kubernetesVersion': '1.36', 'namespace': 'tenant-home-portal',
             'runtimeServiceAccount': 'portal-runtime', 'deployerServiceAccount': 'home-portal-deployer',
             'fleetAgentNamespace': 'cattle-fleet-local-system',
             'imageRepository': 'ghcr.io/perkforge/perkforge-portal'}
    if any(c[k] != v for k, v in fixed.items()):
        raise ValueError('Fixed application scope or target version changed')
    identity = c['identity']
    if set(identity) != {'realm', 'issuer', 'clientId', 'audience', 'existingSecret', 'secretKey', 'requiredRole', 'groups'}:
        raise ValueError('Unexpected identity fields (credentials are forbidden)')
    for key in ('realm', 'clientId', 'audience', 'existingSecret', 'secretKey', 'requiredRole'):
        if not re.fullmatch(r'[a-z][a-z0-9-]{0,62}', identity[key]):
            raise ValueError(f'Invalid identity {key}')
    if identity['secretKey'] != 'client-secret':
        raise ValueError('Tenant chart uses the fixed client-secret key')
    if identity['realm'] != 'perkforge' or identity['requiredRole'] != 'tenant-reader':
        raise ValueError('Existing realm/application role contract must be preserved')
    if identity['clientId'] == identity['audience']:
        raise ValueError('Separate browser client and API audience required')
    if identity['groups'] != [f'/tenants/home/{r}' for r in ('admins', 'developers', 'viewers')]:
        raise ValueError('Only existing Home groups are supported')
    for value in (c['portalOrigin'], identity['issuer']):
        u = urlsplit(value)
        if u.scheme != 'https' or not u.hostname or u.username or u.password or u.query or u.fragment:
            raise ValueError('Verified HTTPS endpoints required')
    if urlsplit(c['portalOrigin']).path or not identity['issuer'].endswith('/realms/perkforge'):
        raise ValueError('Exact origin and realm issuer required')
    if not re.fullmatch(r'[a-f0-9]{40}', c['tenantRevision']):
        raise ValueError('Tenant revision must be a full immutable commit')
    if c['imageDigest'] is not None and not re.fullmatch(r'sha256:[a-f0-9]{64}', c['imageDigest']):
        raise ValueError('Image must be a reviewed digest or null (deny workloads)')
    return c


def helm_values(c):
    return tenant_templates.render('helm-values', portal=c)[0]


def identity_plan(c):
    return tenant_templates.render('identity-plan', portal=c)[0]


def resources(c):
    return tenant_templates.render('portal', portal=c)


def admission(c):
    return [obj for obj in resources(c) if obj['kind'].startswith('ValidatingAdmissionPolicy')]


def outputs(c):
    validate(c)
    reference = tenant_templates.render('tenant-fleet-reference', portal=c)[0]
    return {'resources.yaml': yaml.safe_dump_all(resources(c), sort_keys=False),
            'identity-plan.json': json.dumps(identity_plan(c), indent=2) + '\n',
            'helm-values.yaml': yaml.safe_dump(helm_values(c), sort_keys=False),
            'tenant-fleet-reference.yaml': yaml.safe_dump(reference, sort_keys=False)}


def contract_for(catalog, tenant_id='home', application_id='portal'):
    import copy
    if (tenant_id, application_id) != ('home', 'portal'):
        raise ValueError('Only the Home portal application is supported')
    tenant = next((t for t in catalog['tenants'] if t['id'] == tenant_id), None)
    if tenant is None or application_id not in tenant.get('applications', {}):
        raise ValueError('Home portal application is absent from the catalog')
    if tenant['cluster'] != 'local':
        raise ValueError('Portal application currently supports Home on the local cluster only')
    if tenant.get('classification') != 'protected' or tenant['identity']['provider'] != 'keycloak':
        raise ValueError('Portal remains a protected Home Keycloak application')
    c = copy.deepcopy(tenant['applications'][application_id])
    if not isinstance(c,dict) or not isinstance(c.get('identity'),dict):
        raise ValueError('Application and identity must be mappings')
    if 'kubernetesVersion' in c or 'groups' in c.get('identity', {}):
        raise ValueError('Application must inherit cluster version and Home groups')
    c['kubernetesVersion'] = next(x['podSecurityVersion'] for x in catalog['clusters'] if x['name']==tenant['cluster']).removeprefix('v')
    c['identity']['groups'] = [tenant['identity']['groups'][r] for r in ('admins','developers','viewers')]
    validate(c)
    if c['lifecycle']['state'] == 'disabled' and any(e['namespace']==c['namespace'] for e in tenant['environments']):
        raise ValueError('Disabled means unprovisioned; an allocated portal namespace must remain paused or active')
    if c['lifecycle']['state'] != 'disabled' and not any(e['namespace']==c['namespace'] for e in tenant['environments']):
        raise ValueError('Provisioned portal requires an explicitly budgeted Home environment namespace')
    return c


def load_contract():
    from tenant_catalog import load_catalog
    return contract_for(load_catalog(ROOT/'local-lab/tenant-config/tenants.yaml'))


def validate_applications(catalog):
    for tenant in catalog['tenants']:
        apps=tenant.get('applications', {})
        if not isinstance(apps,dict) or (apps and (tenant['id']!='home' or set(apps)!={'portal'})):
            raise ValueError('Only applications.portal on existing Home is supported')
        if apps:
            contract_for(catalog)


def active_resources(catalog):
    validate_applications(catalog)
    home=next((t for t in catalog['tenants'] if t['id']=='home'), {})
    if not home.get('applications'):
        return []
    c=contract_for(catalog)
    if c['lifecycle']['state']=='disabled':
        return []
    # Base tenant foundation already owns default-deny for protected namespaces.
    result=[o for o in resources(c) if not (o["kind"]=="NetworkPolicy" and o["metadata"]["name"]=="default-deny")]
    for obj in result:
        obj['metadata'].setdefault('labels', {}).update({'platform.perkforge.io/tenant':'home', 'platform.perkforge.io/application':'portal', 'platform.perkforge.io/managed-by':'tenant-application'})
    return result
