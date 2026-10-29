"""Download integrity-pinned public TEST fixtures, never cluster configuration."""
import hashlib
from pathlib import Path
import subprocess
import sys
import urllib.request

import yaml

sources = yaml.safe_load((Path(__file__).resolve().parents[1] / 'tests/fixtures/source-pins.yaml').read_text())
root = Path(sys.argv[1]).resolve()
(root / '.archives').mkdir(parents=True, exist_ok=True)
for name, source in sources.items():
    archive = root / '.archives' / (name + '.tgz')
    if not archive.exists():
        with urllib.request.urlopen(source['url'], timeout=45) as response:
            archive.write_bytes(response.read())
    assert hashlib.sha256(archive.read_bytes()).hexdigest() == source['sha256'], name
    target = root / name
    target.mkdir(exist_ok=True)
    subprocess.run(['tar', '-xzf', str(archive), '-C', str(target), '--strip-components=1'], check=True)
    assert (target / source['chart'] / 'Chart.yaml').is_file(), name
    print(name + ': verified pinned test artifact')
