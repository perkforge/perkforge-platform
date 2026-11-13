"""Validate native-provisioning inputs; never renders, contacts apps or grants access."""
import re
from urllib.parse import urlsplit


class InvalidInputs(ValueError):
    pass


def verify(audiences):
    """Fail closed without printing secrets. Empty list is deliberately unarmed."""
    def require(ok):
        if not ok:
            raise InvalidInputs('Invalid or unapproved alert audience configuration')

    def https(value):
        require(isinstance(value, str) and not any(c.isspace() for c in value))
        try:
            u = urlsplit(value)
            require(u.scheme == 'https' and bool(u.hostname) and not u.username
                    and not u.password and not u.fragment and not u.query)
            return u
        except ValueError:
            raise InvalidInputs('Invalid alert destination') from None

    require(isinstance(audiences, list))
    ids, topics, channels, hooks = set(), set(), set(), set()
    for a in audiences:
        require(isinstance(a, dict))
        require(set(a) == {'id', 'org_id', 'approved', 'ntfy', 'mattermost'})
        require(isinstance(a['id'], str) and re.fullmatch(r'[a-z][a-z0-9-]{0,23}', a['id']))
        require(a['id'] not in ids and a['approved'] is True)
        require(type(a['org_id']) is int and a['org_id'] > 0)
        ids.add(a['id'])
        n, m = a['ntfy'], a['mattermost']
        require(isinstance(n, dict) and set(n) == {'url', 'topic', 'token', 'publisher_permission'})
        require(isinstance(m, dict) and set(m) == {'webhook_url', 'channel_id', 'channel_locked'})
        u = https(n['url'])
        require(isinstance(n['topic'], str) and re.fullmatch(r'[a-z][a-z0-9-]{0,63}', n['topic']))
        require(u.path in ('', '/'))
        require(n['publisher_permission'] == 'exact-topic-write-only')
        require(isinstance(n['token'], str) and len(n['token']) >= 16 and not any(c.isspace() for c in n['token']))
        topic = (u.netloc, n['topic'])
        require(topic not in topics)
        topics.add(topic)
        w = https(m['webhook_url'])
        require(re.fullmatch(r'/hooks/[a-z0-9]{26}', w.path))
        require(isinstance(m['channel_id'], str) and re.fullmatch(r'[a-z0-9]{26}', m['channel_id']))
        require(m['channel_locked'] is True)
        channel = (w.netloc, m['channel_id'])
        require(channel not in channels and m['webhook_url'] not in hooks)
        channels.add(channel)
        hooks.add(m['webhook_url'])
    return True
