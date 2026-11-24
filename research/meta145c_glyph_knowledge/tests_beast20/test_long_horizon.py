"""Exact transition and evidence contracts; no private source fixture required."""
from copy import deepcopy
import gzip
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from src.core import SourceSnapshot
from src.glyph import REGISTRY_SHA
from src.beast20.long_horizon import (BASELINE_INDEX, BUNDLE_SCHEMA, MAX_SAFE_INTEGER, METRICS, NODES,
    ORIGINAL_REFERENCES_SHA256, _assert_module_identity, _build_report, _mix64, _score, _validate_calibration, candidate_id, compile_engine, controls,
    digest, empty_metrics, engine_input, execute_engine, export_bundle, load_bundle, metric_record,
    reference_epoch, report_summary, source_references, sum_metrics, validate_report, workload_events)


def calibration():
    return {"lookup": 41, "store": 29, "fixed": 7, "item": 3,
            "cpu": [11 + i % 37 for i in range(NODES)]}


def fixture_snapshot():
    # Exact public reference metadata, no original source names or bodies. The
    # independent table pin is enforced even for this manually constructed test
    # object, so __new__ cannot substitute invented original record digests.
    raw = gzip.decompress((Path(__file__).parent / "fixtures/ARIADNE_V07_REFERENCES.json.gz").read_bytes())
    if hashlib.sha256(raw).hexdigest() != ORIGINAL_REFERENCES_SHA256:
        raise ValueError("TEST_REFERENCE_FIXTURE_DIGEST")
    refs = {row["id"]: row for row in json.loads(raw)}
    s = SourceSnapshot.__new__(SourceSnapshot)
    s.registry_sha = REGISTRY_SHA
    s.houses, s.spheres, s.nodes = {}, {}, {}
    for h in range(1, 13):
        hid = f"H{h:02d}"
        s.houses[hid] = {"id": hid, "children": []}
        for sphere in range(1, 13):
            sid = f"{hid}.S{sphere:02d}"
            s.spheres[sid] = {"id": sid, "parent": hid, "children": []}
            s.houses[hid]["children"].append(sid)
            for n in range(1, 13):
                nid = f"{sid}.N{n:02d}"
                s.nodes[nid] = {"id": nid, "parent": sid,
                                "kind": "DOMAIN_SPECIALIZATION" if sphere <= 7 else "EPISTEMIC_META",
                                "source_record_sha256": refs[nid]["recordSha256"]}
                s.spheres[sid]["children"].append(nid)
    s.node_ids = tuple(sorted(s.nodes))
    return s


class LongHorizonTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory(prefix="long-horizon-test-")
        cls.binary = Path(cls.tmp.name) / "engine"
        cls.provenance = compile_engine(cls.binary)
        cls.c = calibration()
        cls.snapshot = fixture_snapshot()
        cls.raw = execute_engine(cls.binary, cls.c, epochs=48, years=64, seed=7, threads=2)
        cls.report = _build_report(cls.snapshot, {"traceFileSha256": "a" * 64, "tracePayloadSha256": "b" * 64},
                                  cls.raw, cls.provenance, epochs=48, years=64, seed=7, threads=2)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_exact_configuration_cardinality_namespace_and_current_baseline(self):
        ids = [candidate_id(i) for i in range(NODES)]
        self.assertEqual(len(set(ids)), NODES)
        self.assertEqual(len({tuple(controls(i).values()) for i in range(NODES)}), NODES)
        self.assertTrue(all(x.startswith("CFG.") for x in ids))
        self.assertEqual(controls(BASELINE_INDEX), {"workers": 1, "maxMemoEntries": 2048, "chunkSize": 400})
        self.assertEqual(self.report["meta145"]["baselineCandidateId"], candidate_id(BASELINE_INDEX))

    def test_direct_native_loop_matches_independent_python_oracle_all_regimes_and_holdout(self):
        indices = [0, 11, 59, 143, 1727]
        raw = execute_engine(self.binary, self.c, epochs=49, years=91, seed=701, threads=2, indices=indices, audit=False)
        for row in raw["rows"]:
            totals = {"train": empty_metrics(), "holdout": empty_metrics()}
            coverage = {"train": set(), "holdout": set()}
            checksum = 0
            for epoch in range(49):
                lane = "holdout" if epoch // 12 % 4 == 3 else "train"
                result = reference_epoch(row["index"], workload_events(epoch, 91, 701, self.c), self.c)
                totals[lane] = sum_metrics((totals[lane], result["metrics"]))
                coverage[lane].update(result["coverage"])
                checksum = _mix64(checksum ^ int(result["checksum"], 16) ^ epoch)
            self.assertEqual(metric_record(row["train"]), totals["train"])
            self.assertEqual(metric_record(row["holdout"]), totals["holdout"])
            self.assertEqual(row["coverage"], [len(coverage["train"]), len(coverage["holdout"])])
            self.assertEqual(row["checksum"], f"{checksum:016x}")

    def test_thread_count_changes_neither_results_selection_nor_epoch_evolution(self):
        a = execute_engine(self.binary, self.c, epochs=49, years=73, seed=14, threads=1, indices=[0, 59, 143, 1727])
        b = execute_engine(self.binary, self.c, epochs=49, years=73, seed=14, threads=4, indices=[0, 59, 143, 1727])
        for row in (a, b):
            row.pop("elapsedNs")
            row.pop("coreElapsedNs")
        self.assertEqual(a, b)

    def test_count_receipts_are_sums_of_evaluated_requests_not_only_requested_products(self):
        observed = sum(sum(row[lane][0] for lane in ("train", "holdout")) for row in self.raw["rows"])
        self.assertEqual(observed, self.raw["evaluatedUpdates"])
        self.assertEqual(observed, 48 * 64 * 1728)
        self.assertEqual(self.raw["auditReplayUpdates"], 2 * 48 * 64)

    def test_original_source_references_are_complete_and_have_no_bodies(self):
        refs = source_references(self.snapshot)
        self.assertEqual(len(refs), 1728)
        self.assertEqual(len({r["recordSha256"] for r in refs}), 1728)
        self.assertTrue(all(set(r) == {"id", "parent", "recordSha256", "kind"} for r in refs))
        self.assertEqual(self.report["source"]["nodeReferencesSha256"], digest(refs))

    def test_wrong_source_identity_and_roles_are_rejected(self):
        for change in (lambda s: setattr(s, "registry_sha", "c" * 64),
                       lambda s: s.nodes["H01.S01.N01"].update(kind="EPHEMERAL")):
            s = deepcopy(self.snapshot)
            change(s)
            with self.assertRaises(ValueError):
                source_references(s)
        with self.assertRaises(ValueError):
            source_references(object())

    def test_bad_nonfinite_negative_and_noninteger_calibration(self):
        for value in (-1, True, float("nan"), float("inf"), 1.2, "3"):
            c = calibration()
            c["lookup"] = value
            with self.assertRaises(ValueError):
                engine_input(c)
        c = calibration()
        c["cpu"][0] = 0
        with self.assertRaises(ValueError):
            engine_input(c)

    def test_cost_arithmetic_is_bounded_before_native_execution(self):
        c = calibration()
        c["fixed"] = 10**9
        with self.assertRaisesRegex(ValueError, "SAFE_INTEGER_BUDGET"):
            _validate_calibration(c)

    def test_dimension_seed_thread_and_duplicate_bounds(self):
        for kwargs in ({"epochs": 1730}, {"years": 1729}, {"epochs": 0}, {"years": True},
                       {"threads": 5}, {"threads": 0}, {"seed": -1}, {"seed": MAX_SAFE_INTEGER + 1},
                       {"indices": [0, 0]}, {"indices": [1728]}, {"indices": []}, {"audit": 1}):
            with self.assertRaises(ValueError):
                engine_input(self.c, **kwargs)

    def test_scarce_budget_and_unavailable_sources_hold_work_without_success(self):
        scarce = reference_epoch(0, workload_events(8, 1728, 7, self.c), self.c)["metrics"]
        unavailable = reference_epoch(143, workload_events(10, 1728, 7, self.c), self.c)["metrics"]
        for m in (scarce, unavailable):
            self.assertGreater(m["heldRequests"], 0)
            self.assertEqual(m["requests"], m["freshCompletions"] + m["heldRequests"])
            self.assertEqual(m["freshnessViolations"], 0)

    def test_revision_invalidation_forces_miss_and_never_serves_prior_version(self):
        event = {"node": 0, "local": False, "global": False, "unavailable": False, "budget": 1000}
        events = [dict(event), dict(event), dict(event, local=True), dict(event)]
        metrics = reference_epoch(143, events, self.c)["metrics"]
        self.assertEqual((metrics["cacheHits"], metrics["cacheMisses"], metrics["sourceChanges"]), (2, 2, 1))
        self.assertEqual(metrics["freshnessViolations"], 0)

    def test_lru_capacity_and_batching_have_actual_transition_effects(self):
        work = workload_events(0, 1728, 7, self.c)
        small = reference_epoch(0, work, self.c)["metrics"]
        large = reference_epoch(143, work, self.c)["metrics"]
        self.assertGreater(large["cacheHits"], small["cacheHits"])
        self.assertLess(large["predictedServiceNs"], small["predictedServiceNs"])
        one_batch = reference_epoch(132, work[:1], self.c)["metrics"]
        wide_batch = reference_epoch(143, work[:1], self.c)["metrics"]
        self.assertEqual(one_batch["freshCompletions"], wide_batch["freshCompletions"])
        self.assertLess(wide_batch["predictedServiceNs"], one_batch["predictedServiceNs"])

    def test_freshness_and_coverage_precede_cost_in_selection(self):
        clean = deepcopy(self.report["candidates"][0])
        corrupt = deepcopy(clean)
        corrupt["train"]["freshnessViolations"] = 1
        corrupt["coverage"]["trainDistinctSourceNodes"] = 1728
        corrupt["train"]["predictedServiceNs"] = 0
        self.assertLess(_score(clean), _score(corrupt))
        less_complete = deepcopy(clean)
        less_complete["train"]["freshCompletions"] -= 1
        less_complete["train"]["heldRequests"] += 1
        less_complete["train"]["predictedServiceNs"] = 0
        self.assertLess(_score(clean), _score(less_complete))

    def test_holdout_epochs_do_not_select_or_change_the_incumbent(self):
        rows = self.report["epochSynthesis"]
        self.assertEqual(sum(r["split"] == "holdout" for r in rows), 12)
        for i, row in enumerate(rows):
            if row["split"] == "holdout":
                self.assertIsNone(row["epochWinnerCandidateId"])
                self.assertFalse(row["acceptedChange"])
                self.assertEqual(row["incumbentCandidateId"], rows[i - 1]["incumbentCandidateId"])

    def test_epoch_incumbent_records_real_training_changes(self):
        rows = self.report["epochSynthesis"]
        self.assertTrue(rows[0]["acceptedChange"])
        self.assertEqual(sum(r["acceptedChange"] for r in rows), self.report["counts"]["acceptedCandidateChanges"])
        self.assertEqual(rows[-1]["incumbentCandidateId"], self.report["meta145"]["selectedCandidateId"])

    def test_source_hierarchy_sums_equal_audit_and_selected_candidate(self):
        self.assertEqual((len(self.report["nodes"]), len(self.report["spheres"]), len(self.report["houses"])), (1728, 144, 12))
        self.assertIs(validate_report(self.report, snapshot=self.snapshot), self.report)
        for lane, index in (("baseline", BASELINE_INDEX), ("selected", self.raw["selectedIndex"])):
            total = sum_metrics(row["metrics"][lane] for row in self.report["nodes"])
            candidate = self.report["candidates"][index]
            self.assertEqual(total, sum_metrics((candidate["train"], candidate["holdout"])))

    def test_report_units_and_nonclaims_stay_explicit(self):
        self.assertEqual(self.report["evidenceKind"], "SYNTHETIC_EVOLUTION_EXPERIMENT")
        self.assertEqual(self.report["units"]["time"], "nanoseconds")
        self.assertIn("No resident or model turns", self.report["nonClaims"])
        self.assertTrue(all(r["status"] == "PROPOSED_FROM_SYNTHETIC_EVIDENCE" for r in self.report["meta145"]["upgradeHypotheses"]))
        self.assertNotIn("measuredSpeedup", json.dumps(self.report))

    def test_report_and_raw_bundle_digest_round_trip(self):
        bundle = export_bundle(self.report)
        self.assertEqual(bundle["schema"], BUNDLE_SCHEMA)
        self.assertEqual(hashlib.sha256(bundle["reportJson"].encode()).hexdigest(), bundle["reportSha256"])
        self.assertEqual(load_bundle(bundle), self.report)
        bundle["reportJson"] += " "
        with self.assertRaisesRegex(ValueError, "BUNDLE_DIGEST"):
            load_bundle(bundle)

    def test_summary_keeps_scope_and_separates_full_report_identity(self):
        summary = report_summary(self.report)
        self.assertEqual(summary["fullReportSha256"], digest(self.report))
        self.assertEqual(summary["projection"], "SUMMARY_NOT_COMPLETE_REPORT")
        self.assertEqual(summary["evidenceKind"], self.report["evidenceKind"])
        self.assertLessEqual(len(summary["candidates"]), 2)
        self.assertNotIn("nodes", summary)

    def test_counter_mutations_and_fabricated_completion_are_rejected(self):
        changes = [lambda r: r["counts"].update(evaluatedTimelineYearUpdates=1),
                   lambda r: r["execution"].update(auditReplayUpdates=0),
                   lambda r: r["candidates"][0]["train"].update(freshCompletions=0),
                   lambda r: r["candidates"][0]["train"].update(freshnessViolations=1),
                   lambda r: r["candidates"][0]["train"].update(predictedServiceNs=0)]
        for change in changes:
            r = deepcopy(self.report)
            change(r)
            with self.assertRaises(ValueError):
                validate_report(r)

    def test_namespace_digest_and_hierarchy_tampering_rejected(self):
        changes = [lambda r: r["source"].update(registrySha256="f" * 64),
                   lambda r: r["nodes"][0].update(recordSha256="f" * 64),
                   lambda r: r["nodes"][0].update(parent="H02.S01"),
                   lambda r: r["spheres"][0]["nodeIds"].reverse(),
                   lambda r: r["houses"][0]["sphereIds"].reverse(),
                   lambda r: r["spheres"][0]["metrics"]["selected"].update(requests=0)]
        for change in changes:
            r = deepcopy(self.report)
            change(r)
            with self.assertRaises(ValueError):
                validate_report(r)

    def test_independent_snapshot_check_rejects_rehashed_forged_record_reference(self):
        r = deepcopy(self.report)
        r["nodes"][0]["recordSha256"] = "f" * 64
        r["source"]["nodeReferencesSha256"] = digest([{k: row[k] for k in ("id", "parent", "recordSha256", "kind")} for row in r["nodes"]])
        with self.assertRaisesRegex(ValueError, "REFERENCE_PIN_MISMATCH"):
            validate_report(r, snapshot=self.snapshot)

    def test_rehashed_fake_record_is_rejected_without_private_snapshot(self):
        r = deepcopy(self.report)
        r["nodes"][0]["recordSha256"] = "f" * 64
        r["source"]["nodeReferencesSha256"] = digest([{k: row[k] for k in ("id", "parent", "recordSha256", "kind")} for row in r["nodes"]])
        with self.assertRaisesRegex(ValueError, "REFERENCE_PIN_MISMATCH"):
            validate_report(r)
        s = fixture_snapshot()
        s.nodes["H01.S01.N01"]["source_record_sha256"] = "f" * 64
        with self.assertRaisesRegex(ValueError, "REFERENCE_PIN_MISMATCH"):
            source_references(s)

    def test_extra_fields_cannot_carry_hidden_source_bodies_through_export(self):
        targets = [lambda r: r, lambda r: r["source"], lambda r: r["nodes"][0],
                   lambda r: r["spheres"][0], lambda r: r["houses"][0], lambda r: r["candidates"][0],
                   lambda r: r["meta145"], lambda r: r["regimes"][0], lambda r: r["epochSynthesis"][0]]
        for target in targets:
            r = deepcopy(self.report)
            target(r)["privateBody"] = "SYNTHETIC_PRIVATE_MARKER"
            with self.assertRaisesRegex(ValueError, "UNDECLARED_FIELDS"):
                export_bundle(r)

    def test_module_disk_mutation_after_import_is_rejected(self):
        with patch("src.beast20.long_horizon.Path.read_bytes", return_value=b"changed module"):
            with self.assertRaisesRegex(ValueError, "MODULE_CHANGED_AFTER_IMPORT"):
                _assert_module_identity()

    def test_native_binary_is_checked_before_and_after_dispatch(self):
        with self.assertRaisesRegex(ValueError, "ENGINE_BINARY_IDENTITY"):
            execute_engine(self.binary, self.c, epochs=1, years=1, indices=[143], expected_binary_sha256="f" * 64)
        target = Path(self.tmp.name) / "mutable-engine"
        shutil.copy2(self.binary, target)
        run = subprocess.run
        def mutate_after_run(*args, **kwargs):
            result = run(*args, **kwargs)
            target.write_bytes(target.read_bytes() + b"\n")
            return result
        with patch("src.beast20.long_horizon.subprocess.run", side_effect=mutate_after_run):
            with self.assertRaisesRegex(ValueError, "ENGINE_BINARY_CHANGED_DURING_RUN"):
                execute_engine(target, self.c, epochs=1, years=1, indices=[143])

    def test_hypotheses_use_training_only_regime_metrics(self):
        proposed = {row["id"]: row for row in self.report["meta145"]["upgradeHypotheses"]}
        raw = self.raw["audit"]["trainRegimes"]
        self.assertEqual(proposed["source-gate"]["evidence"]["heldRequests"], metric_record(raw[10][1])["heldRequests"])
        self.assertEqual(proposed["admission"]["evidence"]["stressFreshCompletions"], metric_record(raw[8][1])["freshCompletions"])
        self.assertEqual(sum_metrics(metric_record(r[1]) for r in raw), self.report["candidates"][self.raw["selectedIndex"]]["train"])

    def test_holdout_and_final_winner_tampering_rejected(self):
        for change in (lambda r: r["epochSynthesis"][36].update(acceptedChange=True),
                       lambda r: r["epochSynthesis"][36].update(epochWinnerCandidateId=candidate_id(0)),
                       lambda r: r["meta145"].update(selectedCandidateId=candidate_id(1727))):
            r = deepcopy(self.report)
            change(r)
            with self.assertRaises(ValueError):
                validate_report(r)

    def test_invalid_json_metrics_and_oversized_numbers_rejected(self):
        for value in (float("nan"), float("inf"), 1.1, MAX_SAFE_INTEGER + 1):
            r = deepcopy(self.report)
            r["execution"]["elapsedNs"] = value
            with self.assertRaises(ValueError):
                validate_report(r)


if __name__ == "__main__":
    unittest.main()
