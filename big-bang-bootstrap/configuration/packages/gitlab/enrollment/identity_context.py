"""Pure, versioned identity naming/authority contract; no I/O or native actions."""
import hashlib
import json
import re


def derive(context):
    if not isinstance(context, str) or not re.fullmatch(r'[a-z][a-z0-9-]{0,30}', context) or context.endswith('-') or context in {'platform', 'tenants', 'system', 'default'}:
        raise ValueError('InvalidIdentityContext')
    legacy = context == 'portal'
    kc_policy = 'tenant-identity-bootstrap-keycloak-v1' if legacy else f'tenant-identity-bootstrap-keycloak-{context}-v1'
    eso = 'eso-identity-keycloak' if legacy else f'eso-identity-keycloak-{context}'
    result = {
        'schema': 1, 'context': context,
        'binding': 'portal-legacy-v1' if legacy else 'tenant-derived-v1',
        'client_id': f'perkforge-{context}-identity-reader',
        'actor_policy_name': f'perkforge-{context}-reader-actor',
        'permission_name': f'perkforge-{context}-reader-groups',
        'record': f'identity/keycloak/{context}-membership-reader-v1',
        'bootstrap_policy': kc_policy,
        'eso_policy': eso, 'eso_role': eso, 'eso_service_account': eso,
        'writer_namespace': 'tenant-identity-writer' if legacy else f'tenant-identity-{context}-writer',
        'attestor_namespace': 'tenant-identity-attestor' if legacy else f'tenant-identity-{context}-attestor',
        'evidence_name': f'{context}-identity-evidence',
        'group_reconciler': 'identity-group-reconciler' if legacy else f'identity-{context}-group-reconciler',
        'attestor_reconciler': 'identity-attestor-reconciler' if legacy else f'identity-{context}-attestor-reconciler',
        'declaration_reconciler': 'identity-declaration-reconciler' if legacy else f'identity-{context}-declaration-reconciler',
        'declaration_policy': 'identity-declaration-scope' if legacy else f'identity-{context}-declaration-scope',
        'evidence_policy': 'identity-evidence-fields' if legacy else f'identity-{context}-evidence-fields',
        'phase_prefix': f'identity-{context}',
        'writer_eso_role': 'eso-identity-writer' if legacy else f'eso-identity-writer-{context}',
        'writer_eso_service_account': 'eso-identity-writer' if legacy else f'eso-identity-writer-{context}',
        'reader_eso_role': 'eso-identity-reader' if legacy else f'eso-identity-reader-{context}',
        'reader_eso_service_account': 'eso-identity-reader' if legacy else f'eso-identity-reader-{context}',
        'gitlab_writer_record': 'identity/gitlab/tenants-writer-v1',
        'gitlab_reader_record': 'identity/gitlab/tenant-reader-v1',
    }
    result['digest'] = hashlib.sha256(json.dumps(result, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    return result


def policy_text(context):
    """Exact single-record custody ACL, including its own policy readback."""
    d = derive(context)
    return ('path "auth/token/lookup-self" { capabilities = ["read"] }\n'
            f'path "sys/policies/acl/{d["bootstrap_policy"]}" {{ capabilities = ["read"] }}\n'
            f'path "platform/metadata/{d["record"]}" {{ capabilities = ["read"] }}\n'
            f'path "platform/data/{d["record"]}" {{ capabilities = ["create", "update", "read"] }}\n')
