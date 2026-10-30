#!/usr/bin/env python3
"""Maintain a private, reviewable register of tenant security findings."""
from __future__ import annotations

import argparse
import datetime as dt
import fcntl
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REGISTER = ROOT / ".secrets/security-findings-register.json"
SCHEMA_VERSION = "perkforge.security-findings-register/v1alpha1"
STATUSES = {
    "candidate", "triage", "confirmed", "risk-assessed",
    "remediation-planned", "in-progress", "retest", "accepted",
    "dismissed", "closed",
}
TRANSITIONS = {
    "candidate": {"triage", "dismissed"},
    "triage": {"confirmed", "dismissed"},
    "confirmed": {"risk-assessed"},
    "risk-assessed": {"remediation-planned", "accepted"},
    "remediation-planned": {"in-progress"},
    "in-progress": {"retest"},
    "retest": {"in-progress", "closed"},
    "accepted": {"remediation-planned"},
    "dismissed": set(),
    "closed": {"in-progress"},
}


class RegisterError(ValueError):
    """Raised for an invalid register operation."""


def now_utc() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")


def parse_date(value: str, field: str) -> dt.date:
    try:
        return dt.date.fromisoformat(value)
    except (TypeError, ValueError) as exc:
        raise RegisterError(f"{field} must be an ISO date (YYYY-MM-DD)") from exc


def empty_register() -> dict:
    timestamp = now_utc()
    return {"schemaVersion": SCHEMA_VERSION, "createdAt": timestamp,
            "updatedAt": timestamp, "findings": []}


def validate_register(register: dict) -> None:
    if not isinstance(register, dict) or register.get("schemaVersion") != SCHEMA_VERSION:
        raise RegisterError(f"register must use schemaVersion {SCHEMA_VERSION}")
    if not isinstance(register.get("findings"), list):
        raise RegisterError("register findings must be a list")
    ids, source_keys = set(), set()
    for item in register["findings"]:
        if not isinstance(item, dict):
            raise RegisterError("each finding must be an object")
        for key in ("findingId", "status", "sourceKey", "history"):
            if key not in item:
                raise RegisterError(f"finding is missing {key}")
        if item["findingId"] in ids:
            raise RegisterError(f"duplicate findingId: {item['findingId']}")
        if item["sourceKey"] in source_keys:
            raise RegisterError(f"duplicate sourceKey: {item['sourceKey']}")
        if item["status"] not in STATUSES:
            raise RegisterError(f"invalid status for {item['findingId']}: {item['status']}")
        if not isinstance(item["history"], list) or not item["history"]:
            raise RegisterError(f"{item['findingId']} must have a non-empty history")
        ids.add(item["findingId"])
        source_keys.add(item["sourceKey"])


def load_register(path: Path) -> dict:
    if not path.exists():
        return empty_register()
    if path.stat().st_mode & 0o077:
        raise RegisterError(f"register permissions are too broad; restrict {path} to owner-only access (0600)")
    try:
        data = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise RegisterError(f"cannot read valid JSON register at {path}") from exc
    validate_register(data)
    return data


