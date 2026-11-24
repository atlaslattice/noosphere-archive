"""Source-bound, repeated synthetic workload evolution; never model turns.

The C++ engine performs every reported timeline-year transition. One year means
one synthetic request/admission/cache transition, not a predicted calendar year
or an execution of the complete Atlas graph. Epochs restart independent workload
states; a training-only incumbent evolves across their accumulated evidence.

Only immutable source coordinates, record digests, roles and aggregate counters
are exported. Original node bodies remain in the caller's verified snapshot.
"""
from __future__ import annotations

from collections import OrderedDict
import gzip
import hashlib
import io
import json
from pathlib import Path
import re
import shutil
import statistics
import subprocess
import tempfile
from typing import Any

from ..core import SourceSnapshot
from ..glyph import REGISTRY_SHA
from .strategy_lab import BATCH_SIZES, CACHE_ENTRIES, _validated_trace

SCHEMA = "atlas.beast20.long-horizon/v1"
BUNDLE_SCHEMA = "atlas.beast20.long-horizon-bundle/v1"
ENGINE_VERSION = 1
NODES = 1728
MAX_EPOCHS = 1729
MAX_YEARS = 1728
MAX_SAFE_INTEGER = 9_007_199_254_740_991
MAX_REPORT_BYTES = 32 * 1024 * 1024
MASK64 = (1 << 64) - 1
DEFAULT_SEED = 1451728
BASELINE_INDEX = 143
ORIGINAL_REFERENCES_SHA256 = "caf2585985c6796fbb6526cc67c3126baff21dd2ab3fda29fa49e99fae5577c2"
DEFAULT_TRACE_FILE_SHA256 = "e00022cd1660518af2338c30d9347b71a1effdc1d2882ad743da5d39fbf28232"
METRICS = ("requests", "freshCompletions", "heldRequests", "cacheHits", "cacheMisses",
           "sourceChanges", "globalInvalidations", "metadataObjectsRead",
           "predictedServiceNs", "predictedRequiredNs", "predictedHeldServiceNs",
           "freshnessViolations")
REGIMES = (
    ("STABLE_HOTSET_12", "Repeated requests across twelve source-bound keys."),
    ("STABLE_HOTSET_144", "Repeated requests across 144 source-bound keys."),
    ("UNIFORM_1728", "Uniform seeded requests across all source nodes."),
    ("FULL_SOURCE_SCAN", "One deterministic pass over every original node."),
    ("BURST_REUSE", "Twelve requests per key before advancing through 48 keys."),
    ("HOTSET_512", "Repeated requests across 512 source-bound keys."),
    ("LOCAL_REVISION_CHURN", "Invalidate the requested supplemental input every eighth step."),
    ("GLOBAL_REVISION_CHURN", "Invalidate all memo keys and reread source metadata every 64 steps."),
    ("SCARCE_SERVICE_BUDGET", "Request service receives two fifths of the calibrated median miss cost per step."),
    ("ABUNDANT_SERVICE_BUDGET", "Request service receives eight calibrated median miss costs per step."),
    ("SOURCE_UNAVAILABLE", "One in 32 seeded source checks holds work without returning a result."),
    ("FREQUENT_SOURCE_RECHECK", "Invalidate memo keys and reread source metadata every sixteen steps."),
)
_SHA = re.compile(r"[a-f0-9]{64}\Z")
_ROOT = Path(__file__).resolve().parents[2]
_ENGINE = _ROOT / "benchmarks/native1728_evolution/engine.cpp"
_IMPORTED_MODULE_SHA256 = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()


def _integer(value, low=0, high=MAX_SAFE_INTEGER, error="LONG_HORIZON_INTEGER_INVALID"):
    if type(value) is not int or not low <= value <= high:
        raise ValueError(error)
    return value


def _sha(value):
    if type(value) is not str or not _SHA.fullmatch(value):
        raise ValueError("LONG_HORIZON_SHA256_INVALID")
    return value


def _exact(value, fields, error="LONG_HORIZON_UNDECLARED_FIELDS"):
    if type(value) is not dict or set(value) != set(fields):
        raise ValueError(error)


def _assert_module_identity():
    if hashlib.sha256(Path(__file__).read_bytes()).hexdigest() != _IMPORTED_MODULE_SHA256:
        raise ValueError("LONG_HORIZON_MODULE_CHANGED_AFTER_IMPORT")


def canonical_json(value):
    """Stable ASCII JSON; all public counters are safe integers, never NaN."""
    return json.dumps(value, sort_keys=True, ensure_ascii=True, separators=(",", ":"), allow_nan=False)


def digest(value):
    return hashlib.sha256(canonical_json(value).encode("ascii")).hexdigest()


def _safe_json(value, depth=0):
    if depth > 24:
        raise ValueError("LONG_HORIZON_JSON_DEPTH")
    if value is None or type(value) is bool:
        return
    if type(value) is int:
        _integer(value)
    elif type(value) is str:
        if len(value) > 8192:
            raise ValueError("LONG_HORIZON_STRING_BOUND")
    elif type(value) is list:
        if len(value) > 10_000:
            raise ValueError("LONG_HORIZON_ARRAY_BOUND")
        for item in value:
            _safe_json(item, depth + 1)
    elif type(value) is dict:
        if len(value) > 100 or any(type(k) is not str or len(k) > 128 for k in value):
            raise ValueError("LONG_HORIZON_OBJECT_BOUND")
        for item in value.values():
            _safe_json(item, depth + 1)
    else:
        raise ValueError("LONG_HORIZON_NONFINITE_OR_NONINTEGER_JSON")


def candidate_id(index):
    _integer(index, 0, 1727)
    return f"CFG.W{index // 144 + 1:02d}.M{index // 12 % 12 + 1:02d}.B{index % 12 + 1:02d}"


def controls(index):
    _integer(index, 0, 1727)
    return {"workers": index // 144 + 1, "maxMemoEntries": CACHE_ENTRIES[index // 12 % 12],
            "chunkSize": BATCH_SIZES[index % 12]}


def empty_metrics():
    return dict.fromkeys(METRICS, 0)


def metric_record(values):
    if type(values) is not list or len(values) != len(METRICS):
        raise ValueError("LONG_HORIZON_METRIC_VECTOR")
    return {key: _integer(value) for key, value in zip(METRICS, values)}


