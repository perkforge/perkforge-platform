#!/usr/bin/env python3
"""Pure offline URL/cron verification; never generates configuration or contacts a service."""
import json
import re
import sys
from urllib.parse import urlsplit


def verify(data):
    endpoint = data['endpoint']
    if not isinstance(endpoint, str) or re.search(r'[\s\\]', endpoint):
        raise ValueError('endpoint must be an HTTPS DNS URL without whitespace')
    url = urlsplit(endpoint)
    hostname = url.hostname or ''
    label = r'[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?'
    if (url.scheme != 'https' or url.username is not None or url.password is not None
            or url.path not in ('', '/') or url.query or url.fragment
            or len(hostname) > 253 or not re.fullmatch(label + r'(?:\.' + label + r')*', hostname)
            or not re.search('[a-zA-Z]', hostname) or url.netloc.endswith(':')
            or (url.port is not None and not 1 <= url.port <= 65535)
            or re.search(r'(?i)(example|invalid|placeholder)', hostname)):
        raise ValueError('endpoint requires a valid HTTPS DNS hostname/port with no credentials, query or path')
    prefix = data['prefix']
    if not isinstance(prefix, str) or not re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9/_-]+', prefix):
        raise ValueError('prefix must be an explicit isolated object-store path')
    cron = data['cron']
    if cron is None:
        return
    if not isinstance(cron, str) or len(cron.split()) != 5:
        raise ValueError('cron requires five numeric fields')
    for field, (minimum, maximum) in zip(cron.split(), ((0, 59), (0, 23), (1, 31), (1, 12), (0, 7))):
        for part in field.split(','):
            match = re.fullmatch(r'(\*|\d+(?:-\d+)?)(?:/([1-9]\d*))?', part)
            if not match:
                raise ValueError('invalid cron token')
            span, step = match.groups()
            if step and int(step) > maximum - minimum + 1:
                raise ValueError('cron step exceeds field domain')
            if span != '*':
                numbers = [int(number) for number in span.split('-')]
                if not all(minimum <= number <= maximum for number in numbers) or numbers != sorted(numbers):
                    raise ValueError('cron field outside its ordered range')
    # Review must still establish RPO, DST/timezone, concurrency and missed-run behavior.


if __name__ == '__main__':
    try:
        verify(json.load(sys.stdin))
    except (ValueError, TypeError, KeyError) as error:
        print(str(error), file=sys.stderr)
        sys.exit(1)
