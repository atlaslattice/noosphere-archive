#!/usr/bin/env python3
"""Reproducible local BEAST20 comparisons with raw times and output parity.

Default input is an explicitly synthetic 1,728-node fixture. --registry loads
the exact Ariadne v0.7 pin; --topics optionally loads the exact historical
OpenAlex crosswalk pin. Reports contain counts/digests, never source bodies.
No sleeps, remote calls, model inference or imaginary agents enter timings.
"""
from __future__ import annotations

import argparse
import asyncio
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import platform
import sqlite3
import statistics
import sys
import tempfile
import time
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def source_manifest():
    paths = [ROOT / "src" / name for name in (
        "__init__.py", "core.py", "glyph.py", "gf8.py", "reasoning_filter.py",
        "memory.py", "knowledge.py", "beast20/__init__.py", "beast20/storage.py",
        "beast20/execution.py", "beast20/runtime.py", "beast20/feeds.py")]
    paths.append(Path(__file__).resolve())
    return {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in paths}


IMPORT_SOURCE_MANIFEST = source_manifest()

from src.core import SourceSnapshot, initialize_db
from src.gf8 import Plate
from src.glyph import REGISTRY_SHA, positional_gf7
from src.knowledge import topic_view
from src.memory import LocalMemory
from src.reasoning_filter import prepare_reasoning_context
from src.beast20.execution import AsyncExecutor
from src.beast20.runtime import AtlasBeastRuntime, CascadeCompiler
from src.beast20.storage import ArtifactStore, Scope, canonical_bytes, search_terms


def digest(value):
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def summarize(values):
    ordered = sorted(values)
    return {"median_ms": statistics.median(values),
            "p95_ms": ordered[max(0, math.ceil(0.95 * len(ordered)) - 1)],
            "minimum_ms": ordered[0], "maximum_ms": ordered[-1]}


def finish_comparison(name, rows, limitations, workload):
    left = summarize([r["baseline_ms"] for r in rows])
    right = summarize([r["candidate_ms"] for r in rows])
    return {"name": name, "workload": workload, "repeats": len(rows),
            "baseline": left, "candidate": right,
            "median_ratio_baseline_over_candidate": left["median_ms"] / right["median_ms"],
            "all_outputs_equal": all(row["outputs_equal"] for row in rows),
            "raw_pairs": rows, "limitations": limitations}


def paired(name, baseline, candidate, repeats, *, workload, limitations=(), projection=lambda x: x):
    # Untimed execution checks parity and initializes interpreter/code paths.
    if digest(projection(baseline(-1))) != digest(projection(candidate(-1))):
        raise AssertionError(name + ": WARMUP_OUTPUT_MISMATCH")
    rows = []
    for i in range(repeats):
        order = ("baseline", "candidate") if i % 2 == 0 else ("candidate", "baseline")
        row = {"pair": i + 1, "order": list(order)}
        outputs = {}
        for lane in order:
            fn = baseline if lane == "baseline" else candidate
            start = time.perf_counter_ns()
            output = fn(i)
            row[lane + "_ms"] = (time.perf_counter_ns() - start) / 1e6
            outputs[lane] = digest(projection(output))
        row["outputs_equal"] = outputs["baseline"] == outputs["candidate"]
        row["output_sha256"] = outputs["candidate"]
        if not row["outputs_equal"]:
            raise AssertionError(name + ": TIMED_OUTPUT_MISMATCH")
        rows.append(row)
    return finish_comparison(name, rows, list(limitations), workload)


async def paired_async(name, baseline, candidate, repeats, *, workload, limitations=()):
    rows = []
    for i in range(repeats):
        order = ("baseline", "candidate") if i % 2 == 0 else ("candidate", "baseline")
        row = {"pair": i + 1, "order": list(order)}
        outputs = {}
        for lane in order:
            start = time.perf_counter_ns()
            result = await (baseline(i) if lane == "baseline" else candidate(i))
            row[lane + "_ms"] = (time.perf_counter_ns() - start) / 1e6
            outputs[lane] = digest(result.outputs)
            row[lane + "_counters"] = result.stats
            if not result.succeeded:
                raise AssertionError(name + ": INCOMPLETE_GRAPH")
        row["outputs_equal"] = outputs["baseline"] == outputs["candidate"]
        row["output_sha256"] = outputs["candidate"]
        if not row["outputs_equal"]:
            raise AssertionError(name + ": GRAPH_OUTPUT_MISMATCH")
        rows.append(row)
    return finish_comparison(name, rows, list(limitations), workload)


