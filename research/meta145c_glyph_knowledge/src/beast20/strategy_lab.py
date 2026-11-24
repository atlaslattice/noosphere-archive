"""Finite 12 x 12 x 12 configuration search with explicit simulation provenance.

This is a service-time/discrete-event model, not 1,728 agent turns or measured
performance. It never edits the ontology, executes source text, or calls a
provider. Every axis corresponds to a present BEAST20 control. The configuration
slots borrow the H/S/N addressing shape solely for grouping candidates.
"""
from __future__ import annotations

from collections import OrderedDict, deque
from dataclasses import dataclass
from graphlib import TopologicalSorter, CycleError
import hashlib
import heapq
import math
from pathlib import Path
import re
from typing import Any

from .storage import canonical_bytes


WORKERS = tuple(range(1, 13))
CACHE_ENTRIES = (1, 2, 4, 8, 16, 32, 64, 128, 256, 512, 1024, 2048)
BATCH_SIZES = (1, 2, 4, 8, 16, 32, 64, 96, 128, 192, 256, 400)
_SHA = re.compile(r"[a-f0-9]{64}\Z")
_NAME = re.compile(r"[A-Za-z0-9_.:-]{1,160}\Z")
_HOUSE = re.compile(r"H(?:0[1-9]|1[0-2])\Z")
_ENGINE_SCHEMA = "atlas.beast20.strategy1728/v1"


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def _integer(value, low, high, error):
    if type(value) is not int or not low <= value <= high:
        raise ValueError(error)
    return value


def _hash(value, error):
    if type(value) is not str or not _SHA.fullmatch(value):
        raise ValueError(error)
    return value


def _name(value, error):
    if type(value) is not str or not _NAME.fullmatch(value):
        raise ValueError(error)
    return value


@dataclass(frozen=True)
class StrategyConfig:
    workers: int = 4
    max_memo_entries: int = 256
    chunk_size: int = 400

    def __post_init__(self):
        _integer(self.workers, 1, 256, "WORKER_BOUND_INVALID")
        _integer(self.max_memo_entries, 1, 1_000_000, "MEMO_BOUND_INVALID")
        _integer(self.chunk_size, 1, 400, "BATCH_BOUND_INVALID")

    def as_dict(self):
        self.__post_init__()
        return {"workers": self.workers, "max_memo_entries": self.max_memo_entries,
                "chunk_size": self.chunk_size}


def configurations():
    """Exactly 1,728 unique, directly applicable configurations, in stable order."""
    return tuple((f"H{h:02d}.S{s:02d}.N{n:02d}", StrategyConfig(w, c, b))
                 for h, w in enumerate(WORKERS, 1)
                 for s, c in enumerate(CACHE_ENTRIES, 1)
                 for n, b in enumerate(BATCH_SIZES, 1))


def trace_envelope(payload: dict) -> dict:
    """Hash the exact trace data. This checksum is not measurement attestation."""
    canonical_bytes(payload)
    return {"payload": payload, "sha256": digest(payload)}


