"""Offline review gate for native hook inputs; not a renderer or live reconciler."""
from urllib.parse import urlsplit


def verify(hook, context):
    def require(condition):
        if not condition:
            raise ValueError('Invalid GitLab event hook input')

    require(isinstance(hook, dict))
    require(set(hook) == {'approved', 'context', 'project_id', 'receiver_url', 'token'})
    require(hook['approved'] is True)
    require(hook['context'] == context['id'])
    group_id = context['targets']['gitlab']['group_id']
    ids = context['targets']['gitlab']['project_ids']
    require(type(group_id) is int and group_id > 0)
    require(isinstance(ids, list) and bool(ids))
    require(all(type(i) is int and i > 0 for i in ids) and len(set(ids)) == len(ids))
    require(type(hook['project_id']) is int and hook['project_id'] in ids)
    url = hook['receiver_url']
    require(isinstance(url, str) and not any(c.isspace() for c in url))
    try:
        parsed = urlsplit(url)
        require(parsed.scheme == 'https' and bool(parsed.hostname))
        require(not parsed.username and not parsed.password and not parsed.query and not parsed.fragment)
        require(parsed.port is None or 0 < parsed.port <= 65535)
        require(parsed.path == '/gitlab/events/' + context['id'])
    except ValueError:
        raise ValueError('Invalid GitLab event hook input') from None
    token = hook['token']
    require(isinstance(token, str) and len(token) >= 32 and not any(c.isspace() for c in token))
