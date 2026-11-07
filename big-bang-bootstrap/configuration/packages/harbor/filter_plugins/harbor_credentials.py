"""Pure validation only. Ansible owns assembly, file custody and API operations."""
import base64
import json
import posixpath
import re
from datetime import datetime, timezone


def ancestors(path):
    if not isinstance(path, str) or not path.startswith('/') or posixpath.normpath(path) != path or '//' in path:
        raise ValueError('A canonical absolute private path is required')
    parts = path.split('/')[1:]
    return ['/'] + ['/' + '/'.join(parts[:i]) for i in range(1, len(parts) + 1)]


def protected_path(results, path, root, uid, optional=False):
    try:
        expected = ancestors(path)
        ancestors(root)
        if root in ('/', '/home', '/tmp', '/var', '/run') or not path.startswith(root + '/'):
            return False
        if [r.get('harbor_path_component', r.get('item')) for r in results] != expected:
            return False
        for record in results:
            p, s = record.get('harbor_path_component', record.get('item')), record['stat']
            if p == path and not s.get('exists'):
                if optional:
                    continue
                return False
            if not s.get('exists') or s.get('islnk'):
                return False
            if p == path:
                if not s.get('isreg') or s.get('mode') != '0600' or s.get('uid') != uid or s.get('nlink') != 1 or not 0 < s.get('size', 0) <= 1048576:
                    return False
            elif p == root or p.startswith(root + '/'):
                if not s.get('isdir') or s.get('mode') != '0700' or s.get('uid') != uid:
                    return False
            elif not s.get('isdir') or s.get('uid') not in (0, uid) or int(s['mode'], 8) & 0o022:
                return False
        return True
    except (KeyError, TypeError, ValueError):
        return False


def _certs(pem):
    from cryptography import x509
    if not isinstance(pem, str):
        raise ValueError('Certificate-only PEM required')
    blocks = re.findall(r'-----BEGIN CERTIFICATE-----\s+[A-Za-z0-9+/=\s]+-----END CERTIFICATE-----', pem)
    remaining = pem
    for block in blocks:
        remaining = remaining.replace(block, '', 1)
    if not blocks or remaining.strip():
        raise ValueError('Certificate-only PEM required')
    return [x509.load_pem_x509_certificate(b.encode()) for b in blocks]


def _fingerprint(cert):
    from cryptography.hazmat.primitives import hashes
    return cert.fingerprint(hashes.SHA256()).hex()


def _ca_bundle(pem):
    from cryptography import x509
    certs = _certs(pem)
    now = datetime.now(timezone.utc)
    for c in certs:
        if not c.extensions.get_extension_for_class(x509.BasicConstraints).value.ca:
            raise ValueError('Trust bundle must contain CA certificates only')
        if not c.not_valid_before_utc <= now < c.not_valid_after_utc:
            raise ValueError('CA outside validity interval')
        if not c.extensions.get_extension_for_class(x509.KeyUsage).value.key_cert_sign:
            raise ValueError('CA cannot sign certificates')
    if len({_fingerprint(c) for c in certs}) != len(certs):
        raise ValueError('Supply a deduplicated public CA bundle')
    return certs


def _key_pair(data):
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    certs = _certs(data['tls.crt'])
    if not re.fullmatch(r'\s*-----BEGIN (RSA PRIVATE KEY|PRIVATE KEY)-----\s+[A-Za-z0-9+/=\s]+-----END \1-----\s*', data['tls.key']):
        raise ValueError('Exactly one unencrypted private key PEM required')
    key = serialization.load_pem_private_key(data['tls.key'].encode(), password=None)
    # Harbor token signing is RS256; all network leaves use the reviewed RSA baseline.
    if not isinstance(key, rsa.RSAPrivateKey) or key.key_size < 2048:
        raise ValueError('RSA key of at least 2048 bits required')
    public = lambda k: k.public_bytes(serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo)
    if public(key.public_key()) != public(certs[0].public_key()):
        raise ValueError('Certificate and key do not match')
    now = datetime.now(timezone.utc)
    if not certs[0].not_valid_before_utc <= now < certs[0].not_valid_after_utc:
        raise ValueError('Certificate outside validity interval')
    return certs