def sum_metrics(rows):
    out = empty_metrics()
    for row in rows:
        for key in METRICS:
            out[key] += row[key]
            _integer(out[key])
    return out


def source_references(snapshot):
    if not isinstance(snapshot, SourceSnapshot) or snapshot.registry_sha != REGISTRY_SHA:
        raise ValueError("LONG_HORIZON_VERIFIED_ORIGINAL_SOURCE_REQUIRED")
    if (len(snapshot.nodes), len(snapshot.spheres), len(snapshot.houses)) != (1728, 144, 12):
        raise ValueError("LONG_HORIZON_SOURCE_CARDINALITY")
    rows = []
    for h in range(1, 13):
        for s in range(1, 13):
            for n in range(1, 13):
                nid = f"H{h:02d}.S{s:02d}.N{n:02d}"
                row = snapshot.nodes[nid]
                kind = "DOMAIN_SPECIALIZATION" if s <= 7 else "EPISTEMIC_META"
                if row["id"] != nid or row["parent"] != nid[:7] or row["kind"] != kind:
                    raise ValueError("LONG_HORIZON_ORIGINAL_HIERARCHY")
                rows.append({"id": nid, "parent": row["parent"],
                             "recordSha256": _sha(row["source_record_sha256"]), "kind": row["kind"]})
    if digest(rows) != ORIGINAL_REFERENCES_SHA256:
        raise ValueError("LONG_HORIZON_ORIGINAL_REFERENCE_PIN_MISMATCH")
    return rows


def load_calibration(snapshot, trace_path, *, expected_trace_file_sha256=DEFAULT_TRACE_FILE_SHA256):
    """Verify frozen bytes and trace/source identity; never recalibrate here."""
    source_references(snapshot)
    _sha(expected_trace_file_sha256)
    raw = Path(trace_path).read_bytes()
    if len(raw) > 16 * 1024 * 1024 or hashlib.sha256(raw).hexdigest() != expected_trace_file_sha256:
        raise ValueError("LONG_HORIZON_TRACE_FILE_MISMATCH")
    if Path(trace_path).suffix == ".gz":
        with gzip.GzipFile(fileobj=io.BytesIO(raw)) as stream:
            raw = stream.read(16 * 1024 * 1024 + 1)
        if len(raw) > 16 * 1024 * 1024:
            raise ValueError("LONG_HORIZON_TRACE_DECOMPRESSED_BOUND")
    envelope = json.loads(raw)
    body, _ = _validated_trace(envelope, envelope["sha256"], snapshot.registry_sha, "ariadne-v0.7")
    if body.get("source_fixture_kind") != "PINNED_ORIGINAL_ARIADNE" or body["measurement_kind"] != "MEASURED_HANDLER_SERVICE_TIMES":
        raise ValueError("LONG_HORIZON_MEASURED_ORIGINAL_TRACE_REQUIRED")
    if any(task["async_wait_ns"] for scenario in body["scenarios"] for task in scenario["tasks"]):
        raise ValueError("LONG_HORIZON_ASYNC_TRACE_UNSUPPORTED")
    first = body["scenarios"][0]["tasks"]
    by_id = {task["task_id"]: task for task in first}
    if any(nid not in by_id for nid in snapshot.node_ids):
        raise ValueError("LONG_HORIZON_NODE_CALIBRATION_MISSING")
    c = body["calibration"]
    calibration = {"lookup": c["memo_lookup_ns"], "store": c["memo_store_ns"],
                   "fixed": c["batch_fixed_ns"], "item": c["batch_item_ns"],
                   "cpu": [by_id[nid]["cpu_ns"] for nid in snapshot.node_ids]}
    _validate_calibration(calibration)
    return calibration, {"traceFileSha256": expected_trace_file_sha256,
                         "tracePayloadSha256": envelope["sha256"]}


def _validate_calibration(calibration):
    if type(calibration) is not dict or set(calibration) != {"lookup", "store", "fixed", "item", "cpu"}:
        raise ValueError("LONG_HORIZON_CALIBRATION_FIELDS")
    for key in ("lookup", "store", "fixed", "item"):
        _integer(calibration[key], 0, 10**9)
    cpu = calibration["cpu"]
    if type(cpu) is not list or len(cpu) != NODES:
        raise ValueError("LONG_HORIZON_CALIBRATION_CARDINALITY")
    for value in cpu:
        _integer(value, 1, 10**9)
    # A conservative bound for even every step rereading the complete catalog.
    max_step = sum(calibration[k] for k in ("lookup", "store", "fixed", "item")) + max(cpu)
    max_step += NODES * (calibration["fixed"] + calibration["item"])
    if max_step * MAX_EPOCHS * MAX_YEARS > MAX_SAFE_INTEGER:
        raise ValueError("LONG_HORIZON_SAFE_INTEGER_BUDGET")
    return calibration


def _mix64(value):
    z = (value + 0x9E3779B97F4A7C15) & MASK64
    z = ((z ^ (z >> 30)) * 0xBF58476D1CE4E5B9) & MASK64
    z = ((z ^ (z >> 27)) * 0x94D049BB133111EB) & MASK64
    return z ^ (z >> 31)


