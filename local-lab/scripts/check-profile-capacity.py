#!/usr/bin/env python3
"""Fail closed when optional observability lacks local node memory headroom."""
from __future__ import annotations

import argparse
from decimal import Decimal, InvalidOperation
import json
import re
import subprocess
import sys

CONTROL_NODE = "cks-control"
WORKER_NODE = "cks-worker"
MIB = 1024 ** 2
CONTROL_MIN_MIB = 1024
WORKER_MIN_MIB = 2048
OPENCOST_EXTRA_MIB = 512
DECIMAL_SUFFIXES = {
    "": Decimal(1), "n": Decimal("1e-9"), "u": Decimal("1e-6"),
    "m": Decimal("1e-3"), "k": Decimal(1000), "K": Decimal(1000),
    "M": Decimal(1000) ** 2, "G": Decimal(1000) ** 3,
    "T": Decimal(1000) ** 4, "P": Decimal(1000) ** 5,
    "E": Decimal(1000) ** 6,
}
BINARY_SUFFIXES = {
    "Ki": 1024, "Mi": 1024 ** 2, "Gi": 1024 ** 3,
    "Ti": 1024 ** 4, "Pi": 1024 ** 5, "Ei": 1024 ** 6,
}


def memory_bytes(quantity: str) -> int:
    match = re.fullmatch(r"([0-9]+(?:\.[0-9]+)?)([a-zA-Z]*)", quantity)
    if not match:
        raise ValueError(f"invalid memory quantity: {quantity}")
    number, suffix = match.groups()
    try:
        value = Decimal(number)
        if suffix in BINARY_SUFFIXES:
            value *= BINARY_SUFFIXES[suffix]
        elif suffix in DECIMAL_SUFFIXES:
            value *= DECIMAL_SUFFIXES[suffix]
        else:
            raise ValueError(f"unsupported memory suffix: {suffix}")
        return int(value)
    except InvalidOperation as exc:
        raise ValueError(f"invalid memory quantity: {quantity}") from exc


def calculate_headroom(nodes: dict, metrics: dict) -> dict[str, int]:
    allocatable = {
        item["metadata"]["name"]: memory_bytes(item["status"]["allocatable"]["memory"])
        for item in nodes.get("items", [])
    }
    usage = {
        item["metadata"]["name"]: memory_bytes(item["usage"]["memory"])
        for item in metrics.get("items", [])
    }
    headroom = {}
    for name in (CONTROL_NODE, WORKER_NODE):
        if name not in allocatable or name not in usage:
            raise ValueError(f"missing allocatable memory or Metrics API usage for {name}")
        headroom[name] = allocatable[name] - usage[name]
    return headroom


def requirements(include_opencost: bool = False) -> dict[str, int]:
    worker_min = WORKER_MIN_MIB + (OPENCOST_EXTRA_MIB if include_opencost else 0)
    return {CONTROL_NODE: CONTROL_MIN_MIB * MIB, WORKER_NODE: worker_min * MIB}


def evaluate(headroom: dict[str, int], include_opencost: bool = False) -> list[tuple[str, int, int]]:
    return [(name, headroom.get(name, -1), minimum)
            for name, minimum in requirements(include_opencost).items()
            if headroom.get(name, -1) < minimum]


def kubectl_json(command: list[str], timeout: int = 20) -> dict:
    result = subprocess.run(command, text=True, capture_output=True, timeout=timeout)
    if result.returncode:
        raise RuntimeError("kubectl could not collect node capacity data")
    return json.loads(result.stdout)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kubectl", default="kubectl")
    parser.add_argument("--kubeconfig")
    parser.add_argument("--context")
    parser.add_argument("--include-opencost", action="store_true",
                        help="apply the additional worker headroom requirement for OpenCost")
    args = parser.parse_args()

    prefix = [args.kubectl]
    if args.kubeconfig:
        prefix += ["--kubeconfig", args.kubeconfig]
    if args.context:
        prefix += ["--context", args.context]
    try:
        nodes = kubectl_json(prefix + ["get", "nodes", "-o", "json"])
        metrics = kubectl_json(prefix + ["get", "--raw=/apis/metrics.k8s.io/v1beta1/nodes"])
        headroom = calculate_headroom(nodes, metrics)
    except (OSError, RuntimeError, ValueError, KeyError, json.JSONDecodeError,
            subprocess.TimeoutExpired) as exc:
        print(f"Capacity preflight failed ({type(exc).__name__}); refusing optional observability deployment.",
              file=sys.stderr)
        return 2

    minimums = requirements(args.include_opencost)
    problems = evaluate(headroom, args.include_opencost)
    print("Node memory headroom (allocatable minus Metrics API working set):")
    for name in (CONTROL_NODE, WORKER_NODE):
        print(f"  {name}: {headroom[name] // MIB} MiB available; "
              f"minimum {minimums[name] // MIB} MiB")
    if problems:
        print("Insufficient memory headroom; refusing optional observability deployment.",
              file=sys.stderr)
        return 1
    print("Capacity preflight passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
