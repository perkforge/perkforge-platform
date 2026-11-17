import os,subprocess,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
CLI=ROOT/'configuration/tenant-runner/setup/check-custody-files.py'
class Paths(unittest.TestCase):
 def test_private_paths_and_reject_links(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);p.chmod(0o700);files=[]
   for i in range(3):
    f=p/str(i);f.write_text('synthetic');f.chmod(0o600);files.append(str(f))
   def check():return subprocess.run(['python3',str(CLI),*files],capture_output=True).returncode
   self.assertEqual(check(),0)
   Path(files[0]).chmod(0o644);self.assertNotEqual(check(),0);Path(files[0]).chmod(0o600)
   os.link(files[0],p/'link');self.assertNotEqual(check(),0);(p/'link').unlink()
   p.chmod(0o755);self.assertNotEqual(check(),0);p.chmod(0o700)
if __name__=='__main__':unittest.main()
