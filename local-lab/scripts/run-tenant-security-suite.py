#!/usr/bin/env python3
"""Orchestrate tenant security verifiers and write a suite-level evidence index.

Plan-only by default. Use --apply to run the selected checks against a live
cluster. Network and observability suites create temporary probe resources and
remove only resources carrying their unique run label; admission and quota use
server-side dry-run requests; RBAC performs read-only authorization checks.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SUITES = {
    "rbac": ("verify-tenant-rbac.py", False),
    "admission": ("verify-tenant-admission.py", True),
    "quota": ("verify-tenant-quota.py", True),
    "network": ("verify-tenant-network.py", True),
    "observability": ("verify-tenant-observability.py", True),
}
DEFAULT_SUITES = ("rbac", "admission", "quota", "network")


def display_path(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def build_command(name: str, apply: bool, kubectl: str, kubeconfig: str,
                  context: str | None, output_dir: Path) -> list[str]:
    script, supports_apply = SUITES[name]
    command = [sys.executable, str(ROOT / "local-lab/scripts" / script),
               "--kubectl", kubectl, "--kubeconfig", kubeconfig,
               "--output-dir", str(output_dir)]
    if context:
        command += ["--context", context]
    if apply and supports_apply:
        command.append("--apply")
    return command


def write_summary(run_dir: Path, started: dt.datetime, finished: dt.datetime,
                  apply: bool, context: str | None, results: list[dict]) -> tuple[Path, Path]:
    data = {
        "schemaVersion": "perkforge.security-evidence/v1alpha1",
        "testSuite": "tenant-security-suite",
        "startedAt": started.isoformat().replace("+00:00", "Z"),
        "finishedAt": finished.isoformat().replace("+00:00", "Z"),
        "mode": "live" if apply else "plan-only",
        "requestedContext": context,
        "summary": {
            "total": len(results),
            "passed": sum(item["status"] == "passed" for item in results),
            "failed": sum(item["status"] == "failed" for item in results),
            "errors": sum(item["status"] == "error" for item in results),
        },
        "results": results,
        "limitations": [
            "This index summarizes verifier runs; each suite report is the detailed evidence record.",
            "RBAC checks use Kubernetes impersonation and do not prove browser SSO or Rancher UI behavior.",
            "Admission and quota requests use API server-side dry-run; they are not persisted or runtime tests.",
        ],
    }
    json_path = run_dir / "summary.json"
    md_path = run_dir / "summary.md"
    json_path.write_text(json.dumps(data, indent=2) + "\n")
    lines = ["# Tenant security test suite", "",
             f"- Mode: **{data['mode']}**",
             f"- Started: `{data['startedAt']}`",
             f"- Finished: `{data['finishedAt']}`",
             f"- Requested context: `{context or 'verifier default'}`",
             f"- Summary: **{data['summary']['passed']} passed, {data['summary']['failed']} failed, {data['summary']['errors']} errors**", "",
             "| Suite | Status | Exit code | Detailed evidence |", "|---|---|---:|---|"]
    for item in results:
        detail = item.get("evidenceDirectory", "—")
        lines.append(f"| `{item['suite']}` | {item['status']} | {item['exitCode']} | `{detail}` |")
    lines += ["", "Individual JSON/Markdown reports reside in each suite's evidence directory.",
              "A plan-only run makes no Kubernetes API requests.", ""]
    md_path.write_text("\n".join(lines))
    return json_path, md_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true",
                        help="run selected checks against the live cluster")
    parser.add_argument("--suite", choices=tuple(SUITES), action="append",
                        help="suite to include (repeatable; defaults to RBAC, admission, quota, network)")
    parser.add_argument("--include-observability", action="store_true",
                        help="include the optional observability suite")
    parser.add_argument("--kubectl", default=str(ROOT / ".secrets/kubectl"))
    parser.add_argument("--kubeconfig", default=str(ROOT / ".secrets/rke2.yaml"))
    parser.add_argument("--context")
    parser.add_argument("--output-root", type=Path, default=ROOT / "local-lab/evidence/tenant-suite")
    args = parser.parse_args()
    suites = list(dict.fromkeys(args.suite or DEFAULT_SUITES))
    if args.include_observability and "observability" not in suites:
        suites.append("observability")

    started = dt.datetime.now(dt.timezone.utc)
    stamp = started.strftime("%Y%m%dT%H%M%S%fZ")
    run_dir = args.output_root / f"tenant-suite-{stamp}"
    if not args.apply:
        print("Plan only; no Kubernetes API requests made and no evidence files written.")
        print("Selected suites: " + ", ".join(suites))
        print("Live mode runs read-only RBAC checks, API-server dry-runs for admission/quota, "
              "and creates then cleans up temporary network/optional observability probes.")
        print("Re-run with --apply to execute and write timestamped evidence.")
        return 0

    run_dir.mkdir(mode=0o700, parents=True, exist_ok=False)
    results = []
    for name in suites:
        suite_dir = run_dir / name
        command = build_command(name, True, args.kubectl, args.kubeconfig,
                                args.context, suite_dir)
        print(f"\n=== Running {name} ===", flush=True)
        try:
            completed = subprocess.run(command, text=True, capture_output=True)
            if completed.stdout:
                print(completed.stdout, end="")
            if completed.stderr:
                print(completed.stderr, end="", file=sys.stderr)
            status = "passed" if completed.returncode == 0 else (
                "failed" if completed.returncode == 1 else "error")
            results.append({"suite": name, "status": status,
                            "exitCode": completed.returncode,
                            "evidenceDirectory": display_path(suite_dir)})
        except OSError as exc:
            print(f"Could not start {name} verifier: {exc}", file=sys.stderr)
            results.append({"suite": name, "status": "error", "exitCode": 127,
                            "detail": "verifier could not be started",
                            "evidenceDirectory": display_path(suite_dir)})

    finished = dt.datetime.now(dt.timezone.utc)
    json_path, md_path = write_summary(run_dir, started, finished, True, args.context, results)
    print(f"\nSuite summary: {display_path(json_path)}")
    print(f"Human-readable summary: {display_path(md_path)}")
    counts = json.loads(json_path.read_text())["summary"]
    print(f"Overall: {counts['passed']} passed, {counts['failed']} failed, {counts['errors']} errors")
    return 2 if counts["errors"] else (1 if counts["failed"] else 0)


if __name__ == "__main__":
    raise SystemExit(main())
