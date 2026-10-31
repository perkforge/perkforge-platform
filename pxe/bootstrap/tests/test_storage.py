"""Read-only disk guard against synthetic files; never touches a block device."""
from pathlib import Path
import hashlib
import os
import subprocess
import tempfile
import unittest
from jinja2 import Environment,StrictUndefined

TEMPLATE=Path(__file__).resolve().parents[2]/'kickstart/storage.ks.j2'

class Storage(unittest.TestCase):
    def run_guard(self, failure='', missing=False):
        with tempfile.TemporaryDirectory(prefix='perkforge-bootstrap-fixture-storage-') as folder:
            root=Path(folder);target=root/'target';target.write_bytes(b'TARGET UNCHANGED')
            canary=root/'canary';canary.write_bytes(b'CANARY UNCHANGED')
            before=[hashlib.sha256(p.read_bytes()).digest() for p in [target,canary]]
            bindir=root/'bin';bindir.mkdir()
            scripts={
                'readlink':'printf "%s\\n" "$FIX_TARGET"',
                'lsblk':'''case "$*" in *TYPE*) printf '%s\\n' "${FIX_TYPE:-disk}";; *SERIAL*) printf '%s\\n' "$FIX_SERIAL";; *) exit 99;; esac''',
                'blockdev':'printf "%s\\n" "$FIX_BYTES"'}
            for name,body in scripts.items():
                p=bindir/name;p.write_text('#!/bin/bash\nset -eu\n'+body+'\n');p.chmod(0o700)
            values=dict(storage_layout='UEFI_XFS_LVM_UNENCRYPTED',disk_stable_id='disk/by-id/virtio-FIXTURE',disk_serial='SYNTHETIC',disk_capacity_bytes=68719476736)
            if missing:values['disk_serial']='UNCONFIGURED'
            rendered=Environment(undefined=StrictUndefined).from_string(TEMPLATE.read_text()).render(**values)
            body=rendered.split('%pre ',1)[1].split('\n',1)[1].split('\n%end',1)[0]
            self.assertIn('test -b "$resolved"',body) if not missing else None
            # Fixture checks regular synthetic files; production retains test -b.
            body=body.replace('test -b "$resolved"','test -f "$resolved"')
            for program,path in [('readlink','/usr/bin/readlink'),('lsblk','/usr/bin/lsblk'),('blockdev','/usr/sbin/blockdev')]:body=body.replace(path,str(bindir/program))
            body=body.replace('/dev/console',str(root/'console'))
            script=root/'guard.sh';script.write_text(body)
            env={**os.environ,'FIX_TARGET':str(target),'FIX_SERIAL':'WRONG' if failure=='serial' else 'SYNTHETIC',
                'FIX_BYTES':'1' if failure=='capacity' else '68719476736','FIX_TYPE':'part' if failure=='partition' else 'disk'}
            result=subprocess.run(['bash',str(script)],env=env,capture_output=True,text=True,timeout=5)
            self.assertEqual(before,[hashlib.sha256(p.read_bytes()).digest() for p in [target,canary]])
            return result,rendered,body

    def test_matching_identity_read_only_guard_passes_and_directives_are_scoped(self):
        result,text,body=self.run_guard()
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertIn('ignoredisk --only-use=disk/by-id/virtio-FIXTURE',text)
        self.assertIn('clearpart --all --initlabel --drives=disk/by-id/virtio-FIXTURE',text)
        self.assertEqual(text.count('--ondisk=disk/by-id/virtio-FIXTURE'),3)
        self.assertNotIn('wipefs',body);self.assertNotIn('mkfs',body);self.assertNotIn('clearpart',body)
        self.assertNotIn('part /home',text);self.assertNotIn('logvol swap',text)

    def test_wrong_disk_metadata_fails_without_target_or_canary_writes(self):
        for failure in ['serial','capacity','partition']:
            with self.subTest(failure=failure):self.assertNotEqual(self.run_guard(failure)[0].returncode,0)

    def test_missing_metadata_has_no_active_storage_directives(self):
        result,text,_=self.run_guard(missing=True)
        self.assertNotEqual(result.returncode,0)
        self.assertNotRegex(text,r'(?m)^(ignoredisk|clearpart|bootloader|part |volgroup|logvol)')

if __name__=='__main__':unittest.main()
