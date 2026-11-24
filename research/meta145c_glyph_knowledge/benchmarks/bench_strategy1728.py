#!/usr/bin/env python3
"""Calibrate a finite strategy model, select on training, then measure replay.

Public output contains identifiers/digests/counts, not original source text.
The model's forecast and paired measured composite-workload results are separate.
The measured replay deliberately varies executor receipt versions per scenario
to exercise bounded memo behavior rather than let durable receipts hide it.
"""
from __future__ import annotations

import argparse
import asyncio
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import platform
import sqlite3
import statistics
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.core import SourceSnapshot
from src.beast20.execution import AsyncExecutor
from src.beast20.runtime import CascadeCompiler
from src.beast20.storage import ArtifactStore, Scope, canonical_bytes, semantic_key
from src.beast20.strategy_lab import StrategyConfig, StrategyLab, compact_summary, digest, trace_envelope
from bench_beast20 import synthetic_snapshot


def implementation_manifest():
    paths = [Path(__file__), ROOT / "src/beast20/strategy_lab.py", ROOT / "src/beast20/runtime.py",
             ROOT / "src/beast20/storage.py", ROOT / "src/beast20/execution.py"]
    return {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}


def _timed_ns(fn, repeats=9):
    times = []
    for _ in range(repeats):
        start = time.perf_counter_ns()
        fn()
        times.append(max(1, time.perf_counter_ns() - start))
    return int(statistics.median(times)), times


def _key(scope, version, handler, payload, parents):
    return semantic_key(scope, "strategy_composite_memo", version,
                        {"handler": handler}, {"payload": payload, "parents": parents})


def _metadata_objects(snapshot):
    return [canonical_bytes({"coordinate": nid,
                             "source_record_digest": snapshot.nodes[nid]["source_record_sha256"]})
            for nid in sorted(snapshot.nodes)]


def calibrate_trace(snapshot, *, edition="ariadne-v0.7", synthetic=False):
    """Measure actual lexical/reduction handler services and SQLite operations."""
    compiler = CascadeCompiler(snapshot)
    scope = Scope(snapshot.registry_sha, edition, "local-strategy-calibration", 1)
    node_ids = sorted(snapshot.nodes)
    variants = [None, {node_ids[0]: {"review_revision": 1}},
                {node_ids[-1]: {"review_revision": 7}}]
    measurements = []
    for supplemental in variants:
        outputs, rows = {}, []
        handlers = compiler.handlers()
        for task in compiler.tasks(supplemental):
            parents = {name: outputs[name] for name in task.dependencies}
            fn = handlers[task.handler]
            samples, result = [], None
            for _ in range(3):
                start = time.perf_counter_ns()
                current = fn(task.payload, parents)
                samples.append(max(1, time.perf_counter_ns() - start))
                if result is not None and current != result:
                    raise ValueError("NONDETERMINISTIC_CALIBRATION_HANDLER")
                result = current
            outputs[task.task_id] = result
            rows.append({"task_id": task.task_id, "house": task.house,
                         "dependencies": list(task.dependencies),
                         "cache_key": _key(scope, task.version, task.handler, task.payload, parents),
                         "output_digest": digest(result), "result_bytes": len(canonical_bytes(result)),
                         "cpu_ns": int(statistics.median(samples)), "async_wait_ns": 0})
        measurements.append({"tasks": rows, "output_sha256": digest(outputs),
                             "node_change_count": 0 if supplemental is None else len(supplemental)})
    with tempfile.TemporaryDirectory(prefix="atlas-strategy-calibration-") as tmp:
        with ArtifactStore(str(Path(tmp) / "calibration.sqlite")) as store:
            objects = _metadata_objects(snapshot)[:128]
            digests = [store.put_object(scope, raw) for raw in objects]
            sample_value = {"calibration": "bounded-source-metadata", "value": 7}
            store.memo_put(scope, "calibration-key", sample_value)
            lookup, lookup_raw = _timed_ns(lambda: store.memo_get(scope, "calibration-key"))
            write, write_raw = _timed_ns(lambda: store.memo_put(scope, "calibration-key", sample_value))
            one, one_raw = _timed_ns(lambda: store.batch_get(scope, digests, chunk_size=1))
            batched, batch_raw = _timed_ns(lambda: store.batch_get(scope, digests, chunk_size=128))
            fixed = max(0, round((one - batched) / max(1, len(digests) - 1)))
            item = max(0, round((batched - fixed) / max(1, len(digests))))
    scenarios = []
    for name, split, index in (("train-cold", "train", 0), ("train-repeat", "train", 0),
                               ("train-one-change", "train", 1), ("holdout-cold", "holdout", 0),
                               ("holdout-repeat", "holdout", 0), ("holdout-other-change", "holdout", 2)):
        scenarios.append({"name": name, "split": split, "unique_object_count": len(node_ids),
                          "tasks": measurements[index]["tasks"]})
    payload = {"schema": "atlas.beast20.strategy-trace/v1", "source_digest": snapshot.registry_sha,
               "edition": edition, "measurement_kind": "MEASURED_HANDLER_SERVICE_TIMES",
               "source_fixture_kind": "SYNTHETIC_TOPOLOGY" if synthetic else "PINNED_ORIGINAL_ARIADNE",
               "calibration": {"memo_lookup_ns": lookup, "memo_store_ns": write,
                               "batch_fixed_ns": fixed, "batch_item_ns": item},
               "calibration_method": "Median of nine actual local SQLite calls; linear batch-cost fit, nonnegative-clipped.",
               "calibration_raw_ns": {"memo_lookup": lookup_raw, "memo_store": write_raw,
                                      "single_object_chunks": one_raw, "128_object_chunks": batch_raw},
               "handler_samples_per_task": 3, "implementation_manifest": implementation_manifest(),
               "source_object_representation": "Coordinate and original-record digest metadata; no full source text in batch calibration.",
               "scenario_output_digests": [r["output_sha256"] for r in measurements],
               "scenarios": scenarios,
               "limitations": ["Trace measures handler services, not complete executor wall time.",
                               "Holdout changes a different node; this is bounded workload holdout, not independent external data.",
                               "No async wait is synthesized into the measured trace.",
                               "Model assumes no TTL expiry and excludes provider failures."]}
    return trace_envelope(payload)


