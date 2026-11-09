"""Inspect downloaded bytes, not just navigation. Not a general secret scanner."""
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent.parent
META = json.loads((ROOT / "audiences.json").read_text())
OPERATOR_MARKERS = ["production_pki", "workstation_detail", "bootstrap_installer_flow"]


def verify_bundle(output, audience):
    if not (output / "index.html").is_file():
        raise ValueError(f"{audience}: missing build index")
    chunks = []
    for path in output.rglob("*"):
        if path.is_symlink():
            raise ValueError(f"{audience}: symlink in browser payload")
        if path.is_file():
            if "sources" in path.relative_to(output).parts or path.name == "runbook.html":
                raise ValueError(f"{audience}: operator source asset in browser payload")
            chunks.append(path.read_bytes())
    payload = b"\n".join(chunks)
    for view in META["bundles"][audience]["views"]:
        if view.encode() not in payload:
            raise ValueError(f"{audience}: missing expected view {view}")
    forbidden = list(OPERATOR_MARKERS)
    for other, bundle in META["bundles"].items():
        if other != audience:
            forbidden.extend(bundle["views"])
    for marker in forbidden:
        if marker.encode() in payload:
            raise ValueError(f"{audience}: other-audience marker {marker} in browser payload")
    if re.search(rb"/home/|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----", payload):
        raise ValueError(f"{audience}: private-path/key marker in browser payload")
    return len(chunks)


if __name__ == "__main__":
    for audience in META["bundles"]:
        count = verify_bundle(ROOT / ("dist-" + audience), audience)
        print(f"{audience}: {count} files inspected; expected views present, no other-audience markers/assets")