def workload_events(epoch, years, seed, calibration):
    """Independent readable reference generator, mirrored in the native loop."""
    _integer(epoch, 0, MAX_EPOCHS - 1)
    _integer(years, 1, MAX_YEARS)
    _integer(seed, 0, MAX_SAFE_INTEGER)
    _validate_calibration(calibration)
    base = sum(calibration[k] for k in ("lookup", "store", "fixed", "item")) + sorted(calibration["cpu"])[NODES // 2]
    regime = epoch % 12
    offset = _mix64(seed ^ epoch) % NODES
    hotsets = (12, 144, 1728, 1728, 48, 512, 144, 512, 144, 1728, 144, 512)
    out = []
    for y in range(years):
        r = _mix64(seed ^ ((epoch * 0xD1342543DE82EF95) & MASK64) ^ y)
        node = (offset + r % hotsets[regime]) % NODES
        if regime == 3:
            node = y % NODES
        if regime == 4:
            node = (offset + (y // 12) % 48) % NODES
        budget = base * 2
        if regime == 8:
            budget = max(1, base * 2 // 5)
        if regime == 9:
            budget = base * 8
        out.append({"node": node, "local": regime == 6 and y % 8 == 0,
                    "global": y == 0 or regime == 7 and y % 64 == 0 or regime == 11 and y % 16 == 0,
                    "unavailable": regime == 10 and r % 32 == 0, "budget": budget})
    return out


def reference_epoch(index, events, calibration):
    """Straightforward OrderedDict oracle, not used to inflate full-run counts."""
    config = controls(index)
    _validate_calibration(calibration)
    cache = OrderedDict()
    revisions = [0] * NODES
    metrics, covered_nodes = empty_metrics(), set()
    tokens = events[0]["budget"] * 2 if events else 0
    checksum = 1469598103934665603
    for event in events:
        n = _integer(event["node"], 0, NODES - 1)
        budget = _integer(event["budget"], 1)
        m = empty_metrics()
        m["requests"] = 1
        if event["global"]:
            cache.clear()
            m["globalInvalidations"] = m["sourceChanges"] = 1
            m["metadataObjectsRead"] = NODES
            catalog = calibration["fixed"] * ((NODES + config["chunkSize"] - 1) // config["chunkSize"]) + calibration["item"] * NODES
            m["predictedServiceNs"] = m["predictedRequiredNs"] = catalog
        if event["local"]:
            revisions[n] += 1
            cache.pop(n, None)
            m["sourceChanges"] += 1
        tokens = min(tokens + budget, budget * 8)
        hit = n in cache
        if hit and cache[n] != revisions[n]:
            m["freshnessViolations"] += 1
            hit = False
        cost = calibration["lookup"]
        if not hit:
            cost += calibration["cpu"][n] + calibration["store"] + calibration["fixed"] + calibration["item"]
        m["predictedRequiredNs"] += cost
        accepted = not event["unavailable"] and tokens >= cost
        if accepted:
            tokens -= cost
            cache.pop(n, None)
            if len(cache) == config["maxMemoEntries"]:
                cache.popitem(last=False)
            cache[n] = revisions[n]
            m["freshCompletions"] = 1
            m["cacheHits" if hit else "cacheMisses"] = 1
            m["metadataObjectsRead"] += not hit
            m["predictedServiceNs"] += cost
            covered_nodes.add(n)
        else:
            m["heldRequests"] = 1
            m["predictedHeldServiceNs"] = cost
        metrics = sum_metrics((metrics, m))
        tag = n * 257 + int(accepted) + 2 * int(hit) + 4 * int(event["local"]) + 8 * int(event["global"]) + 16 * int(event["unavailable"])
        checksum = ((checksum ^ tag) * 1099511628211) & MASK64
    return {"metrics": metrics, "coverage": covered_nodes, "checksum": f"{checksum:016x}"}


def compile_engine(output_path):
    """Compile only the fixed local source; never fetch a compiler or package."""
    compiler = shutil.which("g++")
    if not compiler:
        raise RuntimeError("LONG_HORIZON_LOCAL_GXX_REQUIRED")
    _assert_module_identity()
    source_before = hashlib.sha256(_ENGINE.read_bytes()).hexdigest()
    flags = ["-std=c++17", "-O3", "-DNDEBUG", "-fopenmp"]
    subprocess.run([compiler, *flags, str(_ENGINE), "-o", str(output_path)], check=True, timeout=60,
                   stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    version = subprocess.run([compiler, "--version"], check=True, timeout=10, capture_output=True, text=True).stdout.splitlines()[0]
    if hashlib.sha256(_ENGINE.read_bytes()).hexdigest() != source_before:
        raise ValueError("LONG_HORIZON_ENGINE_SOURCE_CHANGED_DURING_COMPILE")
    _assert_module_identity()
    return {"compiler": version, "compilerFlags": flags,
            "engineSourceSha256": source_before,
            "engineBinarySha256": hashlib.sha256(Path(output_path).read_bytes()).hexdigest()}


def engine_input(calibration, *, epochs=MAX_EPOCHS, years=MAX_YEARS, seed=DEFAULT_SEED,
                 threads=4, indices=None, audit=True):
    _validate_calibration(calibration)
    _integer(epochs, 1, MAX_EPOCHS)
    _integer(years, 1, MAX_YEARS)
    _integer(seed, 0, MAX_SAFE_INTEGER)
    _integer(threads, 1, 4)
    if type(audit) is not bool:
        raise ValueError("LONG_HORIZON_AUDIT_FLAG")
    indices = list(range(NODES)) if indices is None else indices
    if type(indices) is not list or not 1 <= len(indices) <= NODES or len(set(indices)) != len(indices):
        raise ValueError("LONG_HORIZON_CANDIDATE_INDICES")
    for index in indices:
        _integer(index, 0, NODES - 1)
    lines = [f"{epochs} {years} {threads} {seed} {len(indices)} {int(audit)}",
             " ".join(map(str, indices)), " ".join(str(calibration[k]) for k in ("lookup", "store", "fixed", "item")),
             " ".join(map(str, calibration["cpu"]))]
    return "\n".join(lines) + "\n"


def execute_engine(binary, calibration, *, timeout_seconds=3600, expected_binary_sha256=None, **kwargs):
    _integer(timeout_seconds, 1, 7200)
    _assert_module_identity()
    binary_before = hashlib.sha256(Path(binary).read_bytes()).hexdigest()
    if expected_binary_sha256 is not None and binary_before != _sha(expected_binary_sha256):
        raise ValueError("LONG_HORIZON_ENGINE_BINARY_IDENTITY")
    result = subprocess.run([str(binary)], input=engine_input(calibration, **kwargs),
                            capture_output=True, text=True, check=True, timeout=timeout_seconds)
    if hashlib.sha256(Path(binary).read_bytes()).hexdigest() != binary_before:
        raise ValueError("LONG_HORIZON_ENGINE_BINARY_CHANGED_DURING_RUN")
    _assert_module_identity()
    if len(result.stdout.encode()) > MAX_REPORT_BYTES:
        raise ValueError("LONG_HORIZON_ENGINE_OUTPUT_BOUND")
    return json.loads(result.stdout)


def _score(row):
    m = row["train"]
    c = row["controls"]
    return (m["freshnessViolations"], -row["coverage"]["trainDistinctSourceNodes"],
            -m["freshCompletions"], m["heldRequests"], m["predictedServiceNs"],
            c["workers"], c["maxMemoEntries"], c["chunkSize"], row["id"])


def _hypotheses(baseline, selected, regimes):
    b, s = baseline["train"], selected["train"]
    observations = {"baselinePredictedServiceNs": b["predictedServiceNs"],
                    "selectedPredictedServiceNs": s["predictedServiceNs"],
                    "baselineFreshCompletions": b["freshCompletions"],
                    "selectedFreshCompletions": s["freshCompletions"]}
    specs = [
        ("memo-capacity", "Measure the selected bounded memo capacity", observations,
         f"Replay max_memo_entries={selected['controls']['maxMemoEntries']} against the baseline with identical outputs.",
         ["Alternating paired real-runtime runs", "Exact output and scope/TTL/LRU parity"]),
        ("batch-width", "Retain verified metadata batching", {"selectedChunkSize": selected["controls"]["chunkSize"], "baselineChunkSize": baseline["controls"]["chunkSize"]},
         "Apply the existing batch_get chunk_size control to source-metadata reads.",
         ["Digest verification on every returned body", "Duplicate/missing object ordering and tamper tests"]),
        ("workers", "Avoid assuming concurrency accelerates synchronous work", {"selectedWorkers": selected["controls"]["workers"], "equivalentWorkerVariants": 12},
         "Use fewer workers for this synchronous service trace; measure genuinely asynchronous work separately.",
         ["Real executor replay", "Async and CPU-bound workloads evaluated independently"]),
        ("revision-invalidation", "Retain dependency invalidation on supplemental changes", {"localChurnFreshnessViolations": regimes[6]["metrics"]["selected"]["freshnessViolations"]},
         "Preserve source and supplemental revision checks before any memo reuse.",
         ["Changed-source invalidation tests", "Measure invalidation traversal costs excluded by this model"]),
        ("source-gate", "Keep unavailable-source work visibly held", {"heldRequests": regimes[10]["metrics"]["selected"]["heldRequests"]},
         "Expose held source checks separately from completed work and block dependent execution.",
         ["Actual host source-gate failure and dependent-blocking tests"]),
        ("admission", "Test quality-first resource admission", {"stressFreshCompletions": regimes[8]["metrics"]["selected"]["freshCompletions"], "stressHeldRequests": regimes[8]["metrics"]["selected"]["heldRequests"]},
         "Prototype bounded admission that never serves stale output to satisfy a latency objective.",
         ["Simulation-only token policy requires a separate implementation", "Queue fairness and bounded waiting tests"]),
        ("workload-partition", "Benchmark cache-heavy and revision-heavy paths separately", {"stableHits": regimes[0]["metrics"]["selected"]["cacheHits"], "revisionHits": regimes[7]["metrics"]["selected"]["cacheHits"]},
         "Keep cold, hotset, scan, churn and source-recheck benchmarks as separate evidence lanes.",
         ["Report all workloads including regressions", "No post-hoc holdout tuning"]),
        ("scope-validation", "Optimize validation overhead without weakening integrity", {"verifiedSourceNodes": 1728},
         "Measure repeated validated scope-key work while retaining validation and content digests on every access.",
         ["Independent old/new measurements", "Mutable scope, expired memo and corrupt body regression cases"]),
    ]
    return [{"id": key, "title": title, "status": "PROPOSED_FROM_SYNTHETIC_EVIDENCE",
             "evidence": evidence, "recommendedAction": action, "validationRequired": validation}
            for key, title, evidence, action, validation in specs]


def _build_report(snapshot, calibration_source, raw, provenance, *, epochs, years, seed, threads):
    _assert_module_identity()
    if hashlib.sha256(_ENGINE.read_bytes()).hexdigest() != provenance["engineSourceSha256"]:
        raise ValueError("LONG_HORIZON_ENGINE_SOURCE_CHANGED_DURING_RUN")
    refs = source_references(snapshot)
    candidates = []
    for expected, row in enumerate(raw["rows"]):
        if row["index"] != expected:
            raise ValueError("LONG_HORIZON_ENGINE_CANDIDATE_ORDER")
        candidates.append({"id": candidate_id(expected), "controls": controls(expected),
                           "train": metric_record(row["train"]), "holdout": metric_record(row["holdout"]),
                           "coverage": {"trainDistinctSourceNodes": row["coverage"][0],
                                        "holdoutDistinctSourceNodes": row["coverage"][1]},
                           "transitionChecksum": row["checksum"]})
    if len(candidates) != NODES:
        raise ValueError("LONG_HORIZON_ENGINE_CANDIDATE_COUNT")
    selected = candidates[raw["selectedIndex"]]
    baseline = candidates[BASELINE_INDEX]
    if min(candidates, key=_score)["id"] != selected["id"]:
        raise ValueError("LONG_HORIZON_SELECTION_PARITY")
    audit = raw["audit"]
    if len(audit["nodes"]) != NODES or len(audit["regimes"]) != 12 or len(audit["trainRegimes"]) != 12:
        raise ValueError("LONG_HORIZON_AUDIT_CARDINALITY")
    for label, candidate in (("baseline", baseline), ("selected", selected)):
        expected = sum_metrics((candidate["train"], candidate["holdout"]))
        if metric_record(audit[label]) != expected:
            raise ValueError("LONG_HORIZON_AUDIT_PARITY")
    nodes = [{**ref, "metrics": {"baseline": metric_record(values[0]), "selected": metric_record(values[1])}}
             for ref, values in zip(refs, audit["nodes"])]
    spheres, houses = [], []
    for h in range(12):
        sphere_rows = []
        for s in range(12):
            children = nodes[h * 144 + s * 12:h * 144 + (s + 1) * 12]
            sid = f"H{h + 1:02d}.S{s + 1:02d}"
            row = {"id": sid, "parent": sid[:3], "nodeIds": [n["id"] for n in children],
                   "metrics": {lane: sum_metrics(n["metrics"][lane] for n in children) for lane in ("baseline", "selected")}}
            sphere_rows.append(row)
            spheres.append(row)
        houses.append({"id": f"H{h + 1:02d}", "sphereIds": [s["id"] for s in sphere_rows],
                       "metrics": {lane: sum_metrics(s["metrics"][lane] for s in sphere_rows) for lane in ("baseline", "selected")}})
    regimes = [{"id": f"R{i + 1:02d}", "name": name, "simulationOnly": True, "description": description,
                "metrics": {"baseline": metric_record(audit["regimes"][i][0]), "selected": metric_record(audit["regimes"][i][1])}}
               for i, (name, description) in enumerate(REGIMES)]
    training_regimes = [{"metrics": {"baseline": metric_record(row[0]), "selected": metric_record(row[1])}}
                        for row in audit["trainRegimes"]]
    for lane, candidate in (("baseline", baseline), ("selected", selected)):
        if sum_metrics(r["metrics"][lane] for r in training_regimes) != candidate["train"]:
            raise ValueError("LONG_HORIZON_TRAINING_REGIME_AUDIT_PARITY")
    epoch_rows = [{"epoch": e[0], "split": "holdout" if e[1] else "train", "regime": f"R{e[0] % 12 + 1:02d}",
                   "epochWinnerCandidateId": None if e[2] == -1 else candidate_id(e[2]),
                   "incumbentCandidateId": candidate_id(e[3]), "acceptedChange": bool(e[4])}
                  for e in raw["epochs"]]
    train_epochs = sum(e["split"] == "train" for e in epoch_rows)
    report = {
        "schema": SCHEMA, "engineVersion": ENGINE_VERSION, "status": "COMPLETED",
        "evidenceKind": "SYNTHETIC_EVOLUTION_EXPERIMENT",
        "source": {"registrySha256": snapshot.registry_sha, "edition": "ariadne-v0.7",
                   "nodeReferencesSha256": digest(refs), "sourceFixtureKind": "PINNED_ORIGINAL_ARIADNE", **calibration_source},
        "counts": {"epochs": epochs, "timelines": NODES, "yearsPerTimeline": years,
                   "representedTimelineYears": epochs * NODES * years,
                   "evaluatedTimelineYearUpdates": raw["evaluatedUpdates"], "nodes": NODES, "spheres": 144, "houses": 12,
                   "trainEpochs": train_epochs, "holdoutEpochs": epochs - train_epochs,
                   "acceptedCandidateChanges": sum(e["acceptedChange"] for e in epoch_rows)},
        "execution": {"method": "DIRECT_STATE_TRANSITIONS", "seed": seed, "threads": threads,
                      "elapsedNs": raw["elapsedNs"], "coreElapsedNs": raw["coreElapsedNs"],
                      "auditReplayUpdates": raw["auditReplayUpdates"], "stateReset": "EACH_EPOCH",
                      "transitionChecksumAlgorithm": "Per-epoch FNV-style 64-bit transition checksum and SplitMix64 fold; not a cryptographic proof.",
                      "pythonSourceSha256": _IMPORTED_MODULE_SHA256, **provenance},
        "candidates": candidates, "nodes": nodes, "spheres": spheres, "houses": houses,
        "meta145": {"selectionStatus": "SELECTED", "selectedCandidateId": selected["id"], "baselineCandidateId": baseline["id"],
                    "trainingObjective": {"qualityOrder": ["minimize freshnessViolations", "maximize trainDistinctSourceNodes", "maximize freshCompletions", "minimize heldRequests", "minimize predictedServiceNs"],
                                          "tieBreak": ["fewer workers", "smaller memo capacity", "smaller chunk width", "stable candidate id"]},
                    "holdout": {"baseline": baseline["holdout"], "selected": selected["holdout"], "usedForSelection": False},
                    "upgradeHypotheses": _hypotheses(baseline, selected, training_regimes)},
        "epochSynthesis": epoch_rows, "regimes": regimes,
        "assumptions": [
            "Each synthetic year is one source-bound request/cache/admission transition, not a calendar year or complete Atlas cascade.",
            "Each epoch resets its workload/cache state; cumulative training evidence changes the incumbent. There is no inherited civilization or autonomous agent state.",
            "The same finite configuration grid is evaluated in every epoch. These are repeated evaluations, not 1729 generations of newly invented algorithms; acceptedCandidateChanges includes the initial selection.",
            "All candidates receive the same seeded events per epoch. Holdout is every fourth 12-epoch block and never selects the incumbent.",
            "Upgrade hypotheses consume training-only overall and regime diagnostics. Holdout observations are reported separately and do not generate proposals.",
            "Existing controls are workers, max_memo_entries and batch_get chunk_size. Request admission budgets and workload regimes are simulation-only.",
            "The baseline is the existing selected build: one worker, 2048 memo entries, and chunk width400. Retaining it is robustness evidence, not an additional speedup.",
            "The measured trace has zero asynchronous wait. One request per step uses one serial service lane, so worker variants have equal modeled work.",
            "Explicit dependency invalidation removes memo keys on supplemental revisions; original registry coordinates and record identities do not change.",
            "Source catalog metadata is reread at epoch start and global invalidation. Its predicted service is included, but this background cost is outside the synthetic request token budget.",
            "Per-node totals attribute all costs of an event, including catalog rereads, to that event's requested node. This is additive operational attribution, not a cost or importance claim about that discipline.",
            "sourceChanges counts supplemental revisions and cold-epoch initializations. It never counts an edit to the pinned original registry, which remains immutable.",
            "Memo lookup/store and metadata batching use frozen local calibration. TTL expiry, invalidation traversal cost, executor overhead and provider behavior are excluded.",
            "Unavailable sources and insufficient request tokens produce held requests, never successful output. Held requests are counted and not automatically retried.",
        ],
        "units": {"time": "nanoseconds", "year": "synthetic workload step", "cost": "predicted calibrated service, not measured latency"},
        "limits": {"maxEpochs": MAX_EPOCHS, "maxYearsPerTimeline": MAX_YEARS, "maxThreads": 4, "maxReportBytes": MAX_REPORT_BYTES},
        "qualityChecks": {"freshnessViolations": sum(c[split]["freshnessViolations"] for c in candidates for split in ("train", "holdout")),
                          "representedEqualsEvaluated": raw["evaluatedUpdates"] == epochs * NODES * years,
                          "baselineAuditMatches": True, "selectedAuditMatches": True, "sourceReferencesComplete": True,
                          "holdoutExcludedFromSelection": True,
                          "allWorkerVariantsEquivalent": all(candidates[i][split] == candidates[i % 144][split] for i in range(NODES) for split in ("train", "holdout")),
                          "allSourceNodesCovered": all(n["metrics"]["selected"]["freshCompletions"] > 0 for n in nodes)},
        "limitations": [
            "Synthetic workload outcomes are not measured runtime speedups or forecasts of civilizations, research quality, or future calendar years.",
            "Freshness proves the declared revision/invalidation model, not semantic correctness of generated answers. No model outputs are produced.",
            "The finite-set selection is conditional on declared workloads, training objective and calibration; no global optimality is claimed.",
            "Source membership grounds workload attribution and aggregation only. Source disciplines, gods, elements and original canonical roles are not reassigned to configurations.",
            "Holdout varies deterministic workload seeds/regimes, not independent real-world data. Performance changes require separate actual paired measurements.",
            "Audit replay evaluates two extra timelines per epoch to attribute metrics to source nodes; these extra updates are separately counted.",
        ],
        "nonClaims": ["No resident or model turns", "No model calls", "No network requests", "No background agents",
                      "No source/canon changes", "No private node bodies published", "No global optimum proven",
                      "No measured speedup inferred from synthetic service costs", "No civilization forecasting"],
    }
    validate_report(report, snapshot=snapshot)
    return report


def run_long_horizon(snapshot, trace_path, *, epochs=MAX_EPOCHS, years=MAX_YEARS, seed=DEFAULT_SEED,
                     threads=4, expected_trace_file_sha256=DEFAULT_TRACE_FILE_SHA256, timeout_seconds=3600):
    _assert_module_identity()
    references_before = digest(source_references(snapshot))
    calibration, source = load_calibration(snapshot, trace_path, expected_trace_file_sha256=expected_trace_file_sha256)
    with tempfile.TemporaryDirectory(prefix="atlas-long-horizon-") as tmp:
        binary = Path(tmp) / "engine"
        provenance = compile_engine(binary)
        raw = execute_engine(binary, calibration, epochs=epochs, years=years, seed=seed, threads=threads,
                             audit=True, timeout_seconds=timeout_seconds,
                             expected_binary_sha256=provenance["engineBinarySha256"])
    if hashlib.sha256(Path(trace_path).read_bytes()).hexdigest() != source["traceFileSha256"] or digest(source_references(snapshot)) != references_before:
        raise ValueError("LONG_HORIZON_INPUT_CHANGED_DURING_RUN")
    return _build_report(snapshot, source, raw, provenance, epochs=epochs, years=years, seed=seed, threads=threads)


def _validate_metrics(row):
    if type(row) is not dict or set(row) != set(METRICS):
        raise ValueError("LONG_HORIZON_METRICS_INVALID")
    for value in row.values():
        _integer(value)
    if row["requests"] != row["freshCompletions"] + row["heldRequests"]:
        raise ValueError("LONG_HORIZON_COMPLETION_PARITY")
    if row["freshCompletions"] != row["cacheHits"] + row["cacheMisses"]:
        raise ValueError("LONG_HORIZON_CACHE_PARITY")
    if row["predictedRequiredNs"] != row["predictedServiceNs"] + row["predictedHeldServiceNs"]:
        raise ValueError("LONG_HORIZON_SERVICE_PARITY")
    if row["freshnessViolations"] != 0:
        raise ValueError("LONG_HORIZON_FRESHNESS_FAILURE")


def validate_report(report, *, snapshot=None):
    """Validate the complete result, counters, hierarchy and selected audit sums.

    The exact original reference-table digest is pinned independently of the
    supplied report. A snapshot adds a second per-node comparison. Free-form
    fields cannot add hidden source bodies to the declared structural records.
    """
    if type(report) is not dict or report.get("schema") != SCHEMA or report.get("engineVersion") != ENGINE_VERSION:
        raise ValueError("LONG_HORIZON_REPORT_SCHEMA")
    _exact(report, ("schema", "engineVersion", "status", "evidenceKind", "source", "counts", "execution",
                    "candidates", "nodes", "spheres", "houses", "meta145", "epochSynthesis", "regimes",
                    "assumptions", "units", "limits", "qualityChecks", "limitations", "nonClaims"))
    _integer(report["engineVersion"], ENGINE_VERSION, ENGINE_VERSION)
    _safe_json(report)
    if len(canonical_json(report).encode()) > MAX_REPORT_BYTES:
        raise ValueError("LONG_HORIZON_REPORT_BYTES")
    if report.get("status") != "COMPLETED" or report.get("evidenceKind") != "SYNTHETIC_EVOLUTION_EXPERIMENT":
        raise ValueError("LONG_HORIZON_EVIDENCE_KIND")
    source = report["source"]
    _exact(source, ("registrySha256", "edition", "nodeReferencesSha256", "sourceFixtureKind", "traceFileSha256", "tracePayloadSha256"))
    if source.get("registrySha256") != REGISTRY_SHA or source.get("edition") != "ariadne-v0.7" or source.get("sourceFixtureKind") != "PINNED_ORIGINAL_ARIADNE":
        raise ValueError("LONG_HORIZON_SOURCE_IDENTITY")
    for key in ("registrySha256", "nodeReferencesSha256", "traceFileSha256", "tracePayloadSha256"):
        _sha(source[key])
    if source["nodeReferencesSha256"] != ORIGINAL_REFERENCES_SHA256:
        raise ValueError("LONG_HORIZON_ORIGINAL_REFERENCE_PIN_MISMATCH")
    c = report["counts"]
    _exact(c, ("epochs", "timelines", "yearsPerTimeline", "representedTimelineYears", "evaluatedTimelineYearUpdates",
               "nodes", "spheres", "houses", "trainEpochs", "holdoutEpochs", "acceptedCandidateChanges"))
    for value in c.values():
        _integer(value)
    _integer(c["epochs"], 1, MAX_EPOCHS)
    _integer(c["yearsPerTimeline"], 1, MAX_YEARS)
    if (c["timelines"], c["nodes"], c["spheres"], c["houses"]) != (1728, 1728, 144, 12):
        raise ValueError("LONG_HORIZON_COUNTS")
    expected = c["epochs"] * c["timelines"] * c["yearsPerTimeline"]
    if c["representedTimelineYears"] != expected or c["evaluatedTimelineYearUpdates"] != expected:
        raise ValueError("LONG_HORIZON_EVALUATED_UPDATES")
    execution = report["execution"]
    _exact(execution, ("method", "seed", "threads", "elapsedNs", "coreElapsedNs", "auditReplayUpdates", "stateReset",
                       "transitionChecksumAlgorithm", "pythonSourceSha256", "compiler", "compilerFlags", "engineSourceSha256", "engineBinarySha256"))
    if execution["method"] != "DIRECT_STATE_TRANSITIONS" or execution["auditReplayUpdates"] != 2 * c["epochs"] * c["yearsPerTimeline"]:
        raise ValueError("LONG_HORIZON_EXECUTION_COUNT")
    for key in ("engineSourceSha256", "pythonSourceSha256", "engineBinarySha256"):
        _sha(execution[key])
    for key in ("seed", "elapsedNs", "coreElapsedNs", "auditReplayUpdates"):
        _integer(execution[key])
    _integer(execution["threads"], 1, 4)
    if execution["elapsedNs"] < execution["coreElapsedNs"] or execution["stateReset"] != "EACH_EPOCH":
        raise ValueError("LONG_HORIZON_EXECUTION_PROVENANCE")
    candidates = report["candidates"]
    if type(candidates) is not list or len(candidates) != 1728:
        raise ValueError("LONG_HORIZON_CANDIDATES")
    epoch_rows = report["epochSynthesis"]
    if len(epoch_rows) != c["epochs"]:
        raise ValueError("LONG_HORIZON_EPOCH_COUNT")
    train_epochs, changes, incumbent = 0, 0, None
    ids = {candidate_id(i) for i in range(1728)}
    for i, row in enumerate(epoch_rows):
        _exact(row, ("epoch", "split", "regime", "epochWinnerCandidateId", "incumbentCandidateId", "acceptedChange"))
        holdout = (i // 12) % 4 == 3
        if row["epoch"] != i or row["split"] != ("holdout" if holdout else "train") or row["regime"] != f"R{i % 12 + 1:02d}":
            raise ValueError("LONG_HORIZON_EPOCH_IDENTITY")
        if row["incumbentCandidateId"] not in ids or type(row["acceptedChange"]) is not bool:
            raise ValueError("LONG_HORIZON_INCUMBENT")
        if holdout:
            if row["acceptedChange"] or row["epochWinnerCandidateId"] is not None or row["incumbentCandidateId"] != incumbent:
                raise ValueError("LONG_HORIZON_HOLDOUT_SELECTION_LEAK")
        else:
            train_epochs += 1
            if row["epochWinnerCandidateId"] not in ids or row["acceptedChange"] != (row["incumbentCandidateId"] != incumbent):
                raise ValueError("LONG_HORIZON_ACCEPTED_CHANGE")
            changes += row["acceptedChange"]
            incumbent = row["incumbentCandidateId"]
    if (c["trainEpochs"], c["holdoutEpochs"], c["acceptedCandidateChanges"]) != (train_epochs, c["epochs"] - train_epochs, changes):
        raise ValueError("LONG_HORIZON_EPOCH_TOTALS")
    for i, row in enumerate(candidates):
        _exact(row, ("id", "controls", "train", "holdout", "coverage", "transitionChecksum"))
        _exact(row["controls"], ("workers", "maxMemoEntries", "chunkSize"))
        _exact(row["coverage"], ("trainDistinctSourceNodes", "holdoutDistinctSourceNodes"))
        for value in row["controls"].values():
            _integer(value, 1)
        if row["id"] != candidate_id(i) or row["controls"] != controls(i):
            raise ValueError("LONG_HORIZON_CANDIDATE_IDENTITY")
        for split, count in (("train", train_epochs), ("holdout", c["epochs"] - train_epochs)):
            _validate_metrics(row[split])
            if row[split]["requests"] != count * c["yearsPerTimeline"]:
                raise ValueError("LONG_HORIZON_REQUEST_COUNT")
            _integer(row["coverage"][split + "DistinctSourceNodes"], 0, 1728)
        if not re.fullmatch(r"[a-f0-9]{16}", row["transitionChecksum"]):
            raise ValueError("LONG_HORIZON_TRANSITION_CHECKSUM")
    meta = report["meta145"]
    _exact(meta, ("selectionStatus", "selectedCandidateId", "baselineCandidateId", "trainingObjective", "holdout", "upgradeHypotheses"))
    _exact(meta["trainingObjective"], ("qualityOrder", "tieBreak"))
    if meta["selectionStatus"] != "SELECTED" or meta["baselineCandidateId"] != candidate_id(BASELINE_INDEX) or meta["selectedCandidateId"] != min(candidates, key=_score)["id"] or incumbent != meta["selectedCandidateId"]:
        raise ValueError("LONG_HORIZON_META_SELECTION")
    selected = next(row for row in candidates if row["id"] == meta["selectedCandidateId"])
    if meta["holdout"] != {"baseline": candidates[BASELINE_INDEX]["holdout"], "selected": selected["holdout"], "usedForSelection": False}:
        raise ValueError("LONG_HORIZON_HOLDOUT_RESULT")
    nodes, spheres, houses = report["nodes"], report["spheres"], report["houses"]
    if (len(nodes), len(spheres), len(houses)) != (1728, 144, 12):
        raise ValueError("LONG_HORIZON_AGGREGATION_COUNTS")
    refs = []
    for i, row in enumerate(nodes):
        _exact(row, ("id", "parent", "kind", "recordSha256", "metrics"))
        _exact(row["metrics"], ("baseline", "selected"))
        nid = f"H{i // 144 + 1:02d}.S{i // 12 % 12 + 1:02d}.N{i % 12 + 1:02d}"
        kind = "DOMAIN_SPECIALIZATION" if i // 12 % 12 < 7 else "EPISTEMIC_META"
        if row["id"] != nid or row["parent"] != nid[:7] or row["kind"] != kind:
            raise ValueError("LONG_HORIZON_NODE_IDENTITY")
        _sha(row["recordSha256"])
        refs.append({k: row[k] for k in ("id", "parent", "recordSha256", "kind")})
        for lane in ("baseline", "selected"):
            _validate_metrics(row["metrics"][lane])
    if digest(refs) != source["nodeReferencesSha256"] or snapshot is not None and refs != source_references(snapshot):
        raise ValueError("LONG_HORIZON_NODE_REFERENCE_DIGEST")
    for i, row in enumerate(spheres):
        _exact(row, ("id", "parent", "nodeIds", "metrics"))
        _exact(row["metrics"], ("baseline", "selected"))
        sid = f"H{i // 12 + 1:02d}.S{i % 12 + 1:02d}"
        children = nodes[i * 12:(i + 1) * 12]
        if row["id"] != sid or row["parent"] != sid[:3] or row["nodeIds"] != [n["id"] for n in children]:
            raise ValueError("LONG_HORIZON_SPHERE_HIERARCHY")
        for lane in ("baseline", "selected"):
            _validate_metrics(row["metrics"][lane])
            if row["metrics"][lane] != sum_metrics(n["metrics"][lane] for n in children):
                raise ValueError("LONG_HORIZON_SPHERE_SUM")
    for i, row in enumerate(houses):
        _exact(row, ("id", "sphereIds", "metrics"))
        _exact(row["metrics"], ("baseline", "selected"))
        children = spheres[i * 12:(i + 1) * 12]
        if row["id"] != f"H{i + 1:02d}" or row["sphereIds"] != [s["id"] for s in children]:
            raise ValueError("LONG_HORIZON_HOUSE_HIERARCHY")
        for lane in ("baseline", "selected"):
            _validate_metrics(row["metrics"][lane])
            if row["metrics"][lane] != sum_metrics(s["metrics"][lane] for s in children):
                raise ValueError("LONG_HORIZON_HOUSE_SUM")
    for i, row in enumerate(report["regimes"]):
        _exact(row, ("id", "name", "simulationOnly", "description", "metrics"))
        _exact(row["metrics"], ("baseline", "selected"))
        if i >= 12 or row["id"] != f"R{i + 1:02d}" or row["name"] != REGIMES[i][0] or row["simulationOnly"] is not True:
            raise ValueError("LONG_HORIZON_REGIME_IDENTITY")
        for lane in ("baseline", "selected"):
            _validate_metrics(row["metrics"][lane])
    for lane, candidate in (("baseline", candidates[BASELINE_INDEX]), ("selected", selected)):
        if sum_metrics(h["metrics"][lane] for h in houses) != sum_metrics((candidate["train"], candidate["holdout"])):
            raise ValueError("LONG_HORIZON_META_SUM")
        if len(report["regimes"]) != 12 or sum_metrics(r["metrics"][lane] for r in report["regimes"]) != sum_metrics((candidate["train"], candidate["holdout"])):
            raise ValueError("LONG_HORIZON_REGIME_SUM")
    q = report["qualityChecks"]
    _exact(q, ("freshnessViolations", "representedEqualsEvaluated", "baselineAuditMatches", "selectedAuditMatches",
               "sourceReferencesComplete", "holdoutExcludedFromSelection", "allWorkerVariantsEquivalent", "allSourceNodesCovered"))
    _integer(q["freshnessViolations"], 0, 0)
    if q["freshnessViolations"] != 0 or any(q[k] is not True for k in ("representedEqualsEvaluated", "baselineAuditMatches", "selectedAuditMatches", "sourceReferencesComplete", "holdoutExcludedFromSelection", "allWorkerVariantsEquivalent")):
        raise ValueError("LONG_HORIZON_QUALITY_FAILURE")
    if not all(candidates[i][split] == candidates[i % 144][split] for i in range(1728) for split in ("train", "holdout")):
        raise ValueError("LONG_HORIZON_WORKER_EQUIVALENCE")
    if q["allSourceNodesCovered"] != all(n["metrics"]["selected"]["freshCompletions"] > 0 for n in nodes):
        raise ValueError("LONG_HORIZON_COVERAGE_CLAIM")
    for row in meta["upgradeHypotheses"]:
        _exact(row, ("id", "title", "status", "evidence", "recommendedAction", "validationRequired"))
        if type(row["evidence"]) is not dict or any(type(v) is not int for v in row["evidence"].values()):
            raise ValueError("LONG_HORIZON_UPGRADE_EVIDENCE")
        if row["status"] != "PROPOSED_FROM_SYNTHETIC_EVIDENCE" or not row["validationRequired"]:
            raise ValueError("LONG_HORIZON_UPGRADE_CLAIM")
        if type(row["validationRequired"]) is not list or any(type(v) is not str for v in row["validationRequired"]):
            raise ValueError("LONG_HORIZON_UPGRADE_VALIDATION")
    if report["units"] != {"time": "nanoseconds", "year": "synthetic workload step", "cost": "predicted calibrated service, not measured latency"}:
        raise ValueError("LONG_HORIZON_UNITS")
    if report["limits"] != {"maxEpochs": MAX_EPOCHS, "maxYearsPerTimeline": MAX_YEARS, "maxThreads": 4, "maxReportBytes": MAX_REPORT_BYTES}:
        raise ValueError("LONG_HORIZON_LIMITS")
    for field in ("assumptions", "limitations", "nonClaims"):
        if type(report[field]) is not list or not report[field] or any(type(v) is not str for v in report[field]):
            raise ValueError("LONG_HORIZON_EXPLANATION_FIELDS")
    return report


def report_summary(report):
    validate_report(report)
    ids = {report["meta145"]["selectedCandidateId"], report["meta145"]["baselineCandidateId"]}
    return {k: report[k] for k in ("schema", "engineVersion", "status", "evidenceKind", "source", "counts", "execution", "meta145", "units", "qualityChecks", "limitations", "nonClaims")} | {
        "candidates": [row for row in report["candidates"] if row["id"] in ids],
        "fullReportSha256": digest(report), "projection": "SUMMARY_NOT_COMPLETE_REPORT"}


compact_summary = report_summary


def export_bundle(report):
    validate_report(report)
    raw = canonical_json(report)
    return {"schema": BUNDLE_SCHEMA, "reportJson": raw, "reportSha256": hashlib.sha256(raw.encode("utf-8")).hexdigest()}


def load_bundle(bundle):
    if type(bundle) is not dict or set(bundle) != {"schema", "reportJson", "reportSha256"} or bundle["schema"] != BUNDLE_SCHEMA:
        raise ValueError("LONG_HORIZON_BUNDLE_SCHEMA")
    raw = bundle["reportJson"]
    if type(raw) is not str or len(raw.encode()) > MAX_REPORT_BYTES:
        raise ValueError("LONG_HORIZON_BUNDLE_BYTES")
    if hashlib.sha256(raw.encode("utf-8")).hexdigest() != _sha(bundle["reportSha256"]):
        raise ValueError("LONG_HORIZON_BUNDLE_DIGEST")
    return validate_report(json.loads(raw))
