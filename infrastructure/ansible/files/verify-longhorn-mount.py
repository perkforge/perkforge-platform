#!/usr/bin/python3
"""Verify an existing dedicated filesystem; never generate configuration."""
import argparse
import array
import errno
import fcntl
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import uuid

OPTIONS = 'rw,noatime,nosuid,nodev,nofail,x-systemd.device-timeout=15s,x-systemd.device-bound'


def require(condition, message):
    if not condition:
        raise ValueError(message)


def command(*args):
    return subprocess.check_output(args, text=True, stderr=subprocess.PIPE).strip()


def validate_fstab(text, spec, marker_exists, device=None):
    expected = [f'UUID={spec.uuid}', spec.path, 'xfs', OPTIONS, '0', '0']
    begin = f'# BEGIN PerkForge Longhorn {spec.path}'
    end = f'# END PerkForge Longhorn {spec.path}'
    matches = []
    for line in text.splitlines():
        fields = line.split()
        if not fields or fields[0].startswith('#'):
            continue
        same_device = fields[0] in (expected[0], 'LABEL=' + spec.label)
        if device is not None and fields[0].startswith('/dev/'):
            same_device = same_device or Path(fields[0]).resolve() == device
        if same_device or (len(fields) > 1 and fields[1] == spec.path):
            matches.append(fields)
    require(not matches or (marker_exists and matches == [expected]),
            'Conflicting or unmanaged fstab entry')
    if matches:
        block = begin + '\n' + ' '.join(expected) + '\n' + end
        require(block in text and text.splitlines().count(begin) == 1 and
                text.splitlines().count(end) == 1, 'Expected fstab entry is outside its unique managed block')
    else:
        require(begin not in text and end not in text, 'Orphaned fstab management marker')


def validate_mounts(mounts, path, number):
    relevant = [m for m in mounts if m['target'] == path or
                m['target'].startswith(path + '/') or m['maj:min'] == number]
    require(not relevant or (len(relevant) == 1 and relevant[0]['target'] == path and
            relevant[0]['maj:min'] == number and relevant[0]['fstype'] == 'xfs' and
            {'rw', 'noatime', 'nosuid', 'nodev'} <= set(relevant[0]['options'].split(','))),
            'Unexpected mount, filesystem or runtime options')
    return bool(relevant)


def secure_file(path, mode=None):
    s = path.lstat()
    require(stat.S_ISREG(s.st_mode) and s.st_uid == 0 and not s.st_mode & 0o022,
            'Configuration file must be root-owned, regular and protected')
    if mode is not None:
        require(stat.S_IMODE(s.st_mode) == mode, 'Unexpected marker permissions')


def validate_guard_identity(marker, root_filesystem_uuid, inode, immutable):
    require(marker['root_filesystem_uuid'] == root_filesystem_uuid and
            marker['root_inode'] == inode and immutable,
            'Underlying guard filesystem, inode or immutable flag changed')


def root_filesystem_identity():
    """Probe the currently mounted root; persist its UUID, never its device number."""
    root_device = os.stat('/').st_dev
    device = Path('/dev/block', f'{os.major(root_device)}:{os.minor(root_device)}').resolve(strict=True)
    require(stat.S_ISBLK(device.stat().st_mode) and device.stat().st_rdev == root_device,
            'Root must be an identifiable block filesystem')
    attrs = dict(line.split('=', 1) for line in command('blkid', '-p', '-o', 'export', str(device)).splitlines() if '=' in line)
    require(attrs.get('TYPE') == 'xfs', 'Expected XFS root filesystem')
    root_uuid = attrs.get('UUID', '')
    require(str(uuid.UUID(root_uuid)) == root_uuid, 'Root filesystem UUID is unavailable or invalid')
    return root_uuid


def inspect_guard(path, root_filesystem_uuid, marker=None, prove=False, root_device=None):
    guard = dict(exists=False, immutable=False)
    root_device = os.stat('/').st_dev if root_device is None else root_device
    if path.exists() or path.is_symlink():
        ps = path.lstat()
        require(stat.S_ISDIR(ps.st_mode) and ps.st_uid == 0 and stat.S_IMODE(ps.st_mode) == 0o700 and
                ps.st_dev == root_device and not any(path.iterdir()),
                'Underlying directory must be empty, root-owned 0700 and on root filesystem')
    # Direct directory fd avoids following a substituted leaf symlink.
    if path.exists():
        fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            flags = array.array('L', [0])
            fcntl.ioctl(fd, 0x80086601, flags, True)  # FS_IOC_GETFLAGS, x86_64
            ps = os.fstat(fd)
            guard = dict(exists=True, immutable=bool(flags[0] & 0x10),
                         root_filesystem_uuid=root_filesystem_uuid, inode=ps.st_ino)
            if marker:
                validate_guard_identity(marker, root_filesystem_uuid, ps.st_ino, guard['immutable'])
            if prove:
                require(guard['immutable'], 'Immutable flag absent')
                probe = '.perkforge-guard-' + uuid.uuid4().hex
                try:
                    probe_fd = os.open(probe, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600, dir_fd=fd)
                except OSError as e:
                    require(e.errno == errno.EPERM, 'Guard probe failed for an unexpected reason')
                else:
                    os.close(probe_fd)
                    os.unlink(probe, dir_fd=fd)
                    raise ValueError('Root write unexpectedly succeeded; guard not proven')
        finally:
            os.close(fd)
    require(not prove or guard["exists"], "Guard proof requires an existing directory")
    require(not marker or guard['exists'], 'Recorded underlying guard directory is missing')
    return guard


