"""Source-package tests: no network, patch application, build or deployment."""
import importlib.util
import pathlib
import shutil
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location('collector_verify', ROOT / 'verify.py')
VERIFY = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VERIFY)

class Integrity(unittest.TestCase):
    def test_exact_package(self):
        self.assertFalse(VERIFY.verify()['image_published'])

    def test_tampering_denied(self):
        for name in ('snapshot.patch', 'LICENSE.upstream', 'source.json'):
            with self.subTest(name=name), tempfile.TemporaryDirectory() as d:
                root = pathlib.Path(d)
                for filename in ('snapshot.patch', 'LICENSE.upstream', 'source.json'):
                    shutil.copyfile(ROOT / filename, root / filename)
                p = root / name
                if name == 'source.json':
                    p.write_text(p.read_text().replace('c50ef849', '00000000'))
                else:
                    p.write_bytes(p.read_bytes() + b'changed')
                with self.assertRaises((AssertionError, ValueError)):
                    VERIFY.verify(root)

if __name__ == '__main__':
    unittest.main()