def _tls(data, ca, names):
    from cryptography import x509
    from cryptography.x509.verification import PolicyBuilder, Store
    certs = _key_pair(data)
    san = certs[0].extensions.get_extension_for_class(x509.SubjectAlternativeName).value
    if len(san) != len(names) or set(san.get_values_for_type(x509.DNSName)) != set(names):
        raise ValueError('Leaf SANs must match only the reviewed service identities')
    store = Store(_ca_bundle(ca))
    for name in names:
        PolicyBuilder().store(store).time(datetime.now(timezone.utc)).build_server_verifier(x509.DNSName(name)).verify(certs[0], certs[1:])


def _password(value, minimum=16, maximum=4096):
    return isinstance(value, str) and minimum <= len(value) <= maximum and all(33 <= ord(c) <= 126 for c in value)


def _values(items, profile, pins, database_pin, valkey_pin, identity_pin):
    from cryptography import x509
    d = {i['metadata']['name']: i['stringData'] for i in items}
    if profile == 'data':
        if d['harbor-database']['username'] != 'harbor' or not _password(d['harbor-database']['password']):
            return False
        cache = d['harbor-valkey-acl']['default']
        # Valkey's ACL password file is interpolated into its generated ACL config.
        if not re.fullmatch(r'[A-Za-z0-9_-]{24,128}', cache) or d['harbor-redis']['REDIS_PASSWORD'] != cache:
            return False
        _tls(d['harbor-valkey-tls'], d['harbor-valkey-tls']['ca.crt'], ['harbor-valkey','harbor-valkey.harbor.svc','harbor-valkey.harbor.svc.cluster.local'])
        return True
    if profile != 'application':
        return False
    for name, key in [('initial-admin','HARBOR_ADMIN_PASSWORD'), ('encryption-key','secretKey'), ('core-auth','secret'), ('xsrf','CSRF_KEY'), ('jobservice-auth','JOBSERVICE_SECRET'), ('registry-auth','REGISTRY_HTTP_SECRET')]:
        if not _password(d['harbor-' + name][key], 32 if name == 'xsrf' else 16):
            return False
    if len(d['harbor-encryption-key']['secretKey'].encode('ascii')) != 16:
        return False
    credentials = d['harbor-registry-credentials']
    if not _password(credentials['REGISTRY_PASSWD'], maximum=72):
        return False
    htpasswd = credentials['REGISTRY_HTPASSWD'].removesuffix('\n')
    if not re.fullmatch(r'harbor_registry_user:\$2[aby]\$(?:0[4-9]|1[0-6])\$[./A-Za-z0-9]{53}', htpasswd):
        return False
    import bcrypt
    if not bcrypt.checkpw(credentials['REGISTRY_PASSWD'].encode(), htpasswd.split(':', 1)[1].encode()):
        return False
    token = _key_pair(d['harbor-token-signing'])
    if len(token) != 1:
        return False
    try:
        if not token[0].extensions.get_extension_for_class(x509.KeyUsage).value.digital_signature:
            return False
    except x509.ExtensionNotFound:
        return False
    internal = d['harbor-internal-ca']['ca.crt']
    internal_fingerprints = {_fingerprint(c) for c in _ca_bundle(internal)}
    for component in ('core','jobservice','registry','portal'):
        leaf = d['harbor-' + component + '-tls']
        if {_fingerprint(c) for c in _ca_bundle(leaf['ca.crt'])} != internal_fingerprints:
            return False
        _tls(leaf, internal, ['harbor-' + component + suffix for suffix in ('','.harbor.svc','.harbor.svc.cluster.local')])
    public = d['harbor-public-ca']['ca.crt']
    public_fingerprints = {_fingerprint(c) for c in _ca_bundle(public)}
    if not isinstance(pins, list) or len(pins) != len(set(pins)) or not all(isinstance(p, str) and re.fullmatch('[0-9a-f]{64}', p) for p in pins):
        return False
    if set(pins) != public_fingerprints or not {database_pin, valkey_pin, identity_pin} <= public_fingerprints or not internal_fingerprints <= public_fingerprints:
        return False
    _tls(d['harbor-service-tls'], public, ['harbor.perkforge.home.arpa'])
    registry = json.loads(d['private-registry']['.dockerconfigjson'])
    if set(registry) != {'auths'} or set(registry['auths']) != {'registry1.dso.mil'}:
        return False
    auth = registry['auths']['registry1.dso.mil']
    if set(auth) != {'auth'} or not isinstance(auth['auth'], str):
        return False
    decoded = base64.b64decode(auth['auth'], validate=True).decode()
    username, password = decoded.split(':', 1)
    return bool(username and password) and not any(c in decoded for c in '\r\n\x00')


