#!/usr/bin/env python3
"""Reproducible, network-free R16 source gate when GitHub Actions runners cannot start.

Source tests are not host attestation. No private registry, network calls,
GitHub token, CI secret, deploy or release decision is read or changed.
"""
from __future__ import annotations

import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parent.parent
SOURCES = (
    "src/telescope_engine.py",
    "src/build_dashboard.py",
    "src/peer_cluster_falsifier.py",
    "src/temporal_dependency_falsifier.py",
    "src/trace_pareto.py",
    "src/verify_output.py",
    "tests/test_public_contract.py",
    "tests/test_temporal_dependency.py",
)
EXPECTED_TESTS = 29
RESULT_SCHEMA = "atlas.r16.local-ci-receipt/v1"


def execute(mode: str) -> dict:
    cmd = [sys.executable, "-I", "-B"]
    if mode == "optimized":
        cmd.append("-O")
    cmd += ["-m", "unittest", "discover", "-s", str(ROOT / "tests"), "-p", "test_*.py", "-q"]
    env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "PYTHONHASHSEED": "0"}
    env.pop("PYTHONOPTIMIZE", None)  # standard and -O are genuinely distinct passes
    try:
        completed = subprocess.run(cmd, cwd=ROOT, env=env, text=True,
                                   capture_output=True, timeout=120, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return {"mode": mode, "result": "HOLD_EXECUTION_UNAVAILABLE", "tests": None}
    output = completed.stdout + "\n" + completed.stderr
    count_match = re.search(r"\bRan (\d+) tests? in\b", output)
    count = int(count_match.group(1)) if count_match else None
    passed = (completed.returncode == 0 and count == EXPECTED_TESTS
              and bool(re.search(r"(?m)^OK\s*$", output)))
    return {"mode": mode, "result": "PASS_LOCAL_SOURCE_ONLY" if passed else "FAIL_OR_INCOMPLETE",
            "tests": count, "expectedTests": EXPECTED_TESTS, "exitCode": completed.returncode}


def main() -> int:
    report = {"schema": RESULT_SCHEMA, "classification": "LOCAL_OFFLINE_NOT_HOST_ATTESTED",
              "hostedGitHubActionsVerified": False, "productionPromotionAllowed": False,
              "python": ".".join(str(x) for x in sys.version_info[:3]),
              "sourceHashes": {}, "checks": [], "state": "HOLD"}
    for filename in SOURCES:
        path = ROOT / filename
        if not path.is_file() or path.stat().st_size == 0:
            report["missingSource"] = filename
            print(json.dumps(report, sort_keys=True, indent=2))
            return 1
        report["sourceHashes"][filename] = hashlib.sha256(path.read_bytes()).hexdigest()
    try:
        version = importlib.metadata.version("numpy")
        major = int(version.split(".")[0])
        if major != 2:
            raise ValueError("Expected NumPy 2.x")
        report["numpyVersion"] = version
    except (importlib.metadata.PackageNotFoundError, ValueError):
        report["dependency"] = "NUMPY_2_REQUIRED_OFFLINE_NO_AUTO_INSTALL"
        print(json.dumps(report, sort_keys=True, indent=2))
        return 1
    report["checks"] = [execute("standard"), execute("optimized")]
    if all(x["result"] == "PASS_LOCAL_SOURCE_ONLY" for x in report["checks"]):
        report["state"] = "PASS_LOCAL_SOURCE_ONLY_HOSTED_HOLD"
    print(json.dumps(report, sort_keys=True, indent=2))
    return 0 if report["state"] == "PASS_LOCAL_SOURCE_ONLY_HOSTED_HOLD" else 1


if __name__ == "__main__":
    raise SystemExit(main())
