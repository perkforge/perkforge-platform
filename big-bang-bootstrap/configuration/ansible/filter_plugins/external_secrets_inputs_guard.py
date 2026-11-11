"""Pure validation only; manifests are authored in Ansible, never generated here."""
import base64
import ipaddress
import json
import re

OWNER = 'external-secrets-inputs-v1'
TARGETS = {('Secret', 'external-secrets', 'private-registry'),
           ('ConfigMap', 'external-secrets', 'openbao-ca'),
           ('ConfigMap', 'bigbang', 'external-secrets-network-values'),
           ('ConfigMap', 'bigbang', 'external-secrets-activation-values')}


def provider_valid(value):
    try:
        address = ipaddress.ip_network(value, strict=True)
        return (str(address) == value and address.version == 4 and address.prefixlen == 32
                and any(address.subnet_of(ipaddress.ip_network(block))
                        for block in ('10.0.0.0/8', '172.16.0.0/12', '192.168.0.0/16')))
    except (ValueError, TypeError):
        return False


def public_pem(value):
    return isinstance(value, str) and bool(re.fullmatch(
        r'-----BEGIN CERTIFICATE-----\r?\n[A-Za-z0-9+/=\r\n]+\r?\n-----END CERTIFICATE-----\s*', value))


def registry_valid(obj):
    try:
        if obj['kind'] != 'Secret' or obj['type'] != 'kubernetes.io/dockerconfigjson':
            return False
        if set(obj['data']) != {'.dockerconfigjson'}:
            return False
        config = json.loads(base64.b64decode(obj['data']['.dockerconfigjson'], validate=True))
        if set(config) != {'auths'} or set(config['auths']) != {'registry1.dso.mil'}:
            return False
        entry = config['auths']['registry1.dso.mil']
        if set(entry) != {'auth'}:
            return False
        username, password = base64.b64decode(entry['auth'], validate=True).decode().split(':', 1)
        return bool(username and password)
    except (ValueError, TypeError, KeyError, UnicodeError):
        return False


def owned(obj):
    try:
        meta = obj['metadata']
        return (obj['apiVersion'] == 'v1'
                and (obj['kind'], meta['namespace'], meta['name']) in TARGETS
                and meta.get('labels', {}).get('perkforge.io/owner') == OWNER
                and obj.get('immutable') is True
                and not any(meta.get(key) for key in ('ownerReferences', 'finalizers', 'deletionTimestamp'))
                and not obj.get('binaryData') and not obj.get('stringData'))
    except (KeyError, TypeError):
        return False


def matches(actual, desired):
    return (owned(actual) and owned(desired)
            and all(actual.get(key) == desired.get(key) for key in ('apiVersion', 'kind', 'type', 'data'))
            and all(actual['metadata'].get(key) == desired['metadata'].get(key)
                    for key in ('namespace', 'name', 'labels', 'annotations')))


class FilterModule:
    def filters(self):
        return {'eso_provider_valid': provider_valid, 'eso_public_pem': public_pem,
                'eso_registry_valid': registry_valid, 'eso_input_owned': owned,
                'eso_input_matches': matches}