def _validated_trace(envelope, expected_sha, source_digest, edition):
    _hash(expected_sha, "EXPECTED_TRACE_DIGEST_REQUIRED")
    if type(envelope) is not dict or set(envelope) != {"payload", "sha256"}:
        raise ValueError("TRACE_ENVELOPE_INVALID")
    body = envelope["payload"]
    if digest(body) != expected_sha or envelope["sha256"] != expected_sha:
        raise ValueError("TRACE_DIGEST_MISMATCH")
    if type(body) is not dict or body.get("schema") != "atlas.beast20.strategy-trace/v1":
        raise ValueError("TRACE_SCHEMA_INVALID")
    if body.get("source_digest") != source_digest or body.get("edition") != edition:
        raise ValueError("TRACE_SOURCE_IDENTITY_MISMATCH")
    if body.get("measurement_kind") not in {"MEASURED_HANDLER_SERVICE_TIMES", "SYNTHETIC_ASSUMED"}:
        raise ValueError("TRACE_MEASUREMENT_KIND_INVALID")
    calibration = body.get("calibration")
    required = {"memo_lookup_ns", "memo_store_ns", "batch_fixed_ns", "batch_item_ns"}
    if type(calibration) is not dict or set(calibration) != required:
        raise ValueError("CALIBRATION_FIELDS_INVALID")
    for value in calibration.values():
        _integer(value, 0, 10**12, "CALIBRATION_NANOSECONDS_INVALID")
    scenarios = body.get("scenarios")
    if type(scenarios) is not list or not 2 <= len(scenarios) <= 24:
        raise ValueError("SCENARIO_COUNT_INVALID")
    names, partitions, outputs, total = set(), set(), {}, 0
    prepared = []
    for scenario in scenarios:
        if type(scenario) is not dict:
            raise ValueError("SCENARIO_INVALID")
        name = _name(scenario.get("name"), "SCENARIO_NAME_INVALID")
        if name in names:
            raise ValueError("DUPLICATE_SCENARIO")
        names.add(name)
        split = scenario.get("split")
        if split not in {"train", "holdout"}:
            raise ValueError("SCENARIO_SPLIT_INVALID")
        partitions.add(split)
        object_count = _integer(scenario.get("unique_object_count"), 0, 100_000,
                                "OBJECT_COUNT_INVALID")
        tasks = scenario.get("tasks")
        if type(tasks) is not list or not 1 <= len(tasks) <= 4096:
            raise ValueError("TRACE_TASK_COUNT_INVALID")
        total += len(tasks)
        if total > 32_768:
            raise ValueError("TRACE_EVENT_BUDGET_EXCEEDED")
        ids = {}
        for row in tasks:
            if type(row) is not dict:
                raise ValueError("TRACE_TASK_INVALID")
            tid = _name(row.get("task_id"), "TRACE_TASK_ID_INVALID")
            if tid in ids:
                raise ValueError("DUPLICATE_TRACE_TASK")
            if type(row.get("house")) is not str or not _HOUSE.fullmatch(row["house"]):
                raise ValueError("TRACE_HOUSE_INVALID")
            key = _hash(row.get("cache_key"), "TRACE_KEY_INVALID")
            output = _hash(row.get("output_digest"), "TRACE_OUTPUT_DIGEST_INVALID")
            if key in outputs and outputs[key] != output:
                raise ValueError("CACHE_KEY_OUTPUT_CONFLICT")
            outputs[key] = output
            for field in ("cpu_ns", "async_wait_ns"):
                _integer(row.get(field), 0, 10**12, "TASK_NANOSECONDS_INVALID")
            if row["cpu_ns"] + row["async_wait_ns"] == 0:
                raise ValueError("ZERO_SERVICE_TIME_INVALID")
            _integer(row.get("result_bytes"), 1, 8 * 1024 * 1024, "RESULT_BYTE_SIZE_INVALID")
            parents = row.get("dependencies")
            if type(parents) is not list or any(type(p) is not str for p in parents):
                raise ValueError("TRACE_DEPENDENCIES_INVALID")
            if len(parents) != len(set(parents)):
                raise ValueError("DUPLICATE_TRACE_DEPENDENCY")
            ids[tid] = len(ids)
        if any(p not in ids for row in tasks for p in row["dependencies"]):
            raise ValueError("UNKNOWN_TRACE_DEPENDENCY")
        try:
            tuple(TopologicalSorter({r["task_id"]: r["dependencies"] for r in tasks}).static_order())
        except CycleError as exc:
            raise ValueError("CYCLIC_TRACE") from exc
        children = [[] for _ in tasks]
        counts = []
        for i, row in enumerate(tasks):
            counts.append(len(row["dependencies"]))
            for parent in row["dependencies"]:
                children[ids[parent]].append(i)
        prepared.append({"name": name, "split": split, "objects": object_count,
                         "tasks": tasks, "children": children, "counts": counts})
    if partitions != {"train", "holdout"}:
        raise ValueError("TRAIN_AND_HOLDOUT_REQUIRED")
    return body, prepared


