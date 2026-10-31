#!/usr/bin/env python3
"""Read-only verification of an uncompressed etcd snapshot's SHA-256 trailer.

Matches the hash/layout rule in etcd/etcdutl/snapshot/v3_snapshot.go.
This is byte-integrity verification, not a bbolt consistency or restore test.
"""
import hashlib
import hmac
import json
import os
from pathlib import Path
import stat
import sys


def verify(path):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(fd, 'rb') as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_size < 544 or info.st_size % 512 != 32:
            raise ValueError('Missing uncompressed etcd snapshot integrity trailer')
        remaining = info.st_size - 32
        content_hash = hashlib.sha256()
        whole_hash = hashlib.sha256()
        while remaining:
            chunk = stream.read(min(1024 * 1024, remaining))
            if not chunk:
                raise ValueError('Truncated snapshot')
            content_hash.update(chunk)
            whole_hash.update(chunk)
            remaining -= len(chunk)
        trailer = stream.read(32)
        if not hmac.compare_digest(trailer, content_hash.digest()) or stream.read(1):
            raise ValueError('Snapshot integrity trailer mismatch')
        whole_hash.update(trailer)
        return dict(size=info.st_size, sha256=whole_hash.hexdigest(), integrity_trailer_valid=True)


if __name__ == '__main__':
    try:
        print(json.dumps(verify(Path(sys.argv[1]))))
    except (OSError, ValueError, IndexError) as error:
        print('Snapshot verification failed: ' + str(error), file=sys.stderr)
        raise SystemExit(1)
