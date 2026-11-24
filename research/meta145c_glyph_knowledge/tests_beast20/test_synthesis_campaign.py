"""R13 regressions for the actual campaign harness and retained witness.

All observations in these tests are synthetic. Temporary byte mirrors exercise
source drift without modifying the real executor, pinned receipt or Work input.
"""
from __future__ import annotations

import asyncio
from contextlib import redirect_stdout
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock


PACKAGE = Path(__file__).resolve().parents[1]
RUNNER_PATH = PACKAGE / "benchmarks/run_synthesis20_campaign.py"
spec = importlib.util.spec_from_file_location("_tested_synthesis_campaign", RUNNER_PATH)
campaign = importlib.util.module_from_spec(spec)
spec.loader.exec_module(campaign)


def copy(value):
    return json.loads(json.dumps(value))


def reencode(output):
    result = output["result"]
    result["sha256"] = campaign.evidence_sha256({key: value for key, value in result.items() if key != "sha256"})
    return campaign.canonical(output)


def work_input(count=4, *, deferred=False):
    rows = []
    for number in range(1, count + 1):
        rows.append({"round": number, "record": {
            "roomId": "private-campaign-test-only", "seq": number,
            "requestId": "private-fixture-request-" + str(number), "memberId": "private-test-member",
            "kind": "objection" if deferred and number == 10 else "revision" if deferred and number == 20 else "summary",
            "topic": "SYNTHETIC FIXTURE ROUND", "text": "PRIVATE SYNTHETIC TEST BODY " + str(number),
            "parentSeq": 10 if deferred and number == 20 else None,
            "referenceSeqs": [10] if deferred and number == 20 else [],
            "evidenceRefs": [], "createdAt": "2026-01-01T00:00:00Z"}})
    return {"schema": "atlas.beast20.observed-work-input/v1", "rounds": rows,
            "deferredClaim": {"challengeRound": 10, "responseRound": 20} if deferred else None}


class CampaignArtifactIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.payload = {"caseId": "F09", "artifactKind": "LOCAL_REVIEW_RESULT"}
        self.built = campaign.build_review(self.payload, {})

    def accept(self, output, expected_parents=()):
        return campaign.validate_review_artifact(reencode(output), output, self.payload, expected_parents)

    def test_original_four_attacks_now_reject_genuine_still_passes(self):
        self.assertTrue(campaign.validate_review_artifact(self.built.artifact, self.built.output, self.payload, ()))
        for attack in ("loss-erasure", "causes-removed", "inflated-count", "forged-parent"):
            with self.subTest(attack=attack):
                output = copy(self.built.output)
                if attack == "loss-erasure":
                    row = next(row for row in output["result"]["results"] if row["method"] == "VALUES_ONLY_ALL_DOMAINS")
                    self.assertFalse(row["matchesBoth"])
                    row.update(matchesBoth=True, lossReasons=[])
                elif attack == "causes-removed":
                    row = next(row for row in output["result"]["results"] if row["method"] == "FULL_KEYED_PROVENANCE")
                    self.assertTrue(row["causeRows"])
                    row["causeRows"] = []
                elif attack == "inflated-count":
                    output["result"]["counts"]["registeredModuleCalls"] = 999
                else:
                    output["parentArtifactSha256"] = ["f" * 64]
                self.assertFalse(self.accept(output))

    def test_unknown_field_policy_schema_and_source_forgeries_reject(self):
        attacks = [lambda result: result.update(unreviewedClaim="invented capability"),
                   lambda result: result.update(schema="unreviewed.schema/v1"),
                   lambda result: result.update(policySha256="f" * 64),
                   lambda result: result["implementationSha256"].update(runner="f" * 64),
                   lambda result: result.update(scope="verified resident implementation")]
        for mutation in attacks:
            output = copy(self.built.output)
            mutation(output["result"])
            self.assertFalse(self.accept(output))

    def test_baseline_identity_and_error_rewrites_cannot_erase_a_loss(self):
        output = copy(self.built.output)
        row = next(row for row in output["result"]["results"] if row["method"] == "VALUES_ONLY_ALL_DOMAINS")
        row.update(afterIdentity="f" * 64, identityRelation="CHANGED", reviewDecision="RECHECK_REQUIRED",
                   identityMatches=True, decisionMatches=True, matchesBoth=True, lossReasons=[], error=None)
        self.assertFalse(self.accept(output))

    def test_actual_parent_witness_must_match_not_just_look_like_a_digest(self):
        parent = {"gate:previous": {"artifactSha256": "a" * 64}}
        built = campaign.build_review(self.payload, parent)
        self.assertTrue(campaign.validate_review_artifact(built.artifact, built.output, self.payload, ("a" * 64,)))
        self.assertFalse(campaign.validate_review_artifact(built.artifact, built.output, self.payload, ("b" * 64,)))
        self.assertFalse(campaign.validate_review_artifact(built.artifact, built.output, self.payload, ()))

    def test_positive_and_negative_checks_do_not_reexecute_falsifier(self):
        with mock.patch.object(campaign, "run_case", side_effect=AssertionError("unexpected extra computation")):
            self.assertTrue(campaign.check_positive(self.built.artifact, self.built.output, self.payload, ()))
            self.assertTrue(campaign.check_negative(self.built.artifact, self.built.output, self.payload, ()))

    def test_all_twenty_actual_cases_match_retained_complete_witness(self):
        for number in range(1, 21):
            payload = {"caseId": f"F{number:02d}", "artifactKind": "LOCAL_REVIEW_RESULT"}
            built = campaign.build_review(payload, {})
            self.assertTrue(campaign.check_positive(built.artifact, built.output, payload, ()))
            self.assertTrue(campaign.check_negative(built.artifact, built.output, payload, ()))
        # Complete coverage includes a real modeled failure and missing evidence,
        # which are preserved inside the passing contract-integrity checks.
        failed = campaign.build_review({"caseId": "F17"}, {})
        held = campaign.build_review({"caseId": "F18"}, {})
        self.assertEqual(failed.output["result"]["expected"]["reviewDecision"], "FAIL")
        self.assertEqual(held.output["result"]["expected"]["reviewDecision"], "HOLD")

    def test_retained_receipt_byte_change_rejects_before_semantic_comparison(self):
        with tempfile.TemporaryDirectory() as directory:
            mirror = Path(directory) / "receipt.json"
            mirror.write_bytes(campaign.SOURCE_PATHS["falsifier-receipt"].read_bytes() + b"\n")
            with mock.patch.dict(campaign.SOURCE_PATHS, {"falsifier-receipt": mirror}):
                with self.assertRaisesRegex(ValueError, "RETAINED_FALSIFIER_CHANGED"):
                    campaign.check_positive(self.built.artifact, self.built.output, self.payload, ())


class CampaignActualExecutionTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def arguments(self, *, count=4, deferred=False):
        private = self.root / "private-observations.json"
        private.write_bytes(campaign.canonical(work_input(count, deferred=deferred)))
        return SimpleNamespace(peer_observations=private, output_dir=self.root / "outputs",
                               allow_partial=count < 20, replace=False)

    async def run_harness(self, args):
        with redirect_stdout(io.StringIO()):
            await campaign.execute(args)
        return json.loads((args.output_dir / "CAMPAIGN_EXECUTION.json").read_text())

    async def test_actual_four_case_run_replay_and_public_export_redaction(self):
        args = self.arguments()
        proof = await self.run_harness(args)
        self.assertEqual(proof["campaignStatus"], "HOLD")
        self.assertEqual(proof["counts"]["ordersComputed"], 4)
        self.assertEqual(proof["counts"]["executorCalls"], 8)
        self.assertEqual(proof["counts"]["testReceipts"], 8)
        self.assertEqual(proof["replayCounts"]["ordersComputed"], 0)
        self.assertEqual(proof["replayCounts"]["executorCalls"], 0)
        self.assertEqual(proof["replayCounts"]["implementedOrders"], 0)
        self.assertEqual(proof["replayCounts"]["ordersReused"], 4)
        self.assertEqual(proof["counts"]["canonicalTasksCompleted"], 0)
        bundle = json.loads((args.output_dir / "CAMPAIGN_BUNDLE.json").read_text())
        self.assertEqual(hashlib.sha256(bundle["reportJson"].encode()).hexdigest(), proof["reportSha256"])
        public = "".join(path.read_text() for path in args.output_dir.glob("*.json"))
        for hidden in ("private-campaign-test-only", "private-test-member", "private-fixture-request", "PRIVATE SYNTHETIC TEST BODY", str(self.root)):
            self.assertNotIn(hidden, public)

    async def test_quality_claim_holds_two_orders_without_blocking_independent_cases(self):
        args = self.arguments(count=20, deferred=True)
        proof = await self.run_harness(args)
        report = json.loads((args.output_dir / "CAMPAIGN_REPORT.json").read_text())
        held = [row["round"] for row in report["orders"] if row["status"] == "HOLD"]
        self.assertEqual(held, [10, 20])
        self.assertEqual(proof["counts"]["ordersComputed"], 18)
        self.assertEqual(proof["counts"]["ordersPassed"], 18)
        self.assertEqual(proof["counts"]["ordersHeld"], 2)
        self.assertEqual(proof["counts"]["observedReviewRounds"], 20)
        self.assertEqual(proof["counts"]["executorCalls"], 40)
        self.assertEqual(proof["counts"]["testReceipts"], 36)
        self.assertEqual(proof["replayCounts"]["executorCalls"], 0)
        self.assertEqual(proof["counts"]["unresolvedChallenges"], 1)
        self.assertEqual(report["challenges"][0]["status"], "DEFERRED")

    async def test_source_change_after_import_prevents_any_new_order_or_report(self):
        args = self.arguments()
        mirror = self.root / "executor-mirror.py"
        mirror.write_bytes(campaign.SOURCE_PATHS["executor"].read_bytes() + b"\n# changed test mirror\n")
        with mock.patch.dict(campaign.SOURCE_PATHS, {"executor": mirror}), mock.patch.object(campaign, "build_review", wraps=campaign.build_review) as build:
            with self.assertRaisesRegex(ValueError, "SOURCE_CHANGED_AFTER_IMPORT"):
                await campaign.execute(args)
            self.assertEqual(build.call_count, 0)
        self.assertFalse(args.output_dir.exists())

    async def test_source_change_during_work_does_not_publish_a_success_receipt(self):
        args = self.arguments()
        mirror = self.root / "executor-mirror.py"
        mirror.write_bytes(campaign.SOURCE_PATHS["executor"].read_bytes())
        original = campaign.build_review
        calls = []
        def change_source(payload, parents):
            calls.append(payload["caseId"])
            built = original(payload, parents)
            mirror.write_bytes(mirror.read_bytes() + b"\n# source changed during observed work\n")
            return built
        with mock.patch.dict(campaign.SOURCE_PATHS, {"executor": mirror}), mock.patch.object(campaign, "build_review", side_effect=change_source):
            with self.assertRaisesRegex(ValueError, "CAMPAIGN_SOURCE_CHANGED"):
                await campaign.execute(args)
        self.assertEqual(calls, ["F01"])
        self.assertFalse((args.output_dir / "CAMPAIGN_EXECUTION.json").exists())
        self.assertFalse((args.output_dir / "CAMPAIGN_REPORT.json").exists())

    async def test_private_observation_change_during_work_does_not_publish_receipt(self):
        args = self.arguments()
        original = campaign.build_review
        calls = []
        def change_observation(payload, parents):
            calls.append(payload["caseId"])
            built = original(payload, parents)
            data = json.loads(args.peer_observations.read_bytes())
            data["rounds"][0]["record"]["text"] = "changed observation bytes"
            args.peer_observations.write_bytes(campaign.canonical(data))
            return built
        with mock.patch.object(campaign, "build_review", side_effect=change_observation):
            with self.assertRaisesRegex(ValueError, "OBSERVED_INPUT_CHANGED"):
                await campaign.execute(args)
        self.assertEqual(calls, ["F01"])
        self.assertFalse((args.output_dir / "CAMPAIGN_EXECUTION.json").exists())

    async def test_duplicate_observed_message_cannot_fill_another_round(self):
        args = self.arguments()
        data = json.loads(args.peer_observations.read_bytes())
        data["rounds"][1]["record"] = data["rounds"][0]["record"]
        args.peer_observations.write_bytes(campaign.canonical(data))
        with self.assertRaisesRegex(ValueError, "OBSERVED_MESSAGE_REUSED"):
            await campaign.execute(args)
        self.assertFalse(args.output_dir.exists())


if __name__ == "__main__":
    unittest.main()