def synthetic_snapshot():
    houses, spheres, nodes = {}, {}, {}
    for h in range(1, 13):
        hid = f"H{h:02d}"
        houses[hid] = {"id": hid, "name": f"SYNTHETIC House {h}", "children": []}
        for s in range(1, 13):
            sid = f"{hid}.S{s:02d}"
            houses[hid]["children"].append(sid)
            spheres[sid] = {"id": sid, "name": f"SYNTHETIC Sphere {h}-{s}",
                            "parent": hid, "children": []}
            for n in range(1, 13):
                nid = f"{sid}.N{n:02d}"
                spheres[sid]["children"].append(nid)
                node = {"id": nid, "name": f"SYNTHETIC subject{h} method{s} sample{n}",
                        "parent": sid, "kind": "DOMAIN_SPECIALIZATION" if s <= 7 else "EPISTEMIC_META"}
                node["source_record_sha256"] = digest(node)
                nodes[nid] = node
    raw_digest = digest({"houses": houses, "spheres": spheres, "nodes": nodes})
    return SimpleNamespace(houses=houses, spheres=spheres, nodes=nodes,
                           node_ids=tuple(sorted(nodes)), sphere_ids=tuple(sorted(spheres)),
                           registry_sha=raw_digest, topics_sha=None, topic_rows=[])


def count_sql(fn, connections):
    counts = Counter()
    for name, db in connections.items():
        db.set_trace_callback(lambda query, name=name: counts.update(
            [name + ":" + query.lstrip().split(None, 1)[0].upper()]))
    try:
        fn()
    finally:
        for db in connections.values():
            db.set_trace_callback(None)
    return dict(sorted(counts.items()))


