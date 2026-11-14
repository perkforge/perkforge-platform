#!/usr/bin/env python3
"""Read-only native identity verification, not account or membership management."""
import argparse
import datetime as dt
import json
import os
import re
import ssl
import stat
import urllib.parse
import urllib.request
from verify_group_paths import safe

LIMIT = 65536


def read_private(path, limit=LIMIT):
    safe(path, limit=limit)
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        s = os.fstat(fd)
        if not stat.S_ISREG(s.st_mode) or s.st_uid != os.getuid() or stat.S_IMODE(s.st_mode) != 0o600 or s.st_nlink != 1 or s.st_size > limit:
            raise ValueError('unsafe opened input')
        with os.fdopen(fd, 'rb', closefd=False) as stream:
            value = stream.read(limit + 1)
        if len(value) > limit:
            raise ValueError('oversized input')
        return value
    finally:
        os.close(fd)


def unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('duplicate key')
        result[key] = value
    return result


def inputs(path):
    data = json.loads(read_private(path), object_pairs_hook=unique)
    patterns = {
        'context': r'[a-z][a-z0-9-]{0,30}',
        'subject': r'[a-f0-9]{8}(?:-[a-f0-9]{4}){3}-[a-f0-9]{12}',
        'source_revision': r'[a-f0-9]{40}',
        'origin': r'https://[A-Za-z0-9.-]+(?::[0-9]+)?',
        'ca_file': r'/[A-Za-z0-9_./-]+',
    }
    if not isinstance(data, dict) or set(data) != set(patterns):
        raise ValueError('unexpected input keys')
    for key, pattern in patterns.items():
        if not isinstance(data[key], str) or not re.fullmatch(pattern, data[key]):
            raise ValueError('nonliteral input')
    if data['context'] in {'platform', 'system', 'default', 'tenants'}:
        raise ValueError('reserved context')
    safe(data['ca_file'], limit=262144, private=False)
    return data


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        raise ValueError('redirect forbidden')


def resolve(data, token):
    opener = urllib.request.build_opener(
        urllib.request.ProxyHandler({}), NoRedirect(),
        urllib.request.HTTPSHandler(context=ssl.create_default_context(cafile=data['ca_file'])))

    def get(path):
        request = urllib.request.Request(data['origin'] + '/api/v4/' + path,
                                         headers={'PRIVATE-TOKEN': token, 'Accept': 'application/json'}, method='GET')
        with opener.open(request, timeout=10) as response:
            if response.status != 200:
                raise ValueError('native verification failed')
            raw = response.read(LIMIT + 1)
            if len(raw) > LIMIT:
                raise ValueError('oversized native response')
            if response.headers.get('X-Next-Page', ''):
                raise ValueError('ambiguous paginated identity')
            return json.loads(raw, object_pairs_hook=unique)

    authority = get('personal_access_tokens/self')
    if not isinstance(authority, dict) or authority.get('active') is not True or authority.get('revoked') is not False:
        raise ValueError('inactive reader')
    scopes = authority.get('scopes')
    if not isinstance(scopes, list) or len(scopes) != len(set(scopes)) or set(scopes) not in ({'read_api'}, {'read_api', 'self_rotate'}):
        raise ValueError('unexpected reader scopes')
    expiry = authority.get('expires_at')
    if not isinstance(expiry, str) or dt.date.fromisoformat(expiry) <= dt.datetime.now(dt.timezone.utc).date():
        raise ValueError('reader expiry missing or elapsed')
    users = get('users?' + urllib.parse.urlencode({'provider': 'openid_connect', 'extern_uid': data['subject'], 'per_page': 2}))
    if not isinstance(users, list) or len(users) > 1:
        raise ValueError('ambiguous identity')
    result = {'schema': 1, 'origin': data['origin'], 'context': data['context'],
              'subject': data['subject'], 'source_revision': data['source_revision'],
              'captured_at': dt.datetime.now(dt.timezone.utc).isoformat(), 'stage': 'PendingFirstLogin'}
    if not users:
        return result
    user = users[0]
    if not isinstance(user, dict) or type(user.get('id')) is not int or not 0 < user['id'] < 2**63 or user.get('is_admin') is not False:
        raise ValueError('invalid tenant identity')
    identities = user.get('identities')
    if not isinstance(identities, list):
        raise ValueError('privileged identity read unavailable')
    oidc = [item for item in identities if isinstance(item, dict) and item.get('provider') == 'openid_connect']
    if len(oidc) != 1 or oidc[0].get('extern_uid') != data['subject']:
        raise ValueError('subject mismatch')
    if user.get('state') == 'active':
        result.update(stage='IdentityVerified', native_user_id=user['id'])
    elif user.get('state') in {'blocked', 'blocked_pending_approval'}:
        result['stage'] = 'PendingAccountApproval'
    else:
        raise ValueError('unsupported account state')
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--verify', action='store_true')
    mode.add_argument('--validate', action='store_true')
    parser.add_argument('token', nargs='?')
    parser.add_argument('receipt', nargs='?')
    parser.add_argument('inputs', nargs='?')
    args = parser.parse_args(argv)
    if not args.verify and not args.validate:
        print('INERT: explicit verification required')
        return
    data = inputs(args.inputs)
    safe(args.token, limit=4096)
    safe(args.receipt, optional=True)
    if os.path.lexists(args.receipt):
        raise ValueError('fresh receipt path required')
    if args.validate:
        print('Validated; no authentication or receipt write')
        return
    # Exclusive reservation before authentication prevents concurrent writers. Failed runs
    # remove only this exact owned inode, never preserve an apparently successful receipt.
    fd = os.open(args.receipt, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    owned = os.fstat(fd)
    try:
        token = read_private(args.token, 4096).decode('ascii').strip()
        if not re.fullmatch(r'[A-Za-z0-9_-]{8,4096}', token):
            raise ValueError('invalid reader token encoding')
        result = resolve(data, token)
        encoded = (json.dumps(result, sort_keys=True) + '\n').encode()
        with os.fdopen(fd, 'wb', closefd=False) as stream:
            stream.write(encoded)
            stream.flush()
            os.fsync(fd)
        print(result['stage'])
    except Exception:
        current = os.lstat(args.receipt)
        if (current.st_dev, current.st_ino) == (owned.st_dev, owned.st_ino):
            os.unlink(args.receipt)
        raise
    finally:
        os.close(fd)


if __name__ == '__main__':
    try:
        main()
    except Exception:
        raise SystemExit('Identity verification failed; no native mutation performed.')