def inspect(spec):
    require(os.geteuid() == 0, 'Run through reviewed Ansible become')
    require(re.fullmatch(r'/mnt/[A-Za-z0-9_-]+', spec.path), 'Invalid mount path')
    require(str(uuid.UUID(spec.uuid)) == spec.uuid, 'Invalid UUID')
    for tool in ('blkid', 'findmnt', 'chattr', 'lsattr', 'mount'):
        require(shutil.which(tool), 'Required host utility unavailable: ' + tool)
    root_uuid = root_filesystem_identity()
    path = Path(spec.path)
    parent = path.parent.lstat()
    require(stat.S_ISDIR(parent.st_mode) and parent.st_uid == 0 and
            not parent.st_mode & 0o022 and parent.st_dev == os.stat('/').st_dev,
            'Mount parent must be protected and on root filesystem')
    device = Path('/dev/disk/by-uuid', spec.uuid).resolve(strict=True)
    ds = device.stat()
    require(stat.S_ISBLK(ds.st_mode), 'UUID does not resolve to block device')
    identities = command('blkid', '-c', '/dev/null', '-t', 'UUID=' + spec.uuid, '-o', 'device').splitlines()
    require(len(identities) == 1 and Path(identities[0]).resolve() == device,
            'Filesystem UUID must identify exactly one device')
    sysdev = Path('/sys/dev/block', f'{os.major(ds.st_rdev)}:{os.minor(ds.st_rdev)}').resolve(strict=True)
    require((sysdev / 'partition').exists(), 'Expected a partition')
    disk = sysdev.parent
    require(int((disk / 'size').read_text()) * 512 == spec.bytes, 'Raw device capacity mismatch')
    usb = next((p for p in disk.parents if (p / 'idVendor').exists() and (p / 'serial').exists()), None)
    require(usb is not None and (usb / 'serial').read_text().strip() == spec.serial,
            'USB descriptor serial mismatch')
    attrs = dict(line.split('=', 1) for line in command('blkid', '-p', '-o', 'export', str(device)).splitlines() if '=' in line)
    require(all(attrs.get(k) == v for k, v in {'TYPE': 'xfs', 'UUID': spec.uuid, 'LABEL': spec.label}.items()),
            'Filesystem identity mismatch')
    mounts = json.loads(command('findmnt', '--json', '--list', '--output', 'TARGET,FSTYPE,MAJ:MIN,OPTIONS'))['filesystems']
    number = f'{os.major(ds.st_rdev)}:{os.minor(ds.st_rdev)}'
    mounted = validate_mounts(mounts, spec.path, number)
    marker_path = Path('/etc/perkforge/longhorn-mounts', path.name + '.json')
    for p in (Path('/etc/perkforge'), marker_path.parent):
        if p.exists() or p.is_symlink():
            ps = p.lstat()
            require(stat.S_ISDIR(ps.st_mode) and ps.st_uid == 0 and not ps.st_mode & 0o077,
                    'Unsafe marker parent')
    marker = None
    if marker_path.exists() or marker_path.is_symlink():
        secure_file(marker_path, 0o600)
        marker = json.loads(marker_path.read_text())
        expected = dict(version=2, uuid=spec.uuid, serial=spec.serial, label=spec.label,
                        bytes=spec.bytes, path=spec.path, immutable_verified=True,
                        root_filesystem_uuid=root_uuid)
        require(all(marker.get(k) == v for k, v in expected.items()), 'Guard marker identity mismatch')
        require(type(marker.get('root_inode')) is int and marker['root_inode'] > 0,
                'Invalid guard inode evidence')
    secure_file(Path('/etc/fstab'))
    validate_fstab(Path('/etc/fstab').read_text(), spec, marker is not None, device)
    guard = dict(exists=False, immutable=False)
    if mounted:
        require(marker is not None, 'Mounted filesystem lacks prior root-directory guard evidence')
        require(os.stat(path).st_dev == ds.st_rdev, 'Mounted path device mismatch')
    else:
        guard = inspect_guard(path, root_uuid, marker, spec.prove_guard)
    require(not spec.prove_guard or (not mounted and guard['exists']), 'Guard proof requires unmounted directory')
    require(not spec.require_mounted or mounted, 'Expected filesystem is not mounted')
    result = dict(mounted=mounted, guard=guard)
    if mounted:
        fs = os.statvfs(path)
        result.update(filesystem_capacity_bytes=fs.f_blocks * fs.f_frsize, available_bytes=fs.f_bavail * fs.f_frsize)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for arg in ('uuid', 'serial', 'label', 'path'):
        parser.add_argument('--' + arg, required=True)
    parser.add_argument('--bytes', type=int, required=True)
    parser.add_argument('--prove-guard', action='store_true')
    parser.add_argument('--require-mounted', action='store_true')
    try:
        print(json.dumps(inspect(parser.parse_args())))
    except (ValueError, OSError, subprocess.SubprocessError, KeyError) as error:
        raise SystemExit('Verification stopped: ' + str(error))