def _replay_scheduler(scenarios, capacity, workers, calibration):
    """Serial CPU lane, overlapping explicit async waits, fair ready Houses.

    Cache state persists inside a split and resets between train and holdout.
    TTL is assumed not to expire during a split; no provider/retry forecast is
    inferred. Identical in-flight keys share work, as BEAST20 singleflight does.
    """
    cache = OrderedDict()
    size = peak_bytes = peak_entries = wall = cpu = hits = misses = coalesced = 0
    object_counts, scenario_rows = [], []
    for scenario in scenarios:
        tasks, children = scenario["tasks"], scenario["children"]
        pending = scenario["counts"][:]
        ready = [deque() for _ in range(12)]
        for i, count in enumerate(pending):
            if not count:
                ready[int(tasks[i]["house"][1:]) - 1].append(i)
        cursor, clock, active, completed, serial, scenario_cpu = 0, 0, 0, 0, 0, 0
        events, flights = [], {}

        def complete(i):
            nonlocal completed
            completed += 1
            for child in children[i]:
                pending[child] -= 1
                if not pending[child]:
                    ready[int(tasks[child]["house"][1:]) - 1].append(child)

        def finish(key, indexes):
            nonlocal size, peak_bytes, peak_entries, clock, scenario_cpu
            row = tasks[indexes[0]]
            cost = calibration["memo_store_ns"]
            clock += cost
            scenario_cpu += cost
            if key in cache:
                size -= cache.pop(key)
            cache[key] = row["result_bytes"]
            size += row["result_bytes"]
            while len(cache) > capacity:
                _, removed = cache.popitem(last=False)
                size -= removed
            peak_bytes, peak_entries = max(peak_bytes, size), max(peak_entries, len(cache))
            for index in indexes:
                complete(index)

        while completed < len(tasks):
            while events and events[0][0] <= clock:
                _, _, key = heapq.heappop(events)
                active -= 1
                finish(key, flights.pop(key))
            if completed == len(tasks):
                break
            found = None
            if active < workers:
                for distance in range(12):
                    h = (cursor + distance) % 12
                    if ready[h]:
                        found = ready[h].popleft()
                        cursor = (h + 1) % 12
                        break
            if found is None:
                if not events:
                    raise ValueError("TRACE_SCHEDULER_STALLED")
                clock = max(clock, events[0][0])
                continue
            row = tasks[found]
            key = row["cache_key"]
            clock += calibration["memo_lookup_ns"]
            scenario_cpu += calibration["memo_lookup_ns"]
            if key in cache:
                cache.move_to_end(key)
                hits += 1
                complete(found)
                continue
            if key in flights:
                flights[key].append(found)
                coalesced += 1
                continue
            misses += 1
            clock += row["cpu_ns"]
            scenario_cpu += row["cpu_ns"]
            if not row["async_wait_ns"]:
                finish(key, [found])
            else:
                active += 1
                serial += 1
                flights[key] = [found]
                heapq.heappush(events, (clock + row["async_wait_ns"], serial, key))
        wall += clock
        cpu += scenario_cpu
        object_counts.append(scenario["objects"])
        scenario_rows.append({"name": scenario["name"], "scheduler_wall_ns": clock,
                              "cpu_service_ns": scenario_cpu, "completed_tasks": completed})
    return {"scheduler_wall_ns": wall, "cpu_service_ns": cpu, "cache_hits": hits,
            "cache_misses": misses, "singleflight_coalesced": coalesced,
            "peak_memo_bytes": peak_bytes, "peak_memo_entries": peak_entries,
            "object_counts": object_counts, "scenarios": scenario_rows}


def _with_batch(core, config, calibration):
    batches = sum(math.ceil(n / config.chunk_size) for n in core["object_counts"])
    batch_ns = batches * calibration["batch_fixed_ns"] + sum(core["object_counts"]) * calibration["batch_item_ns"]
    return {"predicted_wall_ns": core["scheduler_wall_ns"] + batch_ns,
            "predicted_cpu_service_ns": core["cpu_service_ns"] + batch_ns,
            "predicted_peak_memo_bytes": core["peak_memo_bytes"],
            "peak_memo_entries": core["peak_memo_entries"],
            "cache_hits": core["cache_hits"], "cache_misses": core["cache_misses"],
            "singleflight_coalesced": core["singleflight_coalesced"],
            "predicted_batch_queries": batches}


def _pareto(rows):
    """Exact nondominance over training wall time, reserved entries and workers."""
    frontier = []
    for row in sorted(rows, key=lambda r: (r["train"]["predicted_wall_ns"],
                                          r["config"]["max_memo_entries"], r["config"]["workers"], r["id"])):
        point = (row["train"]["predicted_wall_ns"], row["config"]["max_memo_entries"], row["config"]["workers"])
        # Identical objective points retain their first deterministic representative.
        if any(all(a <= b for a, b in zip(p, point)) for _, p in frontier):
            continue
        frontier = [(name, p) for name, p in frontier if not all(a <= b for a, b in zip(point, p))]
        frontier.append((row["id"], point))
    return sorted(name for name, _ in frontier)


