#!/usr/bin/env python3
"""Compare two source checkouts on the identical real cold/warm/changed DAG.

Each lane runs in a fresh Python process. Timings come from replay_actual and
exclude process startup, source loading and object population, as in the pinned
Native1728 benchmark. Raw unfavorable results are retained. No model is called.
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
from pathlib import Path
import platform
import statistics
import subprocess
import sys


def manifest(root):
    paths = ("benchmarks/bench_strategy1728.py", "src/beast20/storage.py",
             "src/beast20/execution.py", "src/beast20/runtime.py",
             "src/beast20/strategy_lab.py")
    return {path: hashlib.sha256((root / path).read_bytes()).hexdigest() for path in paths}


def child(args):
    root = args.lane_root.resolve(strict=True)
    before = manifest(root)
    sys.path.insert(0, str(root / "benchmarks"))
    from bench_strategy1728 import SourceSnapshot, StrategyConfig, replay_actual
    snapshot = SourceSnapshot(args.registry, args.topics)
    result = asyncio.run(replay_actual(snapshot, StrategyConfig(
        workers=args.workers, max_memo_entries=args.memo, chunk_size=args.chunk)))
    after = manifest(root)
    if before != after:
        raise ValueError("IMPLEMENTATION_CHANGED_DURING_LANE")
    result.update(source_digest=snapshot.registry_sha, implementation_manifest=after)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline-root", type=Path)
    parser.add_argument("--candidate-root", type=Path)
    parser.add_argument("--registry", type=Path, required=True)
    parser.add_argument("--topics", type=Path)
    parser.add_argument("--workers", type=int, default=1, choices=range(1, 13))
    parser.add_argument("--memo", type=int, default=2048)
    parser.add_argument("--chunk", type=int, default=400, choices=range(1, 401))
    parser.add_argument("--repeats", type=int, default=9, choices=range(1, 10))
    parser.add_argument("--output", type=Path)
    parser.add_argument("--lane-root", type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.lane_root:
        print(json.dumps(child(args), sort_keys=True))
        return
    if not args.baseline_root or not args.candidate_root or not args.output:
        parser.error("--baseline-root, --candidate-root and --output are required")
    if not 1 <= args.memo <= 1_000_000:
        parser.error("--memo must be between 1 and 1,000,000")
    roots = {name: path.resolve(strict=True) for name, path in
             (("baseline", args.baseline_root), ("candidate", args.candidate_root))}
    expected = {name: manifest(root) for name, root in roots.items()}
    pairs = []
    for i in range(args.repeats):
        order = ["baseline", "candidate"] if i % 2 == 0 else ["candidate", "baseline"]
        pair = {"pair": i + 1, "order": order}
        for lane in order:
            command = [sys.executable, str(Path(__file__).resolve()), "--lane-root", str(roots[lane]),
                       "--registry", str(args.registry.resolve()), "--workers", str(args.workers),
                       "--memo", str(args.memo), "--chunk", str(args.chunk)]
            if args.topics:
                command += ["--topics", str(args.topics.resolve())]
            result = subprocess.run(command, capture_output=True, text=True, check=True,
                                    timeout=180)
            pair[lane] = json.loads(result.stdout)
            if pair[lane]["implementation_manifest"] != expected[lane]:
                raise ValueError("IMPLEMENTATION_CHANGED_BETWEEN_PAIRS")
        pair["outputs_equal"] = pair["baseline"]["output_sha256"] == pair["candidate"]["output_sha256"]
        pair["counts_equal"] = pair["baseline"]["counts"] == pair["candidate"]["counts"]
        if (not pair["outputs_equal"] or not pair["counts_equal"] or
                pair["baseline"]["source_digest"] != pair["candidate"]["source_digest"]):
            raise ValueError("CANDIDATE_BEHAVIOR_MISMATCH")
        pairs.append(pair)
        print(json.dumps({"pair": i + 1, "outputs_equal": True,
                          "baseline_ns": pair["baseline"]["elapsed_ns"],
                          "candidate_ns": pair["candidate"]["elapsed_ns"]}), flush=True)
    if expected != {name: manifest(root) for name, root in roots.items()}:
        raise ValueError("IMPLEMENTATION_CHANGED_DURING_BENCHMARK")
    baseline = statistics.median(p["baseline"]["elapsed_ns"] for p in pairs)
    candidate = statistics.median(p["candidate"]["elapsed_ns"] for p in pairs)
    report = {
        "schema": "atlas.native1728.cascade-upgrade-measurement/v1",
        "status": "MEASURED_LOCAL_COMPOSITE_REPLAY", "python": platform.python_version(),
        "configuration_both_lanes": {"workers": args.workers, "max_memo_entries": args.memo,
                                     "chunk_size": args.chunk},
        "repeats": args.repeats, "baseline_median_ns": baseline, "candidate_median_ns": candidate,
        "measured_ratio_baseline_over_candidate": baseline / candidate,
        "median_latency_reduction_percent": 100 * (1 - candidate / baseline),
        "all_outputs_equal": True, "all_counts_equal": True,
        "source_digest": pairs[0]["baseline"]["source_digest"],
        "implementation_manifest": expected, "implementation_manifest_unchanged": True,
        "raw_pairs": pairs,
        "limits": ["Same runtime configuration in both source versions; this isolates implementation changes.",
                   "Local source metadata and cold/warm/changed DAG replay; no hosted latency claim.",
                   "Process startup and object population excluded from timing in both lanes.",
                   "A ratio below one is retained as a regression; no multiplication with other benchmarks.",
                   "No training, model API call, room post or resident Macroturn."],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({key: report[key] for key in ("status", "repeats", "measured_ratio_baseline_over_candidate",
                                                 "all_outputs_equal", "all_counts_equal")}), flush=True)


if __name__ == "__main__":
    main()
