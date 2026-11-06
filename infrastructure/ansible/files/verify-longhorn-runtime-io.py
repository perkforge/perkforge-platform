#!/usr/bin/python3
"""Bounded SSD I/O verification inside an existing privileged Longhorn manager."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import stat
import subprocess
import uuid

SIZE = 16 * 1024 * 1024


def require(condition, message):
    if not condition:
        raise ValueError(message)


def probe(root_fd, expected_device):
    """Use anchored directory descriptors; remove only this invocation's entries."""
    require(os.fstat(root_fd).st_dev == expected_device, 'Mounted device changed')
    name = '.pf-ssd-acceptance-' + secrets.token_hex(12)
    os.mkdir(name, 0o700, dir_fd=root_fd)
    directory_fd = None
    created = False
    try:
        directory_fd = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=root_fd)
        require(os.fstat(directory_fd).st_dev == expected_device, 'Probe directory device mismatch')
        fd = os.open('probe.bin', os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                     0o600, dir_fd=directory_fd)
        created = True
        expected = hashlib.sha256()
        with os.fdopen(fd, 'wb') as output:
            for _ in range(16):
                chunk = os.urandom(1024 * 1024)
                output.write(chunk)
                expected.update(chunk)
            output.flush()
            os.fsync(output.fileno())
        os.fsync(directory_fd)
        actual = hashlib.sha256()
        count = 0
        fd = os.open('probe.bin', os.O_RDONLY | os.O_NOFOLLOW, dir_fd=directory_fd)
        with os.fdopen(fd, 'rb') as source:
            while True:
                chunk = source.read(1024 * 1024)
                if not chunk:
                    break
                actual.update(chunk)
                count += len(chunk)
        require(count == SIZE and actual.digest() == expected.digest(), 'Probe checksum or size mismatch')
        return dict(verified_bytes=count, checksum_match=True)
    finally:
        if directory_fd is not None:
            try:
                if created:
                    os.unlink('probe.bin', dir_fd=directory_fd)
                    os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
        os.rmdir(name, dir_fd=root_fd)
        os.fsync(root_fd)


def inspect(args):
    require(not args.apply or args.reviewed, 'Explicit review is required for I/O')
    require(re.fullmatch(r'/mnt/[A-Za-z0-9_-]+', args.path), 'Invalid host path')
    require(str(uuid.UUID(args.uuid)) == args.uuid, 'Invalid filesystem UUID')
    require(re.fullmatch(r'[A-Za-z0-9_-]{1,12}', args.label), 'Invalid filesystem label')
    require(os.geteuid() == 0, 'Expected the privileged manager user')
    context = Path('/proc/self/attr/current').read_bytes().split(b'\0', 1)[0].decode().strip()
    require(context == 'system_u:system_r:spc_t:s0', 'Expected actual spc_t runtime context')
    # Do not Path.resolve() a procfs magic link: let the kernel follow host PID 1's root.
    target = '/host/proc/1/root' + args.path
    require(stat.S_ISDIR(os.lstat(target).st_mode), 'Host target must be a real directory')
    block = Path('/host/dev/disk/by-uuid', args.uuid).resolve(strict=True)
    bs = block.stat()
    require(stat.S_ISBLK(bs.st_mode), 'Expected a block-device UUID link')
    output = subprocess.check_output(['blkid', '-p', '-o', 'export', str(block)], universal_newlines=True)
    identity = dict(line.split('=', 1) for line in output.splitlines() if '=' in line)
    require(all(identity.get(k) == v for k, v in
                {'TYPE': 'xfs', 'UUID': args.uuid, 'LABEL': args.label}.items()), 'Filesystem identity mismatch')
    root_fd = os.open(target, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        require(os.fstat(root_fd).st_dev == bs.st_rdev, 'Host path is not the expected SSD')
        require(os.fstat(root_fd).st_dev != os.stat('/host/proc/1/root').st_dev,
                'Refusing host root filesystem')
        require(not os.listdir(root_fd), 'SSD is not empty; do not test a registered or occupied disk')
        result = dict(mode='inspect', context=context, mounted_identity_verified=True)
        if args.apply:
            result.update(probe(root_fd, bs.st_rdev), mode='io', cleanup_complete=True)
        return result
    finally:
        os.close(root_fd)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ('path', 'uuid', 'label'):
        parser.add_argument('--' + key, required=True)
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--reviewed', action='store_true')
    try:
        print(json.dumps(inspect(parser.parse_args())))
    except (ValueError, OSError, subprocess.SubprocessError) as error:
        raise SystemExit('Runtime I/O acceptance stopped: ' + str(error))