class StrategyLab:
    """Finite configuration search; selected-on-training, evaluated-on-holdout."""
    def __init__(self, source_digest, edition, *, max_evaluations=1728):
        self.source_digest = _hash(source_digest, "SOURCE_DIGEST_INVALID")
        self.edition = _name(edition, "EDITION_INVALID")
        self.max_evaluations = _integer(max_evaluations, 1728, 1728, "EXACT_EVALUATION_BUDGET_REQUIRED")

    def evaluate(self, trace, *, expected_trace_sha256, weights=None, constraints=None,
                 baseline=None):
        body, scenarios = _validated_trace(trace, expected_trace_sha256, self.source_digest, self.edition)
        baseline = baseline or StrategyConfig()
        if type(baseline) is not StrategyConfig:
            raise ValueError("BASELINE_CONFIG_REQUIRED")
        baseline.__post_init__()
        weights = dict(weights) if type(weights) is dict else weights
        if weights is None:
            weights = {"latency": 1.0, "cpu": 0.1, "cache_reservation": 0.02, "workers": 0.01}
        if type(weights) is not dict or set(weights) != {"latency", "cpu", "cache_reservation", "workers"}:
            raise ValueError("OBJECTIVE_FIELDS_INVALID")
        if any(type(v) not in (int, float) or not math.isfinite(v) or not 0 <= v <= 1e6 for v in weights.values()) or not sum(weights.values()):
            raise ValueError("OBJECTIVE_WEIGHTS_INVALID")
        limits = {"max_workers": 12, "max_memo_entries": 2048, "max_chunk_size": 400,
                  "max_predicted_memo_bytes": 1 << 30}
        if constraints is not None:
            if type(constraints) is not dict or any(k not in limits for k in constraints):
                raise ValueError("CONSTRAINT_FIELDS_INVALID")
            limits.update(constraints)
        for name, ceiling in (("max_workers", 256), ("max_memo_entries", 1_000_000),
                              ("max_chunk_size", 400), ("max_predicted_memo_bytes", 1 << 40)):
            _integer(limits[name], 1, ceiling, "CONSTRAINT_BOUND_INVALID")
        partitions = {split: [s for s in scenarios if s["split"] == split] for split in ("train", "holdout")}
        calibration, memo = body["calibration"], {}
        async_present = any(t["async_wait_ns"] for s in scenarios for t in s["tasks"])

        def metrics(config, split):
            effective_workers = config.workers if async_present else 1
            key = (split, effective_workers, config.max_memo_entries)
            if key not in memo:
                memo[key] = _replay_scheduler(partitions[split], config.max_memo_entries, effective_workers, calibration)
            return _with_batch(memo[key], config, calibration)

        base = {split: metrics(baseline, split) for split in partitions}

        def score(config, row):
            b = base["train"]
            return (weights["latency"] * row["predicted_wall_ns"] / max(1, b["predicted_wall_ns"])
                    + weights["cpu"] * row["predicted_cpu_service_ns"] / max(1, b["predicted_cpu_service_ns"])
                    + weights["cache_reservation"] * config.max_memo_entries / baseline.max_memo_entries
                    + weights["workers"] * config.workers / baseline.workers)

        candidates = []
        for slot, config in configurations():
            train, holdout = metrics(config, "train"), metrics(config, "holdout")
            feasible = (config.workers <= limits["max_workers"] and
                        config.max_memo_entries <= limits["max_memo_entries"] and
                        config.chunk_size <= limits["max_chunk_size"] and
                        train["predicted_peak_memo_bytes"] <= limits["max_predicted_memo_bytes"])
            candidates.append({"id": "STRATEGY-" + slot, "slot": slot, "config": config.as_dict(),
                               "eligible": feasible, "training_objective": score(config, train),
                               "train": train, "holdout": holdout})
        # Holdout never enters selection, candidate pruning, or the Pareto frontier.
        rank = lambda row: (row["training_objective"], row["config"]["workers"],
                            row["config"]["max_memo_entries"], row["config"]["chunk_size"], row["id"])
        eligible = [row for row in candidates if row["eligible"]]
        selected = min(eligible, key=rank) if eligible else None
        sphere_rows, house_rows = [], []
        for h in range(1, 13):
            house = f"H{h:02d}"
            for s in range(1, 13):
                sphere = f"{house}.S{s:02d}"
                group = [r for r in candidates if r["slot"].startswith(sphere + ".")]
                accepted = [r for r in group if r["eligible"]]
                winner = min(accepted, key=rank) if accepted else None
                sphere_rows.append({"sphere": sphere, "candidate_count": 12, "eligible_count": len(accepted),
                                    "selected_id": winner["id"] if winner else None,
                                    "training_objective": winner["training_objective"] if winner else None})
            group = [r for r in eligible if r["slot"].startswith(house + ".")]
            winner = min(group, key=rank) if group else None
            house_rows.append({"house": house, "sphere_count": 12, "candidate_count": 144,
                               "selected_id": winner["id"] if winner else None,
                               "config": winner["config"] if winner else None})
        holdout_ratio = (base["holdout"]["predicted_wall_ns"] / max(1, selected["holdout"]["predicted_wall_ns"])) if selected else None
        holdout_resources = (selected["holdout"]["predicted_peak_memo_bytes"] <= limits["max_predicted_memo_bytes"]) if selected else None
        report = {"schema": _ENGINE_SCHEMA, "status": "SIMULATED", "source_digest": self.source_digest,
                  "edition": self.edition, "trace_sha256": expected_trace_sha256,
                  "trace_measurement_kind": body["measurement_kind"],
                  "measurement_attestation": "CALLER_SUPPLIED_TRACE_WITH_CHECKSUM",
                  "simulation_engine_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                  "coordinate_role": "CONFIGURATION_GROUPING_NOT_ONTOLOGY_OR_DEITY_MAPPING",
                  "axes": {"workers": list(WORKERS), "max_memo_entries": list(CACHE_ENTRIES),
                           "chunk_size": list(BATCH_SIZES)},
                  "runtime_controls": {"workers": "AsyncExecutor(workers=)",
                                       "max_memo_entries": "ArtifactStore(max_memo_entries=)",
                                       "chunk_size": "ArtifactStore.batch_get(chunk_size=)"},
                  "units": {"time": "nanoseconds", "memory": "bytes", "objective": "dimensionless"},
                  "candidate_count": len(candidates), "eligible_count": len(eligible),
                  "unique_scheduler_replays": len(memo), "weights": weights, "constraints": limits,
                  "baseline": {"config": baseline.as_dict(), **base},
                  "selection_policy": "MINIMIZE_TRAINING_OBJECTIVE_WITH_DETERMINISTIC_TIES",
                  "holdout_used_for_selection": False,
                  "spheres": sphere_rows, "houses": house_rows,
                  "meta145": {"status": ("SELECTED_FOR_MEASURED_REPLAY" if holdout_resources else "HOLDOUT_RESOURCE_LIMIT_EXCEEDED") if selected else "NO_FEASIBLE_STRATEGY",
                              "selected": selected, "predicted_holdout_ratio_baseline_over_candidate": holdout_ratio,
                              "holdout_regression": holdout_ratio is not None and holdout_ratio < 1,
                              "holdout_resource_constraints_satisfied": holdout_resources},
                  "pareto_candidate_ids": _pareto(eligible), "candidates": candidates,
                  "assumptions": ["Memo entries do not expire during each split; splits start with an empty memo.",
                                  "CPU handler service is serialized; only explicit async wait can overlap.",
                                  "Batch cost is a calibrated linear estimate; runtime scheduler/SQLite overhead is not fully modeled.",
                                  "All equal cache keys have equal output digests in the supplied trace.",
                                  "Trace checksum detects alteration relative to supplied expected bytes; it does not authenticate measurement."],
                  "non_claims": {"measured_speedup": False, "hosted_verified": False, "model_calls": 0,
                                 "resident_turns": 0, "canon_changed": False, "global_optimum_proven": False}}
        report["report_sha256"] = digest(report)
        return report


def compact_summary(report):
    """Native host view: retain decisions and provenance, omit 1,728 metric rows."""
    if type(report) is not dict or report.get("schema") != _ENGINE_SCHEMA:
        raise ValueError("STRATEGY_REPORT_INVALID")
    raw = {key: value for key, value in report.items() if key != "report_sha256"}
    if digest(raw) != report.get("report_sha256"):
        raise ValueError("STRATEGY_REPORT_DIGEST_MISMATCH")
    summary = {key: value for key, value in report.items() if key != "candidates"}
    summary["candidate_rows_omitted"] = report["candidate_count"]
    summary["full_report_sha256"] = report["report_sha256"]
    summary.pop("report_sha256")
    summary["summary_sha256"] = digest(summary)
    return summary
