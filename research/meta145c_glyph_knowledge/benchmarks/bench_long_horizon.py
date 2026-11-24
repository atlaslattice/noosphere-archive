#!/usr/bin/env python3
"""Run every requested synthetic transition and publish source-free receipts.

Default: initial batch plus 1,728 additional epochs, each containing 1,728
configuration timelines of 1,728 request steps. No network, models or resident
turns are used. An explicit original registry and exact calibration checksum
are required; source bodies are never serialized into the result.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.core import SourceSnapshot
from src.beast20.long_horizon import (DEFAULT_SEED, MAX_EPOCHS, MAX_YEARS, _build_report,
                                    canonical_json, compile_engine, engine_input, export_bundle,
                                    load_calibration, report_summary, validate_report)


def _sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", type=Path, required=True)
    parser.add_argument("--trace", type=Path, required=True)
    parser.add_argument("--trace-sha256", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--epochs", type=int, default=MAX_EPOCHS)
    parser.add_argument("--years", type=int, default=MAX_YEARS)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--threads", type=int, default=4)
    parser.add_argument("--timeout-seconds", type=int, default=3600)
    parser.add_argument("--replace", action="store_true")
    args = parser.parse_args()
    output = args.output_dir
    names = ("LONG_HORIZON_REPORT.json", "LONG_HORIZON_REPORT.json.gz", "LONG_HORIZON_SUMMARY.json",
             "LONG_HORIZON_BUNDLE.json.gz", "LONG_HORIZON_ENGINE_RAW.json.gz", "LONG_HORIZON_MANIFEST.json")
    if not args.replace and any((output / name).exists() for name in names):
        parser.error("an output exists; choose a fresh directory or explicitly --replace")
    snapshot = SourceSnapshot(args.registry)
    calibration, source = load_calibration(snapshot, args.trace, expected_trace_file_sha256=args.trace_sha256)
    watched = {"registry": args.registry, "trace": args.trace,
               "engine": ROOT / "benchmarks/native1728_evolution/engine.cpp",
               "module": ROOT / "src/beast20/long_horizon.py", "runner": Path(__file__)}
    before = {key: _sha(path) for key, path in watched.items()}
    start = time.perf_counter_ns()
    with tempfile.TemporaryDirectory(prefix="atlas-long-horizon-run-") as tmp:
        binary = Path(tmp) / "engine"
        provenance = compile_engine(binary)
        payload = engine_input(calibration, epochs=args.epochs, years=args.years, seed=args.seed,
                               threads=args.threads, audit=True)
        if _sha(binary) != provenance["engineBinarySha256"]:
            raise RuntimeError("LONG_HORIZON_ENGINE_BINARY_IDENTITY")
        raw_path = Path(tmp) / "engine.json"
        with raw_path.open("w") as stream:
            # Engine progress remains visible on stderr. No unbounded pipe or
            # asynchronous work survives this command.
            subprocess.run([str(binary)], input=payload, text=True, stdout=stream,
                           check=True, timeout=args.timeout_seconds)
        if _sha(binary) != provenance["engineBinarySha256"]:
            raise RuntimeError("LONG_HORIZON_ENGINE_BINARY_CHANGED_DURING_RUN")
        raw = json.loads(raw_path.read_text())
    after = {key: _sha(path) for key, path in watched.items()}
    if before != after:
        raise RuntimeError("LONG_HORIZON_INPUT_OR_IMPLEMENTATION_CHANGED_DURING_RUN")
    report = _build_report(snapshot, source, raw, provenance, epochs=args.epochs, years=args.years,
                           seed=args.seed, threads=args.threads)
    validate_report(report, snapshot=snapshot)
    raw_report = canonical_json(report).encode("ascii")
    bundle = canonical_json(export_bundle(report)).encode("ascii")
    summary = (json.dumps(report_summary(report), indent=2, sort_keys=True) + "\n").encode()
    documents = {"LONG_HORIZON_REPORT.json": raw_report,
                 "LONG_HORIZON_REPORT.json.gz": gzip.compress(raw_report, mtime=0),
                 "LONG_HORIZON_SUMMARY.json": summary,
                 "LONG_HORIZON_BUNDLE.json.gz": gzip.compress(bundle, mtime=0),
                 "LONG_HORIZON_ENGINE_RAW.json.gz": gzip.compress(canonical_json(raw).encode(), mtime=0)}
    output.mkdir(parents=True, exist_ok=True)
    for name, contents in documents.items():
        temporary = output / (name + ".tmp")
        temporary.write_bytes(contents)
        temporary.replace(output / name)
    manifest = {"schema": "atlas.beast20.long-horizon-artifacts/v1", "status": "COMPLETED",
                "sourceRegistrySha256": snapshot.registry_sha, "traceFileSha256": source["traceFileSha256"],
                "reportSha256": hashlib.sha256(raw_report).hexdigest(),
                "implementationUnchangedDuringRun": before == after,
                "implementation": {key: value for key, value in before.items() if key not in ("registry", "trace")},
                "runnerElapsedNs": time.perf_counter_ns() - start,
                "files": {name: {"sha256": hashlib.sha256(contents).hexdigest(), "bytes": len(contents)}
                          for name, contents in documents.items()},
                "evidenceKind": report["evidenceKind"], "counts": report["counts"]}
    (output / "LONG_HORIZON_MANIFEST.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": report["status"], "evidenceKind": report["evidenceKind"],
                      "counts": report["counts"], "selectedCandidateId": report["meta145"]["selectedCandidateId"],
                      "baselineCandidateId": report["meta145"]["baselineCandidateId"],
                      "engineElapsedNs": report["execution"]["elapsedNs"],
                      "auditReplayUpdates": report["execution"]["auditReplayUpdates"],
                      "qualityChecks": report["qualityChecks"], "reportSha256": manifest["reportSha256"],
                      "files": list(manifest["files"]) + ["LONG_HORIZON_MANIFEST.json"]}, indent=2))


if __name__ == "__main__":
    main()