def memory_benchmarks(snapshot, scope, runtime, repeats, temporary, *, include_legacy=True):
    db = initialize_db(Path(temporary) / "knowledge.sqlite", snapshot)
    source_topics = bool(snapshot.topic_rows)
    if not source_topics:
        topics, edges = [], []
        for i, nid in enumerate(snapshot.node_ids):
            for rank in (1, 2):
                tid = f"T{10000 + 2 * i + rank}"
                topics.append((tid, f"SYNTHETIC topic {i}-{rank}", "SYNTHETIC_UNREVIEWED"))
                edges.append((tid, nid, rank, "SYNTHETIC_UNREVIEWED"))
        db.executemany("INSERT INTO topics VALUES(?,?,?)", topics)
        db.executemany("INSERT INTO topic_candidates VALUES(?,?,?,?)", edges)
        db.commit()
    memory = LocalMemory(Path(temporary) / "memory.sqlite")
    for i, sid in enumerate(snapshot.sphere_ids):
        nid = snapshot.spheres[sid]["children"][0]
        row = db.execute("SELECT topic_id FROM topic_candidates WHERE hsn=? ORDER BY topic_id LIMIT 1",
                         (nid,)).fetchone()
        memory.append({"event_id": f"beast-benchmark-{i:03d}", "mode": "WORK",
                       "scope": "SYNTHETIC_LOCAL_REVIEW", "coordinate": nid,
                       "topic_id": row[0] if row else None,
                       "action": "NOTE" if i % 2 == 0 else "CHALLENGE",
                       "source_ref": "urn:atlas:synthetic:beast20-memory-benchmark",
                       "source_digest": scope.source_digest})
    checkpoint = memory.verify()
    coordinates = list(snapshot.node_ids)
    anchor = {"expected_tip": checkpoint["tip"], "expected_count": checkpoint["count"]}

    def legacy(_=0):
        # The current public API requires an independent checkpoint for every
        # memory projection. This comparator is now a repeated anchored scan;
        # historical unanchored results remain in the immutable initial report.
        return {nid: topic_view(db, nid, memory, memory_checkpoint=anchor)
                for nid in coordinates}

    def r10(_=0):
        batch = memory.verified_triage_batch(coordinates, expected_tip=checkpoint["tip"],
                                             expected_count=checkpoint["count"])
        class BatchAdapter:
            def verified_triage_batch(self, selected, *, expected_tip, expected_count):
                if (expected_tip, expected_count) != (anchor["expected_tip"], anchor["expected_count"]):
                    raise ValueError("CHECKPOINT_CHANGED")
                return {coordinate: batch[coordinate] for coordinate in selected}
        adapter = BatchAdapter()
        return {nid: topic_view(db, nid, adapter, memory_checkpoint=anchor)
                for nid in coordinates}

    def combined(_=0):
        return runtime.topic_views(db, memory, coordinates, expected_tip=checkpoint["tip"],
                                   expected_count=checkpoint["count"])

    workload = {"coordinates": len(coordinates), "synthetic_review_events": checkpoint["count"],
                "topic_count": db.execute("SELECT COUNT(*) FROM topics").fetchone()[0],
                "candidate_edges": db.execute("SELECT COUNT(*) FROM topic_candidates").fetchone()[0],
                "topic_input": "PINNED_HISTORICAL_OPENALEX_CANDIDATES" if source_topics else "SYNTHETIC"}
    connections = {"knowledge": db, "memory": memory.db}
    try:
        results = []
        if include_legacy:
            results.append(paired("repeated_checkpoint_topic_loop_vs_r10_verified_batch", legacy, r10, repeats,
                   workload=workload, limitations=[
                       "Current repeated-scan comparator verifies the checkpoint for every coordinate; historical unanchored results are retained separately.",
                       "R10 verifies once and retains existing per-coordinate topic queries.",
                       "Synthetic reviews affect ordering only; topic candidates remain unreviewed."]))
        results.append(paired("r10_verified_memory_vs_beast20_batched_topic_views", r10, combined, repeats,
                   workload=workload, limitations=[
                       "Baseline is the current optimized R10 verified memory API, not the older raw scans.",
                       "BEAST20 additionally verifies at return and uses bounded topic SQL batches.",
                       "Authorization callbacks are local test callbacks, not live host authentication."]))
        counters = {"r10": count_sql(r10, connections),
                    "beast20": count_sql(combined, connections)}
        if include_legacy:
            counters["legacy"] = count_sql(legacy, connections)
        for item in results:
            item["untimed_observed_sql_counts"] = counters
        return results
    finally:
        memory.close()
        db.close()


def physics_benchmarks(repeats):
    scope = Scope(REGISTRY_SHA, "ariadne-reader/v0.7", "local-benchmark", 1)
    plate = Plate()
    addresses = [f"H{h:02d}.S{s:02d}.N01" for h in range(1, 13) for s in (1, 12)]
    options = {"plate": plate, "drive_hz": 55.0, "grid": 17, "max_mode": 4}
    def baseline(_=0):
        return [prepare_reasoning_context(hsn=nid, gf7=positional_gf7(nid), **options)
                for nid in addresses]
    cold_counters = []
    def cold(_=0):
        with ArtifactStore() as store:
            runtime = AtlasBeastRuntime(scope, store, lambda scope, phase: True)
            output = [runtime.reasoning_context(hsn=nid, gf7=positional_gf7(nid), **options)
                      for nid in addresses]
            cold_counters.append(dict(runtime.stats))
            return output
    with ArtifactStore() as store:
        runtime = AtlasBeastRuntime(scope, store, lambda scope, phase: True)
        def warm(_=0):
            return [runtime.reasoning_context(hsn=nid, gf7=positional_gf7(nid), **options)
                    for nid in addresses]
        warm()  # Explicit cache warmup, outside timing.
        workload = {"contexts": 24, "distinct_plates": 1, "distinct_drives": 1,
                    "grid": 17, "max_mode": 4, "drive_hz": 55.0,
                    "source": "REAL_GF8_ANALYTIC_COMPUTATIONS_WITH_AUTHORED_REQUESTS"}
        common = ["Exact reasoning-packet parity includes per-coordinate receipts.",
                  "Reuse is valid only for identical physics inputs; changing a material/drive changes the key.",
                  "Local analytic CPU model; no physical acoustic processor, GPT inference or hosted latency."]
        cold_result = paired("gf8_uncached_vs_cold_batch_physics_reuse", baseline, cold, repeats,
                             workload=workload, limitations=common + [
                                 "Candidate timing includes a fresh in-memory store and runtime per batch."])
        cold_result["observed_candidate_counters_per_call_including_warmup"] = cold_counters
        before = dict(runtime.stats)
        warm_result = paired("gf8_uncached_vs_prepopulated_physics_reuse", baseline, warm, repeats,
                             workload=workload, limitations=common + ["Candidate cache is prepopulated before timing."])
        warm_result["observed_candidate_counters_before"] = before
        warm_result["observed_candidate_counters_after"] = dict(runtime.stats)
        return [cold_result, warm_result]


