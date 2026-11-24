"""Configuration simulation contracts, not claims of live model execution."""
from copy import deepcopy
import math
import unittest

from src.beast20.strategy_lab import (BATCH_SIZES, CACHE_ENTRIES, WORKERS, StrategyConfig,
                                     StrategyLab, compact_summary, configurations, digest,
                                     trace_envelope)


SOURCE = "a" * 64


def task(name, *, dependencies=(), wait=0, key=None, house="H01", size=100):
    return {"task_id": name, "house": house, "dependencies": list(dependencies),
            "cache_key": key or digest({"input": name}), "output_digest": digest({"output": name}),
            "result_bytes": size, "cpu_ns": 100, "async_wait_ns": wait}


def fixture():
    rows = [task("a"), task("b", house="H02"), task("sum", dependencies=("a", "b"))]
    return {"schema": "atlas.beast20.strategy-trace/v1", "source_digest": SOURCE,
            "edition": "test-v1", "measurement_kind": "SYNTHETIC_ASSUMED",
            "calibration": {"memo_lookup_ns": 10, "memo_store_ns": 20,
                            "batch_fixed_ns": 100, "batch_item_ns": 5},
            "scenarios": [{"name": "train-cold", "split": "train", "unique_object_count": 24,
                           "tasks": deepcopy(rows)},
                          {"name": "train-warm", "split": "train", "unique_object_count": 24,
                           "tasks": deepcopy(rows)},
                          {"name": "holdout-cold", "split": "holdout", "unique_object_count": 24,
                           "tasks": deepcopy(rows)}]}


def evaluate(payload=None, **kwargs):
    envelope = trace_envelope(fixture() if payload is None else payload)
    return StrategyLab(SOURCE, "test-v1").evaluate(envelope, expected_trace_sha256=envelope["sha256"], **kwargs)


class StrategyLabTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = evaluate()

    def test_exact_1728_unique_runtime_configs(self):
        rows = configurations()
        self.assertEqual(len(rows), 1728)
        self.assertEqual(len({tuple(r.as_dict().values()) for _, r in rows}), 1728)
        self.assertEqual(len({name for name, _ in rows}), 1728)
        self.assertEqual(rows[0][0], "H01.S01.N01")
        self.assertEqual(rows[-1][0], "H12.S12.N12")

    def test_axis_bounds_match_existing_runtime(self):
        self.assertEqual(len(WORKERS), 12)
        self.assertEqual(len(CACHE_ENTRIES), 12)
        self.assertEqual(len(BATCH_SIZES), 12)
        self.assertLessEqual(max(BATCH_SIZES), 400)
        for _, config in configurations():
            self.assertEqual(StrategyConfig(**config.as_dict()), config)

    def test_counts_and_meta145(self):
        self.assertEqual(self.report["candidate_count"], 1728)
        self.assertEqual(len(self.report["spheres"]), 144)
        self.assertEqual(len(self.report["houses"]), 12)
        self.assertTrue(all(s["candidate_count"] == 12 for s in self.report["spheres"]))
        self.assertTrue(all(h["candidate_count"] == 144 for h in self.report["houses"]))
        self.assertEqual(self.report["meta145"]["status"], "SELECTED_FOR_MEASURED_REPLAY")

    def test_deterministic_report_digest_and_ties(self):
        self.assertEqual(self.report, evaluate())
        self.assertEqual(self.report["meta145"]["selected"]["config"]["workers"], 1)

    def test_simulation_labels_no_measured_speedup_claim(self):
        self.assertEqual(self.report["status"], "SIMULATED")
        self.assertFalse(self.report["non_claims"]["measured_speedup"])
        self.assertFalse(self.report["non_claims"]["global_optimum_proven"])
        self.assertEqual(self.report["non_claims"]["model_calls"], 0)
        self.assertEqual(self.report["non_claims"]["resident_turns"], 0)
        self.assertEqual(self.report["units"]["time"], "nanoseconds")
        self.assertIn("NOT_ONTOLOGY", self.report["coordinate_role"])

    def test_expected_trace_checksum_required(self):
        env = trace_envelope(fixture())
        with self.assertRaisesRegex(ValueError, "TRACE_DIGEST_MISMATCH"):
            StrategyLab(SOURCE, "test-v1").evaluate(env, expected_trace_sha256="f" * 64)
        env["payload"]["scenarios"][0]["tasks"][0]["cpu_ns"] += 1
        with self.assertRaisesRegex(ValueError, "TRACE_DIGEST_MISMATCH"):
            StrategyLab(SOURCE, "test-v1").evaluate(env, expected_trace_sha256=env["sha256"])

    def test_source_and_edition_bound(self):
        env = trace_envelope(fixture())
        for source, edition in (("b" * 64, "test-v1"), (SOURCE, "other")):
            with self.assertRaisesRegex(ValueError, "TRACE_SOURCE_IDENTITY_MISMATCH"):
                StrategyLab(source, edition).evaluate(env, expected_trace_sha256=env["sha256"])

    def test_bad_identity_and_budget(self):
        for value in (None, "", "x" * 64, "a" * 63):
            with self.assertRaises(ValueError):
                StrategyLab(value, "test-v1")
        for count in (0, 1727, 1729, True):
            with self.assertRaisesRegex(ValueError, "EXACT_EVALUATION"):
                StrategyLab(SOURCE, "test-v1", max_evaluations=count)

    def test_duplicate_scenarios_rejected(self):
        p = fixture()
        p["scenarios"][1]["name"] = p["scenarios"][0]["name"]
        with self.assertRaisesRegex(ValueError, "DUPLICATE_SCENARIO"):
            evaluate(p)

    def test_train_and_holdout_required(self):
        p = fixture()
        for row in p["scenarios"]:
            row["split"] = "train"
        with self.assertRaisesRegex(ValueError, "TRAIN_AND_HOLDOUT_REQUIRED"):
            evaluate(p)

    def test_holdout_does_not_select_winner(self):
        p = fixture()
        for row in p["scenarios"][-1]["tasks"]:
            row["cpu_ns"] *= 1000
        changed = evaluate(p)
        self.assertEqual(changed["meta145"]["selected"]["id"], self.report["meta145"]["selected"]["id"])
        self.assertEqual(changed["pareto_candidate_ids"], self.report["pareto_candidate_ids"])
        self.assertFalse(changed["holdout_used_for_selection"])

    def test_holdout_regression_retained(self):
        p = fixture()
        p["scenarios"][0]["tasks"] = [task("only")]
        p["scenarios"][1]["tasks"] = [task("only")]
        p["scenarios"][2]["tasks"] = [task(f"cold{i}") for i in range(8)]
        p["scenarios"].append({"name": "holdout-repeat", "split": "holdout", "unique_object_count": 24,
                                "tasks": [task(f"cold{i}") for i in range(8)]})
        result = evaluate(p)
        self.assertTrue(result["meta145"]["holdout_regression"])
        self.assertLess(result["meta145"]["predicted_holdout_ratio_baseline_over_candidate"], 1)

    def test_nonfinite_and_boolean_durations_rejected(self):
        for value in (float("inf"), float("nan"), -1, True, 1.5):
            p = fixture()
            p["scenarios"][0]["tasks"][0]["cpu_ns"] = value
            with self.assertRaises(ValueError):
                evaluate(p)

    def test_zero_time_invalid(self):
        p = fixture()
        p["scenarios"][0]["tasks"][0]["cpu_ns"] = 0
        with self.assertRaisesRegex(ValueError, "ZERO_SERVICE_TIME"):
            evaluate(p)

    def test_task_and_scenario_size_bounds(self):
        p = fixture()
        p["scenarios"][0]["tasks"] *= 1366
        with self.assertRaisesRegex(ValueError, "TRACE_TASK_COUNT"):
            evaluate(p)
        p = fixture()
        p["scenarios"] *= 9
        with self.assertRaisesRegex(ValueError, "SCENARIO_COUNT"):
            evaluate(p)

    def test_unknown_and_duplicate_dependencies(self):
        for parents, error in ((["missing"], "UNKNOWN_TRACE_DEPENDENCY"), (["b", "b"], "DUPLICATE_TRACE_DEPENDENCY")):
            p = fixture()
            p["scenarios"][0]["tasks"][0]["dependencies"] = parents
            with self.assertRaisesRegex(ValueError, error):
                evaluate(p)

    def test_cycle_rejected_before_simulation(self):
        p = fixture()
        p["scenarios"][0]["tasks"][0]["dependencies"] = ["sum"]
        with self.assertRaisesRegex(ValueError, "CYCLIC_TRACE"):
            evaluate(p)

    def test_duplicate_task_rejected(self):
        p = fixture()
        p["scenarios"][0]["tasks"][1]["task_id"] = "a"
        with self.assertRaisesRegex(ValueError, "DUPLICATE_TRACE_TASK"):
            evaluate(p)

    def test_cache_key_output_conflict_rejected(self):
        p = fixture()
        p["scenarios"][0]["tasks"][1]["cache_key"] = p["scenarios"][0]["tasks"][0]["cache_key"]
        with self.assertRaisesRegex(ValueError, "CACHE_KEY_OUTPUT_CONFLICT"):
            evaluate(p)

    def test_sync_work_does_not_get_fictional_multicore_gain(self):
        rows = {r["slot"]: r for r in self.report["candidates"]}
        self.assertEqual(rows["H01.S05.N12"]["train"], rows["H12.S05.N12"]["train"])
        self.assertLessEqual(self.report["unique_scheduler_replays"], 26)

    def test_explicit_async_wait_can_overlap(self):
        p = fixture()
        for scenario in p["scenarios"]:
            scenario["tasks"] = [task("a", wait=1000), task("b", wait=1000)]
        rows = {r["slot"]: r for r in evaluate(p)["candidates"]}
        self.assertLess(rows["H02.S05.N12"]["train"]["predicted_wall_ns"], rows["H01.S05.N12"]["train"]["predicted_wall_ns"])

    def test_singleflight_simulated_only_for_equal_keys_and_outputs(self):
        p = fixture()
        first = task("a", wait=1000)
        second = deepcopy(first)
        second["task_id"] = "alias"
        for scenario in p["scenarios"]:
            scenario["tasks"] = [first, second]
        rows = {r["slot"]: r for r in evaluate(p)["candidates"]}
        self.assertGreater(rows["H02.S05.N12"]["train"]["singleflight_coalesced"], 0)

    def test_weight_validation(self):
        for weights in ({}, {"latency": 1}, {"latency": math.nan, "cpu": 0, "cache_reservation": 0, "workers": 0},
                        {"latency": 0, "cpu": 0, "cache_reservation": 0, "workers": 0}):
            with self.assertRaisesRegex(ValueError, "OBJECTIVE"):
                evaluate(weights=weights)

    def test_constraints_apply_to_candidates(self):
        result = evaluate(constraints={"max_workers": 2, "max_memo_entries": 8, "max_chunk_size": 16})
        eligible = [r for r in result["candidates"] if r["eligible"]]
        self.assertEqual(len(eligible), 2 * 4 * 5)
        self.assertTrue(all(r["config"]["workers"] <= 2 for r in eligible))

    def test_no_feasible_configuration_explicit(self):
        report = evaluate(constraints={"max_predicted_memo_bytes": 1})
        self.assertEqual(report["meta145"]["status"], "NO_FEASIBLE_STRATEGY")
        self.assertIsNone(report["meta145"]["selected"])
        self.assertEqual(report["pareto_candidate_ids"], [])

    def test_constraint_unknown_or_invalid_rejected(self):
        for value in ({"magic_budget": 5}, {"max_workers": True}, {"max_chunk_size": 401}):
            with self.assertRaisesRegex(ValueError, "CONSTRAINT"):
                evaluate(constraints=value)

    def test_pareto_frontier_only_eligible_and_not_empty(self):
        candidates = {r["id"]: r for r in self.report["candidates"]}
        self.assertTrue(self.report["pareto_candidate_ids"])
        for name in self.report["pareto_candidate_ids"]:
            self.assertTrue(candidates[name]["eligible"])

    def test_compact_summary_retains_integrity_and_decisions(self):
        result = compact_summary(self.report)
        self.assertNotIn("candidates", result)
        self.assertEqual(result["candidate_rows_omitted"], 1728)
        self.assertEqual(result["full_report_sha256"], self.report["report_sha256"])
        self.assertEqual(result["meta145"], self.report["meta145"])
        self.assertEqual(result["summary_sha256"], digest({k: v for k, v in result.items() if k != "summary_sha256"}))

    def test_tampered_report_rejected(self):
        report = deepcopy(self.report)
        report["candidate_count"] = 1729
        with self.assertRaisesRegex(ValueError, "STRATEGY_REPORT_DIGEST"):
            compact_summary(report)

    def test_measured_trace_label_does_not_become_attestation(self):
        p = fixture()
        p["measurement_kind"] = "MEASURED_HANDLER_SERVICE_TIMES"
        report = evaluate(p)
        self.assertEqual(report["measurement_attestation"], "CALLER_SUPPLIED_TRACE_WITH_CHECKSUM")
        self.assertFalse(report["non_claims"]["measured_speedup"])


if __name__ == "__main__":
    unittest.main()