async def replay_actual(snapshot, config):
    """Run the actual batch, bounded memo, and executor controls on three graphs."""
    compiler = CascadeCompiler(snapshot)
    scope = Scope(snapshot.registry_sha, "strategy-replay-v1", "local-strategy-replay", 1)
    node_ids = sorted(snapshot.nodes)
    changes = [None, None, {node_ids[-1]: {"review_revision": 7}}]
    with tempfile.TemporaryDirectory(prefix="atlas-strategy-replay-") as tmp:
        store = ArtifactStore(str(Path(tmp) / "objects.sqlite"), max_memo_entries=config.max_memo_entries)
        objects = _metadata_objects(snapshot)
        object_digests = [store.put_object(scope, raw) for raw in objects]
        original = compiler.handlers()
        version = compiler.tasks()[0].version
        counts = {"memo_hits": 0, "memo_misses": 0}

        def wrap(name):
            def handler(payload, parents):
                key = _key(scope, version, name, payload, parents)
                cached = store.memo_get(scope, key)
                if cached.hit:
                    counts["memo_hits"] += 1
                    return cached.value
                counts["memo_misses"] += 1
                result = original[name](payload, parents)
                store.memo_put(scope, key, result)
                return result
            return handler

        executor = AsyncExecutor(str(Path(tmp) / "jobs.sqlite"), {name: wrap(name) for name in original},
                                 scope_key=scope.key, workers=config.workers)
        outputs = []
        start = time.perf_counter_ns()
        try:
            for number, changed in enumerate(changes):
                returned = store.batch_get(scope, object_digests, chunk_size=config.chunk_size)
                if returned != objects:
                    raise ValueError("REPLAY_BATCH_OUTPUT_MISMATCH")
                tasks = [replace(task, version=task.version + f":scenario-{number}")
                         for task in compiler.tasks(changed)]
                result = await executor.run_graph(tasks)
                if not result.succeeded:
                    raise ValueError("REPLAY_GRAPH_FAILED")
                outputs.append(digest(result.outputs))
            elapsed = time.perf_counter_ns() - start
        finally:
            executor.close()
            store.close()
    return {"elapsed_ns": elapsed, "output_sha256": digest(outputs), "counts": counts}


