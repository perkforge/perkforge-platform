"""Strict offline selection validation; not an installer or runtime authorization."""
import re
from urllib.parse import urlsplit


def verify(v):
    def need(ok):
        if not ok:
            raise ValueError('Invalid inactive pipeline snapshot selection')
    def match(x, pattern):
        return isinstance(x, str) and re.fullmatch(pattern, x) is not None
    need(isinstance(v, dict) and set(v) == {'snapshot_enabled', 'context_id', 'grafana_org_id', 'prometheus_uid', 'gitlab_url', 'interval_seconds', 'timeout_seconds', 'freshness_seconds', 'snapshot_targets'})
    need(type(v['snapshot_enabled']) is bool)
    need(match(v['context_id'], r'[a-z][a-z0-9-]{0,30}'))
    need(type(v['grafana_org_id']) is int and v['grafana_org_id'] > 0)
    need(match(v['prometheus_uid'], r'[A-Za-z0-9_-]{1,64}'))
    need(match(v['gitlab_url'], r'https://[A-Za-z0-9.-]+(?::[0-9]{1,5})?/?'))
    u = urlsplit(v['gitlab_url'])
    need(u.scheme == 'https' and bool(u.hostname) and not u.username and not u.password and not u.query and not u.fragment and u.path in ('', '/') and match(u.netloc, r'[A-Za-z0-9.-]+(?::[0-9]{1,5})?'))
    try:
        need(u.port is None or 1 <= u.port <= 65535)
    except ValueError:
        raise ValueError('Invalid HTTPS origin') from None
    interval, timeout, fresh = (v[k] for k in ('interval_seconds', 'timeout_seconds', 'freshness_seconds'))
    need(all(type(x) is int for x in (interval, timeout, fresh)))
    need(15 <= interval <= 300 and 1 <= timeout <= 30 and timeout < interval and interval <= fresh <= 3 * interval)
    targets = v['snapshot_targets']
    need(isinstance(targets, list) and 1 <= len(targets) <= 16 and len(targets) * timeout <= interval)
    ids, paths, tuples, uids = {}, {}, set(), set()
    for t in targets:
        need(isinstance(t, dict) and set(t) == {'uid', 'project_id', 'project', 'ref', 'source'})
        need(match(t['uid'], r'[a-z][a-z0-9-]{0,29}') and t['uid'] not in uids)
        need(type(t['project_id']) is int and 0 < t['project_id'] < 2**63)
        need(match(t['project'], r'[A-Za-z0-9_-]+(?:/[A-Za-z0-9_.-]+)+') and len(t['project']) <= 200 and all(x not in ('.', '..') for x in t['project'].split('/')))
        need(match(t['ref'], r'[A-Za-z0-9_-][A-Za-z0-9_./-]{0,127}') and '..' not in t['ref'] and '//' not in t['ref'] and not t['ref'].endswith(('/', '.lock')))
        need(isinstance(t['source'], str) and t['source'] in ('push', 'web'))
        need(ids.get(t['project_id'], t['project']) == t['project'] and paths.get(t['project'], t['project_id']) == t['project_id'])
        key = (t['project_id'], t['ref'], t['source'])
        need(key not in tuples)
        ids[t['project_id']] = t['project']; paths[t['project']] = t['project_id']; tuples.add(key); uids.add(t['uid'])