def storage_benchmarks(snapshot, scope, repeats):
    # Original source records and names stay local; the report includes digests only.
    with ArtifactStore() as store:
        rows = [(nid, canonical_bytes(snapshot.nodes[nid])) for nid in snapshot.node_ids]
        digests = [store.put_object(scope, raw) for _, raw in rows]
        objects = paired("source_objects_individual_vs_bounded_batch_get",
                         lambda _: [store.get_object(scope, d) for d in digests],
                         lambda _: store.batch_get(scope, digests), repeats,
                         projection=lambda result: [hashlib.sha256(raw).hexdigest() for raw in result],
                         workload={"objects": len(rows), "unique_digests": len(set(digests)),
                                   "source_bytes": sum(len(raw) for _, raw in rows)},
                         limitations=["Both paths verify exact bytes against SHA-256.",
                                      "Source insertion/setup is excluded from retrieval timing."])
        docs = []
        for nid in snapshot.node_ids:
            text = snapshot.nodes[nid]["name"]
            docs.append((nid, text, search_terms(text)))
            store.upsert_document(scope, nid, text, polarity="RELATED")
        query_texts = [snapshot.nodes[nid]["name"] for nid in snapshot.node_ids[::72]]
        queries = [(text, search_terms(text)) for text in query_texts]
        def linear(_):
            results = []
            for _, terms in queries:
                hits = [(nid, len(tokens & terms)) for nid, _, tokens in docs]
                results.append(sorted(((nid, score) for nid, score in hits if score),
                                      key=lambda x: (-x[1], x[0]))[:20])
            return results
        def indexed(_):
            return [[(row["id"], row["score"]) for row in store.search(scope, text, limit=20)]
                    for text, _ in queries]
        search = paired("source_names_preparsed_linear_vs_persistent_inverted_index",
                        linear, indexed, repeats,
                        workload={"documents": len(docs), "queries": len(queries),
                                  "query_texts_sha256": digest(query_texts), "limit": 20},
                        limitations=[
                            "Baseline tokens are already parsed; this is a competitive in-memory linear baseline.",
                            "Persistent index additionally retrieves and verifies source bytes/metadata.",
                            "Output comparison uses exact ordered IDs/scores; no semantic-relevance improvement is inferred.",
                            "SQLite overhead can make the indexed route slower for a small or broad-query corpus."])
        return [objects, search]