def source_key(artifact: str, candidate: dict) -> str:
    value = json.dumps({"artifact": artifact, "candidate": candidate},
                       sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(value.encode()).hexdigest()


def next_finding_id(register: dict, year: int) -> str:
    prefix = f"PF-{year}-"
    numbers = [int(item["findingId"].rsplit("-", 1)[1])
               for item in register["findings"]
               if item["findingId"].startswith(prefix)
               and item["findingId"].rsplit("-", 1)[1].isdigit()]
    return f"{prefix}{max(numbers, default=0) + 1:04d}"


def import_candidates(register: dict, candidate_file: Path) -> list[str]:
    validate_register(register)
    try:
        payload = json.loads(candidate_file.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise RegisterError(f"cannot read candidate file: {candidate_file}") from exc
    if payload.get("schemaVersion") != "perkforge.security-findings/v1alpha1":
        raise RegisterError("input is not a supported PerkForge candidate-findings file")
    candidates = payload.get("findings")
    if not isinstance(candidates, list):
        raise RegisterError("candidate file findings must be a list")

    artifact = candidate_file.as_posix()
    existing = {item["sourceKey"] for item in register["findings"]}
    imported = []
    for candidate in candidates:
        if not isinstance(candidate, dict) or candidate.get("status") != "untriaged":
            raise RegisterError("only untriaged candidate records can be imported")
        key = source_key(artifact, candidate)
        if key in existing:
            continue
        identifier = next_finding_id(register, dt.datetime.now(dt.timezone.utc).year)
        record = {
            "findingId": identifier,
            "status": "candidate",
            "title": candidate.get("title", "Untitled candidate"),
            "sourceKey": key,
            "sourceCandidate": {
                "candidateId": candidate.get("findingId"),
                "artifact": artifact,
                "evidenceArtifact": candidate.get("evidenceArtifact"),
                "testSuite": candidate.get("testSuite"),
                "testId": candidate.get("testId"),
                "observedAt": candidate.get("observedAt"),
                "target": candidate.get("target", {}),
                "expected": candidate.get("expected"),
                "actual": candidate.get("actual"),
                "potentialControlIds": candidate.get("potentialControlIds", []),
            },
            "risk": {"status": "unassessed"},
            "remediation": {"status": "unassigned"},
            "history": [{
                "timestamp": now_utc(), "from": None, "to": "candidate",
                "actor": "candidate-import", "rationale": "Imported from verifier output; human triage required.",
            }],
        }
        register["findings"].append(record)
        existing.add(key)
        imported.append(identifier)
    register["updatedAt"] = now_utc()
    validate_register(register)
    return imported


def transition(register: dict, finding_id: str, target: str, *, actor: str,
               rationale: str, impact_rationale: str | None = None,
               likelihood_rationale: str | None = None,
               residual_risk_rationale: str | None = None,
               owner: str | None = None,
               due_date: str | None = None, decision_authority: str | None = None,
               accepted_until: str | None = None, evidence: str | None = None,
               retest_result: str | None = None) -> None:
    validate_register(register)
    if target not in STATUSES:
        raise RegisterError(f"invalid target status: {target}")
    if not actor.strip() or not rationale.strip():
        raise RegisterError("actor and rationale are required for every transition")
    finding = next((item for item in register["findings"]
                    if item["findingId"] == finding_id), None)
    if finding is None:
        raise RegisterError(f"unknown finding: {finding_id}")
    previous = finding["status"]
    if target not in TRANSITIONS[previous]:
        raise RegisterError(f"transition {previous} -> {target} is not allowed")

    event_details = {}
    if target == "risk-assessed":
        if not impact_rationale or not impact_rationale.strip():
            raise RegisterError("impact rationale is required before risk assessment")
        if not likelihood_rationale or not likelihood_rationale.strip():
            raise RegisterError("likelihood rationale is required before risk assessment")
        if not residual_risk_rationale or not residual_risk_rationale.strip():
            raise RegisterError("residual-risk rationale is required before risk assessment")
        finding["risk"].update({"status": "assessed", "assessedAt": now_utc(),
                                 "assessor": actor,
                                 "impactRationale": impact_rationale,
                                 "likelihoodRationale": likelihood_rationale,
                                 "residualRiskRationale": residual_risk_rationale,
                                 "decision": "pending"})
        event_details["riskAssessment"] = {
            "impactRationale": impact_rationale,
            "likelihoodRationale": likelihood_rationale,
            "residualRiskRationale": residual_risk_rationale,
        }
    if target == "remediation-planned":
        if not owner or not owner.strip():
            raise RegisterError("remediation owner is required")
        if not due_date:
            raise RegisterError("remediation due date is required")
        parse_date(due_date, "remediation due date")
        if previous == "accepted":
            expiry = finding.get("risk", {}).get("acceptedUntil")
            if not expiry or parse_date(expiry, "accepted-until date") > dt.date.today():
                raise RegisterError("accepted risk may be reopened only after its review/expiry date")
        finding["remediation"].update({"status": "planned", "owner": owner,
                                       "dueDate": due_date})
        finding["risk"]["decision"] = "remediate"
        event_details["remediation"] = {"owner": owner, "dueDate": due_date}
    if target == "accepted":
        if not decision_authority or not decision_authority.strip():
            raise RegisterError("authorized decision maker is required for risk acceptance")
        if not accepted_until:
            raise RegisterError("risk acceptance review/expiry date is required")
        expiry = parse_date(accepted_until, "accepted-until date")
        if expiry <= dt.date.today():
            raise RegisterError("risk acceptance review/expiry date must be in the future")
        finding["risk"].update({"status": "accepted", "decision": "accept",
                                 "decisionAuthority": decision_authority,
                                 "acceptedUntil": accepted_until,
                                 "decisionAt": now_utc()})
        event_details["riskAcceptance"] = {
            "decisionAuthority": decision_authority,
            "acceptedUntil": accepted_until,
        }
    if target == "retest":
        if not evidence or not evidence.strip():
            raise RegisterError("implementation/change evidence is required before retest")
        finding["retest"] = {"implementationEvidence": evidence,
                              "result": "pending"}
        event_details["implementationEvidence"] = evidence
    if target == "closed":
        if retest_result != "pass":
            raise RegisterError("closure requires a passing retest")
        if not evidence or not evidence.strip():
            raise RegisterError("closure requires a retest evidence reference")
        finding["retest"].update({"result": "pass", "evidence": evidence,
                                  "testedAt": now_utc(), "reviewer": actor})
        event_details["retest"] = {"result": "pass", "evidence": evidence}
    if target == "in-progress" and previous == "retest":
        if retest_result != "fail":
            raise RegisterError("failed retest must be recorded before returning to in-progress")
        if not evidence or not evidence.strip():
            raise RegisterError("failed retest requires an evidence reference")
        finding["retest"].update({"result": "fail", "evidence": evidence,
                                  "testedAt": now_utc(), "reviewer": actor})
        finding["remediation"]["status"] = "in-progress"
        event_details["retest"] = {"result": "fail", "evidence": evidence}
    if target == "in-progress" and previous == "closed":
        if retest_result != "fail" or not evidence or not evidence.strip():
            raise RegisterError("reopening a closed finding requires a failed retest and evidence reference")
        finding["retest"].update({"result": "fail", "evidence": evidence,
                                  "testedAt": now_utc(), "reviewer": actor})
        finding["remediation"]["status"] = "in-progress"
        event_details["retest"] = {"result": "fail", "evidence": evidence,
                                   "reopenedAfterClosure": True}
    if target == "in-progress" and previous == "remediation-planned":
        finding["remediation"]["status"] = "in-progress"
    if target == "dismissed":
        finding["review"] = {"disposition": "dismissed", "reviewer": actor,
                              "reviewedAt": now_utc(), "rationale": rationale}
    if target == "confirmed":
        finding["review"] = {"disposition": "confirmed", "reviewer": actor,
                              "reviewedAt": now_utc(), "rationale": rationale}
    if target == "triage":
        finding["review"] = {"disposition": "in-review", "reviewer": actor,
                              "reviewedAt": now_utc(), "rationale": rationale}

    finding["status"] = target
    finding["history"].append({"timestamp": now_utc(), "from": previous,
                               "to": target, "actor": actor,
                               "rationale": rationale, **event_details})
    register["updatedAt"] = now_utc()
    validate_register(register)


def write_register(path: Path, register: dict) -> None:
    validate_register(register)
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w") as stream:
            json.dump(register, stream, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp_name, path)
        os.chmod(path, 0o600)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)


def mutate(path: Path, operation) -> object:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    lock_path = path.with_suffix(path.suffix + ".lock")
    lock_fd = os.open(lock_path, os.O_CREAT | os.O_RDWR, 0o600)
    try:
        os.fchmod(lock_fd, 0o600)
        fcntl.flock(lock_fd, fcntl.LOCK_EX)
        register = load_register(path)
        result = operation(register)
        write_register(path, register)
        return result
    finally:
        os.close(lock_fd)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--register", type=Path, default=DEFAULT_REGISTER,
                        help=f"private JSON register (default: {DEFAULT_REGISTER})")
    commands = parser.add_subparsers(dest="command", required=True)
    imp = commands.add_parser("import-candidates", help="idempotently import a candidate report")
    imp.add_argument("candidate_file", type=Path)

    show = commands.add_parser("list", help="list current records")
    show.add_argument("--status", choices=sorted(STATUSES))

    change = commands.add_parser("transition", help="record a reviewed status transition")
    change.add_argument("finding_id")
    change.add_argument("--to", required=True, choices=sorted(STATUSES))
    change.add_argument("--actor", required=True)
    change.add_argument("--rationale", required=True)
    change.add_argument("--impact-rationale")
    change.add_argument("--likelihood-rationale")
    change.add_argument("--residual-risk-rationale")
    change.add_argument("--owner")
    change.add_argument("--due-date")
    change.add_argument("--decision-authority")
    change.add_argument("--accepted-until")
    change.add_argument("--evidence")
    change.add_argument("--retest-result", choices=("pass", "fail"))
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "import-candidates":
            imported = mutate(args.register,
                              lambda reg: import_candidates(reg, args.candidate_file))
            print(f"Imported {len(imported)} candidate(s): " +
                  (", ".join(imported) if imported else "none (already present or empty report)"))
        elif args.command == "transition":
            def update(reg):
                transition(reg, args.finding_id, args.to, actor=args.actor,
                           rationale=args.rationale,
                           impact_rationale=args.impact_rationale,
                           likelihood_rationale=args.likelihood_rationale,
                           residual_risk_rationale=args.residual_risk_rationale,
                           owner=args.owner, due_date=args.due_date,
                           decision_authority=args.decision_authority,
                           accepted_until=args.accepted_until, evidence=args.evidence,
                           retest_result=args.retest_result)
            mutate(args.register, update)
            print(f"Recorded {args.finding_id} -> {args.to}")
        else:
            register = load_register(args.register)
            findings = [item for item in register["findings"]
                        if args.status is None or item["status"] == args.status]
            for item in findings:
                candidate = item["sourceCandidate"]
                print(f"{item['findingId']}\t{item['status']}\t{item['title']}\t"
                      f"{candidate.get('testSuite')}:{candidate.get('testId')}")
            print(f"{len(findings)} finding(s)")
    except (RegisterError, OSError, json.JSONDecodeError) as exc:
        print(f"Finding register operation failed: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
