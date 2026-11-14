"""Explicitly authorized, temporary org-local native Grafana verification only.

No CLI/automatic execution. Caller supplies a TLS-verifying, no-redirect transport
and protected receipt writer. Bodies/tokens never belong in diagnostic output.
"""
import secrets
import re
import urllib.parse


class ProbeFailure(RuntimeError):
    pass


def require(value, label):
    if not value:
        raise ProbeFailure(label)


def verify(api, record, *, approved=False, org_id, org_name, own_uid,
           foreign_uids, marker, query):
    """api(method,path,headers,body)->(status,decoded JSON); memory-only token.

    api uses approved recovery auth unless Authorization is explicitly supplied.
    record persists sanitized ownership/cleanup receipts outside Git. This is a
    machine Viewer probe, never human OIDC/session revocation evidence.
    """
    require(approved is True, 'explicit approval required')
    require(type(org_id) is int and org_id > 1, 'dedicated tenant org required')
    require(org_name and own_uid and foreign_uids and own_uid not in foreign_uids,
            'exact datasource contract required')
    require(marker and 1 <= len(marker) <= 160, 'benign marker required')
    require(all(re.fullmatch(r'[A-Za-z0-9_-]{1,40}', uid) for uid in [own_uid, *foreign_uids]), 'invalid datasource UID')
    parsed = urllib.parse.urlsplit(query)
    params = urllib.parse.parse_qs(parsed.query)
    require(not parsed.scheme and not parsed.netloc and not parsed.fragment and
            parsed.path == '/loki/api/v1/query_range' and
            params.get('limit') == ['5'], 'bounded local Loki query required')
    headers = {'X-Grafana-Org-Id': str(org_id)}
    status, org = api('GET', '/api/orgs/'+str(org_id), headers, None)
    require(status == 200 and org['id'] == org_id and org['name'] == org_name,
            'org identity mismatch')
    name = 'pf-isolation-probe-'+secrets.token_hex(12)
    sa_id = None
    token = None
    receipt = {'org_id': org_id, 'name': name, 'passed': False, 'cleaned': False}
    try:
        status, sa = api('POST', '/api/serviceaccounts/', headers,
                         {'name': name, 'role': 'Viewer', 'isDisabled': False})
        require(status == 201, 'service account creation failed')
        # Record ID before assertions so any malformed readback still gets cleanup.
        sa_id = sa['id']
        receipt['service_account_id'] = sa_id
        record(receipt.copy())
        require(sa['orgId'] == org_id and sa['name'] == name and sa['role'] == 'Viewer',
                'service account identity mismatch')
        status, created = api('POST', f'/api/serviceaccounts/{sa_id}/tokens', headers,
                              {'name': name, 'secondsToLive': 600})
        require(status == 200, 'token creation failed')
        token = created['key']
        actor = {'Authorization': 'Bearer '+token}
        status, sources = api('GET', '/api/datasources', actor, None)
        require(status == 200 and {s['uid'] for s in sources} == {own_uid},
                'unexpected tenant datasource inventory')
        status, source = api('GET', '/api/datasources/uid/'+own_uid, actor, None)
        require(status == 200 and source['orgId'] == org_id, 'own datasource absent')
        status, result = api('GET', '/api/datasources/proxy/uid/'+own_uid+query, actor, None)
        require(status == 200 and result.get('status') == 'success', 'own query failed')
        lines = [v[1] for stream in result.get('data', {}).get('result', [])
                 for v in stream.get('values', [])]
        require(any(marker in line for line in lines), 'benign marker absent')
        for uid in foreign_uids:
            for path in ['/api/datasources/uid/'+uid,
                         '/api/datasources/proxy/uid/'+uid+query]:
                for extra in [{}, {'X-Grafana-Org-Id': '1'}]:
                    status, _ = api('GET', path, actor | extra, None)
                    require(status in (401, 403, 404), 'foreign datasource accessible')
            status, _ = api('POST', '/api/ds/query', actor, {
                'from': 'now-5m', 'to': 'now', 'queries': [{
                    'refId': 'A', 'datasource': {'uid': uid, 'type': 'loki'},
                    'expr': '{namespace="synthetic-denial"}', 'queryType': 'range', 'maxLines': 1}]})
            require(status in (400, 401, 403, 404), 'foreign query API accepted')
        status, _ = api('POST', '/api/user/using/1', actor, None)
        require(status in (401, 403, 404), 'foreign org switch accepted')
        receipt['passed'] = True
    finally:
        if sa_id is not None:
            status, _ = api('DELETE', f'/api/serviceaccounts/{sa_id}', headers, None)
            require(status == 200, 'cleanup failed: recovery intervention required')
            status, _ = api('GET', f'/api/serviceaccounts/{sa_id}', headers, None)
            require(status == 404, 'deleted service account still present')
            if token:
                status, _ = api('GET', '/api/datasources',
                                {'Authorization': 'Bearer '+token}, None)
                require(status == 401, 'revoked token still accepted')
            receipt['cleaned'] = True
        record(receipt.copy())
    return receipt