async def paired_actual(snapshot, baseline, candidate, repeats):
    if type(repeats) is not int or not 1 <= repeats <= 9:
        raise ValueError("REPLAY_REPEAT_BOUND_INVALID")
    pairs = []
    for i in range(repeats):
        order = ("baseline", "candidate") if i % 2 == 0 else ("candidate", "baseline")
        row = {"pair": i + 1, "order": list(order)}
        for lane in order:
            row[lane] = await replay_actual(snapshot, baseline if lane == "baseline" else candidate)
        row["outputs_equal"] = row["baseline"]["output_sha256"] == row["candidate"]["output_sha256"]
        if not row["outputs_equal"]:
            raise ValueError("ACTUAL_PAIRED_OUTPUT_MISMATCH")
        pairs.append(row)
    b = statistics.median(r["baseline"]["elapsed_ns"] for r in pairs)
    c = statistics.median(r["candidate"]["elapsed_ns"] for r in pairs)
    return {"status": "MEASURED_LOCAL_COMPOSITE_REPLAY", "repeats": repeats,
            "baseline_config": baseline.as_dict(), "candidate_config": candidate.as_dict(),
            "baseline_median_ns": b, "candidate_median_ns": c,
            "measured_ratio_baseline_over_candidate": b / c,
            "all_outputs_equal": all(r["outputs_equal"] for r in pairs), "raw_pairs": pairs,
            "limitations": ["Composite local workload, not hosted or total-Atlas performance.",
                            "Executor receipt versions change per scenario to expose bounded memo behavior.",
                            "Source metadata batches contain coordinates and record digests; full source text is excluded.",
                            "Task handlers are synchronous; extra async workers do not imply CPU multicore speedup.",
                            "Measured replay is independent of simulated forecasts; unfavorable results are retained."]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", type=Path)
    parser.add_argument("--topics", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--repeats", type=int, default=5, choices=range(1, 10))
    args = parser.parse_args()
    if args.topics and not args.registry:
        parser.error("--topics requires --registry")
    initial_manifest = implementation_manifest()
    snapshot = SourceSnapshot(args.registry, args.topics) if args.registry else synthetic_snapshot()
    edition = "ariadne-v0.7" if args.registry else "synthetic-1728-v1"
    trace = calibrate_trace(snapshot, edition=edition, synthetic=not bool(args.registry))
    result = StrategyLab(snapshot.registry_sha, edition).evaluate(trace, expected_trace_sha256=trace["sha256"])
    selected = result["meta145"]["selected"]
    if selected is None:
        raise ValueError("NO_SELECTED_STRATEGY")
    actual = asyncio.run(paired_actual(snapshot, StrategyConfig(), StrategyConfig(**selected["config"]), args.repeats))
    actual.update({"trace_sha256": trace["sha256"], "strategy_report_sha256": result["report_sha256"],
                   "source_digest": snapshot.registry_sha, "python": platform.python_version(),
                   "sqlite": sqlite3.sqlite_version, "implementation_manifest": initial_manifest,
                   "implementation_manifest_unchanged": initial_manifest == implementation_manifest()})
    if not actual["implementation_manifest_unchanged"]:
        raise ValueError("IMPLEMENTATION_CHANGED_DURING_BENCHMARK")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    documents = {"STRATEGY1728_TRACE.json": trace, "STRATEGY1728_CANDIDATES.json": result,
                 "STRATEGY1728_SUMMARY.json": compact_summary(result), "STRATEGY1728_MEASURED_REPLAY.json": actual}
    for filename, value in documents.items():
        (args.output_dir / filename).write_text(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n")
    print(json.dumps({"status": "COMPLETED", "candidate_count": result["candidate_count"],
                      "selected": selected["config"], "predicted_holdout_ratio": result["meta145"]["predicted_holdout_ratio_baseline_over_candidate"],
                      "measured_composite_ratio": actual["measured_ratio_baseline_over_candidate"],
                      "all_outputs_equal": actual["all_outputs_equal"], "files": list(documents)}, indent=2))


if __name__ == "__main__":
    main()
