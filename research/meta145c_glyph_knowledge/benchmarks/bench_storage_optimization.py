#!/usr/bin/env python3
"""Compare current storage with immutable Git baseline bytes on real operations.

This is a finite storage-facing handler benchmark. The separate cascade-upgrade
runner measures the AsyncExecutor composite. Public receipts contain only
identities, hashes, counts and timings, never original source bodies.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import platform
import re
import sqlite3
import statistics
import subprocess
import sys
import tempfile
import time
import types

ROOT = Path(__file__).resolve().parents[1]
REPOSITORY = ROOT.parents[1]
sys.path.insert(0, str(ROOT))

from src.core import SourceSnapshot
from src.beast20.runtime import CascadeCompiler
from bench_beast20 import synthetic_snapshot

BASELINE_COMMIT = "2bea02211f93763bd753434676945c0f5bc7b8a7"
STORAGE_PATH = "research/meta145c_glyph_knowledge/src/beast20/storage.py"


def require(condition, message):
    if not condition:
        raise ValueError(message)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                      allow_nan=False).encode("utf-8")


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def file_sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_storage(body, name):
    module = types.ModuleType(name)
    module.__file__ = f"<{name}:storage.py>"
    sys.modules[name] = module
    exec(compile(body, module.__file__, "exec"), module.__dict__)
    return module


def pinned_baseline(commit):
    require(re.fullmatch(r"[0-9a-f]{40}", commit) is not None, "IMMUTABLE_COMMIT_REQUIRED")
    body = subprocess.run(["git", "-C", str(REPOSITORY), "show", f"{commit}:{STORAGE_PATH}"],
                          check=True, capture_output=True).stdout
    blob = subprocess.run(["git", "-C", str(REPOSITORY), "rev-parse", f"{commit}:{STORAGE_PATH}"],
                          check=True, capture_output=True, text=True).stdout.strip()
    require(hashlib.sha1(b"blob " + str(len(body)).encode() + b"\0" + body).hexdigest() == blob,
            "BASELINE_GIT_BLOB_MISMATCH")
    return body, blob


def clear_identity_cache(module):
    cached = getattr(module, "_scope_digest", None)
    if hasattr(cached, "cache_clear"):
        cached.cache_clear()


def current_manifest():
    names = [
        "src/beast20/storage.py", "src/beast20/runtime.py", "src/beast20/execution.py",
        "src/core.py", "benchmarks/bench_beast20.py", "benchmarks/bench_storage_optimization.py",
    ]
    return {name: file_sha(ROOT / name) for name in names}


def historical_evidence():
    names = [
        "STRATEGY1728_SUMMARY.json", "STRATEGY1728_MEASURED_REPLAY.json",
        "STRATEGY1728_TRACE.json.gz", "STRATEGY1728_CANDIDATES.json.gz",
    ]
    return {f"benchmarks/strategy1728/{name}": file_sha(ROOT / "benchmarks/strategy1728" / name)
            for name in names if (ROOT / "benchmarks/strategy1728" / name).exists()}


def memo_workload(module, snapshot, capacity, storage_mode):
    clear_identity_cache(module)
    scope = module.Scope(snapshot.registry_sha, "storage-upgrade-v1", "local-storage-benchmark", 1)
    compiler = CascadeCompiler(snapshot)
    nodes = sorted(snapshot.nodes)
    variants = [("cold", None), ("warm", None),
                ("changed", {nodes[-1]: {"review_revision": 7}})]
    # Exact snapshot validation and task construction are setup for this
    # storage-facing benchmark. The separate full-cascade benchmark times them.
    templates = [(name, compiler.tasks(change)) for name, change in variants]
    objects = [module.canonical_bytes({"coordinate": key,
                 "source_record_digest": snapshot.nodes[key]["source_record_sha256"]}) for key in nodes]
    handlers = compiler.handlers()
    phases = []
    with tempfile.TemporaryDirectory(prefix="atlas-storage-bench-") as directory:
        path = ":memory:" if storage_mode == "memory" else str(Path(directory) / "store.sqlite")
        with module.ArtifactStore(path, max_memo_entries=capacity, clock=lambda: 100.0) as store:
            object_digests = [store.put_object(scope, raw) for raw in objects]
            for name, tasks in templates:
                outputs = {}
                hits = misses = 0
                started = time.perf_counter_ns()
                require(store.batch_get(scope, object_digests, chunk_size=400) == objects,
                        "BATCH_OUTPUT_MISMATCH")
                for task in tasks:
                    parents = {key: outputs[key] for key in task.dependencies}
                    key = module.semantic_key(scope, "strategy_composite_memo", task.version,
                                              {"handler": task.handler},
                                              {"payload": task.payload, "parents": parents})
                    cached = store.memo_get(scope, key)
                    if cached.hit:
                        hits += 1
                        output = cached.value
                    else:
                        misses += 1
                        output = handlers[task.handler](task.payload, parents)
                        store.memo_put(scope, key, output)
                    outputs[task.task_id] = output
                elapsed = max(1, time.perf_counter_ns() - started)
                phases.append({"name": name, "elapsedNs": elapsed, "memoHits": hits,
                               "memoMisses": misses, "outputSha256": digest(outputs)})
            rows = store.db.execute("SELECT COUNT(*) FROM beast_memo").fetchone()[0]
            require(rows <= capacity, "MEMO_CAPACITY_VIOLATED")
    counts = {"memoHits": sum(p["memoHits"] for p in phases),
              "memoMisses": sum(p["memoMisses"] for p in phases)}
    signature = {"phases": [{k: v for k, v in phase.items() if k != "elapsedNs"} for phase in phases],
                 "counts": counts, "memoEntries": rows}
    return {"elapsedNs": sum(p["elapsedNs"] for p in phases), "phases": phases,
            "counts": counts, "memoEntries": rows, "outputSha256": digest(signature)}


def batch_workload(module, source_digest, width, rounds, storage_mode):
    clear_identity_cache(module)
    scope = module.Scope(source_digest, "storage-batch-control-v1", "local-storage-benchmark", 1)
    bodies = [module.canonical_bytes({"record": i, "payload": "source-metadata-" + str(i)})
              for i in range(256)]
    with tempfile.TemporaryDirectory(prefix="atlas-batch-bench-") as directory:
        path = ":memory:" if storage_mode == "memory" else str(Path(directory) / "store.sqlite")
        with module.ArtifactStore(path, clock=lambda: 100.0) as store:
            keys = [store.put_object(scope, body) for body in bodies]
            requested = list(reversed(keys)) + [keys[0], "0" * 64]
            expected = list(reversed(bodies)) + [bodies[0], None]
            started = time.perf_counter_ns()
            for _ in range(rounds):
                result = store.batch_get(scope, requested, chunk_size=width)
                require(result == expected, "BATCH_ORDER_DUPLICATE_OR_MISSING_CHANGED")
            elapsed = max(1, time.perf_counter_ns() - started)
    return {"elapsedNs": elapsed, "calls": rounds, "requestedPerCall": len(requested),
            "outputSha256": digest([hashlib.sha256(row).hexdigest() if row is not None else None
                                     for row in result])}


def paired(name, run, modules, repeats, extra):
    pairs = []
    for number in range(repeats):
        order = ["baseline", "candidate"] if number % 2 == 0 else ["candidate", "baseline"]
        pair = {"pair": number + 1, "order": order}
        for lane in order:
            pair[lane] = run(modules[lane])
        pair["outputsEqual"] = pair["baseline"]["outputSha256"] == pair["candidate"]["outputSha256"]
        require(pair["outputsEqual"], "PAIRED_OUTPUT_OR_COUNT_MISMATCH")
        pairs.append(pair)
    baseline = statistics.median(p["baseline"]["elapsedNs"] for p in pairs)
    candidate = statistics.median(p["candidate"]["elapsedNs"] for p in pairs)
    phase_names = [phase["name"] for phase in pairs[0]["baseline"].get("phases", [])]
    phases = {}
    for phase in phase_names:
        medians = {lane: statistics.median(next(v["elapsedNs"] for v in p[lane]["phases"]
                                                if v["name"] == phase) for p in pairs)
                   for lane in modules}
        phases[phase] = {"medianBaselineNs": medians["baseline"],
                         "medianCandidateNs": medians["candidate"],
                         "speedupRatio": medians["baseline"] / medians["candidate"]}
    result = {"workload": name, **extra, "repeats": repeats, "rawPairs": pairs,
              "medianBaselineNs": baseline, "medianCandidateNs": candidate,
              "speedupRatio": baseline / candidate, "allOutputsEqual": True,
              "phaseMedians": phases,
              "interpretation": "LOCAL_MEDIAN_RATIO_UNCERTAINTY_NOT_ESTIMATED",
              "medianRegression": candidate > baseline}
    print(json.dumps({"workload": name, "speedupRatio": result["speedupRatio"],
                      "allOutputsEqual": True}), flush=True)
    return result


def contract_checks(module):
    scope = module.Scope("a" * 64, "storage-integrity-v1", "synthetic-owner", 1)
    now = [100.0]
    checks = {}
    with module.ArtifactStore(max_memo_entries=8, clock=lambda: now[0]) as store:
        raw = b"synthetic-integrity-object"
        object_digest = store.put_object(scope, raw)
        require(store.get_object(scope, object_digest) == raw, "OBJECT_SETUP")
        with store.db:
            store.db.execute("UPDATE beast_objects SET body=?", (b"tampered",))
        try:
            store.batch_get(scope, [object_digest, object_digest])
        except module.IntegrityError as error:
            checks["objectTamper"] = str(error)
        else:
            raise ValueError("OBJECT_TAMPER_NOT_DETECTED")
        store.memo_put(scope, "payload", {"nested": [1]})
        value = store.memo_get(scope, "payload").value
        value["nested"].append(2)
        require(store.memo_get(scope, "payload").value == {"nested": [1]}, "SHARED_MEMO_RETURN")
        checks["detachedMemo"] = True
        with store.db:
            store.db.execute("UPDATE beast_memo SET body=? WHERE key='payload'", (b'{"nested":[9]}',))
        try:
            store.memo_get(scope, "payload")
        except module.IntegrityError as error:
            checks["memoTamper"] = str(error)
        else:
            raise ValueError("MEMO_TAMPER_NOT_DETECTED")
        original_key = scope.key
        object.__setattr__(scope, "mode", "PLAY")
        try:
            store.memo_get(scope, "payload")
        except ValueError as error:
            checks["invalidScopeMutation"] = str(error)
        else:
            raise ValueError("INVALID_SCOPE_REUSED")
        object.__setattr__(scope, "mode", "WORK")
        object.__setattr__(scope, "rights_epoch", 2)
        require(scope.key != original_key and not store.memo_get(scope, "payload").hit,
                "VALID_SCOPE_MUTATION_REUSED_OLD_NAMESPACE")
        checks["validScopeMutation"] = True
        store.memo_put(scope, "a", 1, ttl=5)
        store.memo_put(scope, "b", 2, ttl=20)
        store.set_dependencies(scope, "a", ["root"])
        store.set_dependencies(scope, "b", ["a"])
        require(store.invalidate(scope, ["root"]) == ["a", "b", "root"], "INVALIDATION_CHANGED")
        require(not store.memo_get(scope, "b").hit, "INVALIDATION_MISSED")
        checks["invalidation"] = True
        store.memo_put(scope, "expires", 1, ttl=5)
        now[0] = 105.0
        require(not store.memo_get(scope, "expires").hit, "TTL_BOUNDARY_CHANGED")
        checks["exactTTL"] = True
        store.max_memo_entries = 2
        store.memo_put(scope, "x", 1)
        store.memo_put(scope, "y", 2)
        store.memo_get(scope, "x")
        store.memo_put(scope, "z", module.NEGATIVE)
        require(store.memo_get(scope, "x").hit and not store.memo_get(scope, "y").hit
                and store.memo_get(scope, "z").negative, "LRU_OR_NEGATIVE_CHANGED")
        checks["lruAndNegative"] = True
    return checks


def expiry_diagnostic(module, capacity):
    scope = module.Scope("b" * 64, "expiry-diagnostic-v1", "synthetic-owner", 1)
    with module.ArtifactStore(max_memo_entries=capacity, clock=lambda: 100.0) as store:
        for number in range(capacity):
            store.memo_put(scope, f"k-{number}", number)
        plan = [row[3] for row in store.db.execute(
            "EXPLAIN QUERY PLAN DELETE FROM beast_memo WHERE expires<=?", (100.0,))]
        callbacks = [0]
        def progress():
            callbacks[0] += 1
            return 0
        store.db.set_progress_handler(progress, 100)
        try:
            for number in range(32):
                store.memo_put(scope, f"new-{number}", number)
        finally:
            store.db.set_progress_handler(None, 0)
        return {"capacity": capacity, "puts": 32, "expiryQueryPlan": plan,
                "sqliteVMProgressInterval": 100, "sqliteVMApproximateSteps": callbacks[0] * 100,
                "diagnosticOutsideTimedPairs": True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline-revision", default=BASELINE_COMMIT)
    parser.add_argument("--registry", type=Path)
    parser.add_argument("--topics", type=Path)
    parser.add_argument("--repeats", type=int, default=9, choices=range(1, 16))
    parser.add_argument("--capacities", type=int, nargs="+", default=[8, 256, 2048])
    parser.add_argument("--batch-rounds", type=int, default=40, choices=range(1, 1001))
    parser.add_argument("--storage-mode", choices=["memory", "file"], default="memory")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    require(1 <= len(args.capacities) <= 4 and len(set(args.capacities)) == len(args.capacities)
            and all(1 <= size <= 8192 for size in args.capacities), "CAPACITY_BOUND_INVALID")
    if args.topics and not args.registry:
        parser.error("--topics requires --registry")
    baseline_bytes, baseline_blob = pinned_baseline(args.baseline_revision)
    candidate_bytes = (ROOT / "src/beast20/storage.py").read_bytes()
    before = current_manifest()
    history_before = historical_evidence()
    modules = {"baseline": load_storage(baseline_bytes, "_beast_storage_baseline_benchmark"),
               "candidate": load_storage(candidate_bytes, "_beast_storage_candidate_benchmark")}
    snapshot = SourceSnapshot(args.registry, args.topics) if args.registry else synthetic_snapshot()
    integrity = {lane: contract_checks(module) for lane, module in modules.items()}
    require(integrity["baseline"] == integrity["candidate"], "INTEGRITY_CONTRACT_CHANGED")
    workloads = []
    for capacity in args.capacities:
        workloads.append(paired(f"memo_cascade_capacity_{capacity}",
            lambda module: memo_workload(module, snapshot, capacity, args.storage_mode),
            modules, args.repeats,
            {"maxMemoEntries": capacity, "storageMode": args.storage_mode, "taskCount": 1885,
             "phases": ["cold", "warm", "changed"],
             "measurementScope": "ACTUAL_SEQUENTIAL_HANDLER_AND_STORAGE_LOOP_WITHOUT_ASYNC_EXECUTOR"}))
    for width in (1, 32, 400):
        workloads.append(paired(f"batch_read_chunk_{width}",
            lambda module: batch_workload(module, snapshot.registry_sha, width, args.batch_rounds,
                                          args.storage_mode),
            modules, args.repeats,
            {"chunkSize": width, "storageMode": args.storage_mode,
             "measurementScope": "UNCHANGED_BATCH_READ_PATH_CONTROL"}))
    diagnostics = {lane: [expiry_diagnostic(module, cap) for cap in args.capacities]
                   for lane, module in modules.items()}
    require(before == current_manifest(), "IMPLEMENTATION_CHANGED_DURING_BENCHMARK")
    require(history_before == historical_evidence(), "HISTORICAL_EVIDENCE_CHANGED")
    result = {
        "schema": "atlas.beast20.storage-upgrade/v1", "status": "MEASURED_LOCAL_STORAGE_WORKLOAD",
        "sourceDigest": snapshot.registry_sha,
        "sourceFixtureKind": "PINNED_ORIGINAL_ARIADNE" if args.registry else "SYNTHETIC_TOPOLOGY",
        "baseline": {"commit": args.baseline_revision, "path": STORAGE_PATH, "gitBlobSha": baseline_blob,
                     "sha256": hashlib.sha256(baseline_bytes).hexdigest()},
        "candidate": {"path": "src/beast20/storage.py",
                      "sha256": hashlib.sha256(candidate_bytes).hexdigest()},
        "implementationManifest": before, "implementationManifestUnchanged": True,
        "historicalEvidenceSha256": history_before, "historicalEvidenceUnchanged": True,
        "python": platform.python_version(), "sqlite": sqlite3.sqlite_version,
        "repeats": args.repeats, "workloads": workloads, "integrityChecks": integrity,
        "integrityParity": True, "expiryDiagnostics": diagnostics,
        "allOutputsEqual": all(row["allOutputsEqual"] for row in workloads),
        "medianRegressions": [row["workload"] for row in workloads if row["medianRegression"]],
        "changes": ["Fresh validated scalar scope values key a bounded 256-entry digest cache.",
                    "An expiry index replaces a full memo scan for TTL cleanup on each put."],
        "networkRequests": 0, "modelCalls": 0, "sourceBodiesReturned": False,
        "limitations": [
            "Local storage-facing benchmark; use the separately paired full-cascade receipt for total runtime latency.",
            "Default memory SQLite isolates storage CPU work; file mode is an explicit separate option.",
            "Store/schema/object setup, task construction, output hashing and diagnostics are outside timed pairs.",
            "Within a phase, verified batch reads, semantic-key construction, memo I/O and actual handler work are timed.",
            "The clock is fixed during timed scenarios to isolate cache behavior; TTL/invalidation/tamper are separate checks.",
            "Scope digest reuse never caches authorization or object/memo payload integrity.",
            "Medians and raw pairs are reported without a confidence-interval or hosted-speedup claim.",
            "Unfavorable measured cases are retained; no ratios are multiplied with the earlier configuration-selection gain.",
        ],
    }
    result["receiptSha256"] = digest(result)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False) + "\n")
    print(json.dumps({"status": result["status"], "receiptSha256": result["receiptSha256"],
                      "workloads": len(workloads), "allOutputsEqual": result["allOutputsEqual"],
                      "medianRegressions": result["medianRegressions"]}), flush=True)


if __name__ == "__main__":
    main()