def manifest_valid(manifest, contract, namespace_uid, profile, pins=None, database_pin=None, valkey_pin=None, identity_pin=None):
    try:
        if set(manifest) != {'apiVersion','kind','items'} or manifest['apiVersion'] != 'v1' or manifest['kind'] != 'List' or not isinstance(manifest['items'], list):
            return False
        items = manifest['items']
        if len(items) != len(contract) or {i['metadata']['name'] for i in items} != set(contract):
            return False
        for item in items:
            c = contract[item['metadata']['name']]
            if set(item) != {'apiVersion','kind','immutable','metadata','type','stringData'} or item['apiVersion'] != 'v1' or item['kind'] != 'Secret' or item['immutable'] is not True or item['type'] != c['type']:
                return False
            m = item['metadata']
            if set(m) != {'name','namespace','labels','annotations'} or m['namespace'] != 'harbor' or m['labels'] != {'perkforge.io/owner': c['owner']} or m['annotations'] != {'perkforge.io/namespace-uid':namespace_uid}:
                return False
            if set(item['stringData']) != set(c['keys']) or not all(isinstance(v,str) and 0 < len(v.encode()) < 262144 for v in item['stringData'].values()):
                return False
        return _values(items, profile, pins or [], database_pin, valkey_pin, identity_pin)
    except Exception:
        # Fail closed without rendering secret material in Ansible exception output.
        return False


def secret_matches(actual, desired, require_uid=True):
    try:
        if set(actual) - {'apiVersion','kind','metadata','immutable','type','data'}:
            return False
        if actual['apiVersion'] != 'v1' or actual['kind'] != 'Secret' or actual.get('immutable') is not True or actual['type'] != desired['type']:
            return False
        m = actual['metadata']
        if set(m) - {'name','namespace','labels','annotations','uid','resourceVersion','creationTimestamp','managedFields','generation'}:
            return False
        for key in ('name','namespace','labels','annotations'):
            if m.get(key) != desired['metadata'][key]:
                return False
        if require_uid and (not isinstance(m.get('uid'), str) or len(m['uid']) < 8):
            return False
        expected = {k: base64.b64encode(v.encode()).decode() for k,v in desired['stringData'].items()}
        return actual.get('data') == expected
    except (KeyError, TypeError, ValueError):
        return False


def namespace_valid(namespace, expected_uid):
    try:
        m = namespace['metadata']
        labels = m['labels']
        return (namespace['apiVersion'] == 'v1' and namespace['kind'] == 'Namespace'
                and m['name'] == 'harbor' and m['uid'] == expected_uid
                and labels.get('perkforge.io/owner') == 'harbor-foundation-v1'
                and not m.get('deletionTimestamp') and not m.get('ownerReferences')
                and namespace.get('status', {}).get('phase') == 'Active')
    except (KeyError, TypeError):
        return False


def kubeconfig_valid(config, context, api):
    try:
        if config.get('current-context') != context or len(config['contexts']) != 1 or len(config['clusters']) != 1:
            return False
        ctx = config['contexts'][0]
        cluster = config['clusters'][0]
        c = cluster['cluster']
        return (ctx['name'] == context and ctx['context']['cluster'] == cluster['name']
                and c['server'] == api and c.get('insecure-skip-tls-verify', False) is False
                and 'proxy-url' not in c and 'tls-server-name' not in c)
    except (KeyError, TypeError):
        return False


class FilterModule:
    def filters(self):
        return {'harbor_kubeconfig_valid': kubeconfig_valid, 'harbor_ancestors': ancestors, 'harbor_protected_path': protected_path,
                'harbor_manifest_valid': manifest_valid, 'harbor_secret_matches': secret_matches,
                'harbor_namespace_valid': namespace_valid}
