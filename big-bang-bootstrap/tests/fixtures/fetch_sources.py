"""Download integrity-pinned public TEST fixtures, never cluster configuration."""
import hashlib
import http.client
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request

import yaml


def transient(error):
    if isinstance(error, urllib.error.HTTPError):
        return error.code in (500, 502, 503, 504)
    reason = error.reason if isinstance(error, urllib.error.URLError) else error
    return (isinstance(reason, (TimeoutError, ConnectionError, http.client.IncompleteRead))
            or isinstance(reason, socket.gaierror) and reason.errno == socket.EAI_AGAIN)


def fetch_archive(name, source, root, *, open_url=urllib.request.urlopen, sleep=time.sleep):
    archives = root / '.archives'
    archives.mkdir(parents=True, exist_ok=True)
    archive = archives / (name + '.tgz')
    if archive.exists():
        if hashlib.sha256(archive.read_bytes()).hexdigest() != source['sha256']:
            raise ValueError(name + ': cached checksum mismatch; stop without replacing it')
        return archive
    for attempt in range(1, 4):
        print(f"{name}: fetching {source['url']} (attempt {attempt}/3)", flush=True)
        try:
            with open_url(source['url'], timeout=45) as response:
                data = response.read()
        except (urllib.error.URLError, TimeoutError, ConnectionError,
                http.client.IncompleteRead, socket.gaierror) as error:
            label = f'HTTP {error.code}' if isinstance(error, urllib.error.HTTPError) else type(error).__name__
            print(f'{name}: download failed ({label})', flush=True)
            if isinstance(error, urllib.error.HTTPError):
                error.close()
            if not transient(error) or attempt == 3:
                raise
            sleep((2, 5)[attempt - 1])
            continue
        if hashlib.sha256(data).hexdigest() != source['sha256']:
            raise ValueError(name + ': downloaded checksum mismatch; no retry or cache promotion')
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(dir=archives, prefix='.' + name + '-', delete=False) as output:
                temporary = Path(output.name)
                output.write(data)
            temporary.replace(archive)
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
        return archive


def main(root):
    sources = yaml.safe_load((Path(__file__).resolve().parent / 'source-pins.yaml').read_text())
    for name, source in sources.items():
        archive = fetch_archive(name, source, root)
        target = root / name
        target.mkdir(exist_ok=True)
        subprocess.run(['tar', '-xzf', str(archive), '-C', str(target), '--strip-components=1'], check=True)
        if not (target / source['chart'] / 'Chart.yaml').is_file():
            raise ValueError(name + ': expected chart is absent after verified extraction')
        print(name + ': verified pinned test artifact', flush=True)


if __name__ == '__main__':
    main(Path(sys.argv[1]).resolve())