async def cascade_benchmarks(snapshot, scope, runtime, repeats, temporary):
    compiler = CascadeCompiler(snapshot)
    handlers = compiler.handlers()
    warm_executor = AsyncExecutor(":memory:", handlers, scope_key=scope.key, workers=12)
    cold_stats = await runtime.run_cascade(compiler, warm_executor)
    if not cold_stats.succeeded or cold_stats.stats["executed"] != 1885:
        raise AssertionError("INITIAL_CASCADE_INCOMPLETE")
    async def fresh(_=0, node_inputs=None):
        executor = AsyncExecutor(":memory:", handlers, scope_key=scope.key, workers=12)
        try:
            return await runtime.run_cascade(compiler, executor, node_inputs=node_inputs)
        finally:
            executor.close()
    async def warm(_=0):
        return await runtime.run_cascade(compiler, warm_executor)
    workload = {"nodes": 1728, "spheres": 144, "houses": 12, "meta": 1,
                "total_jobs": 1885, "workers": 12, "handler_type": "LOCAL_SYNCHRONOUS_LEXICAL_AND_DIGEST"}
    common = ["Jobs are actual source-text/digest reductions, not model calls or resident turns.",
              "Synchronous CPU handlers do not gain multicore parallelism from asyncio.",
              "Timings include task construction, integrity checks, scheduling and checkpoint operations."]
    try:
        warm_result = await paired_async("full_cascade_rebuild_vs_verified_job_reuse",
                                         fresh, warm, repeats, workload=workload,
                                         limitations=common + ["Each baseline uses a fresh in-memory checkpoint DB."])
        if any(row["candidate_counters"]["executed"] != 0 for row in warm_result["raw_pairs"]):
            raise AssertionError("WARM_CASCADE_REEXECUTED_HANDLER")
        def perturbation(i):
            return {snapshot.node_ids[0]: {"benchmark_supplement_revision": i + 1}}
        async def fresh_changed(i):
            return await fresh(i, perturbation(i))
        async def incremental(i):
            return await runtime.run_cascade(compiler, warm_executor, node_inputs=perturbation(i))
        changed = await paired_async("full_rebuild_vs_one_node_supplement_change", fresh_changed,
                                     incremental, repeats, workload={**workload, "changed_inputs": 1},
                                     limitations=common + [
                                         "Supplemental computation input changes; original source bytes and CANON stay fixed.",
                                         "Each pair uses a never-before-seen supplement revision; cache reuse cannot hide updates."])
        if any(row["candidate_counters"]["executed"] != 4 for row in changed["raw_pairs"]):
            raise AssertionError("INCREMENTAL_CASCADE_DID_NOT_RECOMPUTE_EXACTLY_FOUR")
        persistent = Path(temporary) / "cascade-restart.sqlite"
        first = AsyncExecutor(persistent, handlers, scope_key=scope.key, workers=12)
        original = await runtime.run_cascade(compiler, first)
        first.close()
        second = AsyncExecutor(persistent, handlers, scope_key=scope.key, workers=12)
        try:
            start = time.perf_counter_ns()
            resumed = await runtime.run_cascade(compiler, second)
            restart_ms = (time.perf_counter_ns() - start) / 1e6
        finally:
            second.close()
        if (not resumed.succeeded or resumed.stats["executed"] != 0 or
                digest(original.outputs) != digest(resumed.outputs)):
            raise AssertionError("RESTART_REPLAY_OR_OUTPUT_MISMATCH")
        restart = {"name": "persistent_cascade_restart", "workload": workload,
                   "elapsed_ms": restart_ms, "initial_counters": original.stats,
                   "restart_counters": resumed.stats, "outputs_equal": True,
                   "output_sha256": digest(resumed.outputs),
                   "limitation": "One functional restart observation, not a paired latency speedup claim."}
        return [warm_result, changed], restart
    finally:
        warm_executor.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", type=Path)
    parser.add_argument("--topics", type=Path)
    parser.add_argument("--repeats", type=int, default=5)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--sections", nargs="+", choices=("memory", "memory-current", "physics", "storage", "cascade"),
                        default=["memory", "physics", "storage", "cascade"],
                        help="memory-current omits the slow legacy scan baseline")
    parser.add_argument("--merge-from", type=Path,
                        help="Retain previous scenarios and replace only newly measured scenario names")
    args = parser.parse_args()
    if not 3 <= args.repeats <= 15:
        parser.error("--repeats must be 3..15")
    if args.topics and not args.registry:
        parser.error("--topics requires --registry")
    before = source_manifest()
    if before != IMPORT_SOURCE_MANIFEST:
        raise RuntimeError("SOURCE_CHANGED_DURING_IMPORT")
    snapshot = SourceSnapshot(args.registry, args.topics) if args.registry else synthetic_snapshot()
    scope = Scope(snapshot.registry_sha, "ariadne-reader/v0.7" if args.registry else "SYNTHETIC_BEAST20/v1",
                  "local-benchmark", 1)
    report = {"schema": "atlas.beast20.benchmark/v2", "created_utc": datetime.now(timezone.utc).isoformat(),
              "environment": {"python": sys.version, "sqlite": sqlite3.sqlite_version,
                              "platform": platform.platform(), "clock": "perf_counter_ns"},
              "dataset": {"kind": "EXACT_PINNED_ARIADNE_V07" if args.registry else "SYNTHETIC_TOPOLOGY_FIXTURE",
                          "registry_sha256": snapshot.registry_sha, "topics_sha256": snapshot.topics_sha},
              "method": {"paired_order": "alternating baseline-first/candidate-first",
                         "p95": "nearest rank; small paired sample, descriptive only",
                         "ratios": "median baseline divided by median candidate; never multiplied",
                         "warmups": "one untimed paired parity pass except graph scenarios",
                         "setup": "described separately per workload; no artificial sleeps"},
              "comparisons": [], "functional_observations": [],
              "claim_limits": ["Local Python/SQLite performance only.",
                               "No hosted authorization, model-quality, physical cymatics or universal superiority measurement.",
                               "Cold setup and full-source invalidation remain real costs.",
                               "Negative results are retained; source text is not included in this report."]}
    with tempfile.TemporaryDirectory(prefix="atlas-beast20-benchmark-") as temporary, ArtifactStore() as store:
        runtime = AtlasBeastRuntime(scope, store, lambda scope, phase: True)
        if "memory" in args.sections or "memory-current" in args.sections:
            print("Running memory comparisons", flush=True)
            report["comparisons"].extend(memory_benchmarks(
                snapshot, scope, runtime, args.repeats, temporary, include_legacy="memory" in args.sections))
        if "physics" in args.sections:
            print("Running GF8 comparisons", flush=True)
            report["comparisons"].extend(physics_benchmarks(args.repeats))
        if "storage" in args.sections:
            print("Running exact-source storage/search comparisons", flush=True)
            report["comparisons"].extend(storage_benchmarks(snapshot, scope, args.repeats))
        if "cascade" in args.sections:
            print("Running 1,885-job cascade comparisons and restart", flush=True)
            comparisons, restart = asyncio.run(cascade_benchmarks(snapshot, scope, runtime, args.repeats, temporary))
            report["comparisons"].extend(comparisons)
            report["functional_observations"].append(restart)
        report["observed_runtime_stats"] = dict(runtime.stats)
    after = source_manifest()
    if before != after:
        raise RuntimeError("SOURCE_CHANGED_DURING_BENCHMARK")
    pass_id = "source-" + digest(after)[:16]
    report["measurement_passes"] = [{"id": pass_id, "sections": args.sections,
                                      "created_utc": report["created_utc"],
                                      "source_manifest_before": before,
                                      "source_manifest_after": after,
                                      "source_manifests_equal": True}]
    for item in report["comparisons"] + report["functional_observations"]:
        item["measurement_pass"] = pass_id
    if args.merge_from:
        previous_bytes = args.merge_from.read_bytes()
        previous = json.loads(previous_bytes)
        if previous["dataset"] != report["dataset"]:
            raise ValueError("MERGE_DATASET_MISMATCH")
        prior_passes = previous.get("measurement_passes") or [{
            "id": "initial-before-source-manifests", "created_utc": previous["created_utc"],
            "source_manifests_equal": None,
            "note": "Initial measurement; source-file manifests were not captured during that pass."}]
        report["measurement_passes"] = prior_passes + report["measurement_passes"]
        for section in ("comparisons", "functional_observations"):
            replacements = {item["name"]: item for item in report[section]}
            for item in previous[section]:
                if item["name"] not in replacements:
                    replacements[item["name"]] = {**item,
                        "measurement_pass": item.get("measurement_pass", "initial-before-source-manifests")}
            previous_order = [item["name"] for item in previous[section]]
            order = previous_order + [key for key in replacements if key not in previous_order]
            report[section] = [replacements[key] for key in order]
        report["preserved_prior_report"] = {"filename": args.merge_from.name,
                                             "sha256": hashlib.sha256(previous_bytes).hexdigest(),
                                             "meaning": "Prior raw measurements remain intact in this separate artifact."}
    report["all_output_comparisons_equal"] = all(item["all_outputs_equal"] for item in report["comparisons"])
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False) + "\n")
    print(json.dumps({"output": str(args.output), "all_outputs_equal": report["all_output_comparisons_equal"],
                      "ratios": {item["name"]: item["median_ratio_baseline_over_candidate"]
                                 for item in report["comparisons"]}}, indent=2))


if __name__ == "__main__":
    main()
