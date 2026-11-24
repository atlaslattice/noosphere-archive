"""Real local executor seams for the bounded synthesis coordinator.

Peer rows here are explicitly synthetic test observations, never live people.
The optional source-mounted tests consume the genuine existing package/plan.
"""
from __future__ import annotations

import asyncio
from dataclasses import replace
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest

from src.beast20.synthesis import (
    ArtifactResult, BuildOrder, ChallengeDisposition, ExcellenceBinding,
    LocalCheck, LocalHandler, REGISTRY_SHA256, SynthesisCoordinator,
    compact_summary, evidence_sha256, make_order_provenance,
    make_peer_observation, report_bundle, validate_report,
)
from src.beast20.synthesis_provenance import make_provenance
from src.beast20.federation import PinnedFederation
from src.beast20.storage import Scope


def sha(value):
    return hashlib.sha256(value).hexdigest()


def observed(seq=1, *, kind="proposal", parent=None, room="private-test-room"):
    return make_peer_observation({"roomId": room, "seq": seq,
        "requestId": "private-request-" + str(seq), "memberId": "private-member",
        "kind": kind, "topic": "synthetic test review", "text": "PRIVATE TEST MESSAGE BODY " + str(seq),
        "parentSeq": parent, "referenceSeqs": [] if parent is None else [parent],
        "evidenceRefs": ["https://example.invalid/test-fixture"],
        "createdAt": "2026-01-01T00:00:00Z"})


def alter(record, *, field="inputs", key="source", value=None):
    fields = {k: dict(record[k]) for k in ("inputs", "dependencies", "peer_evidence", "checks")}
    code = record["code_sha256"]
    if field == "code_sha256":
        code = value
    elif value is None:
        fields[field].pop(key, None)
    else:
        fields[field][key] = value
    return make_provenance(code_sha256=code, **fields)


class SynthesisExecutionTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.peers = [observed()]
        self.handler_count = self.check_count = self.probe_count = 0
        self.current_source = sha(b"source-v1")
        self.permission = True
        self.handler_sha = sha(b"trusted test handler v1")
        self.positive_sha = sha(b"trusted positive check v1")
        self.negative_sha = sha(b"trusted negative check v1")
        self.coordinators = []

    def tearDown(self):
        for coordinator in self.coordinators:
            coordinator.close()
        self.temp.cleanup()

    def handler(self, payload, parents):
        self.handler_count += 1
        return ArtifactResult(("artifact:" + str(payload["n"])).encode(),
                              {"n": payload["n"], "parents": len(parents)})

    def positive(self, artifact, output, payload):
        self.check_count += 1
        return artifact == ("artifact:" + str(payload["n"])).encode() and output["n"] == payload["n"]

    def negative(self, artifact, output, payload):
        self.check_count += 1
        # The negative control is a deliberately wrong artifact/output pair.
        return artifact != b"wrong-artifact" and output["n"] != -1

    def probe(self, order):
        self.probe_count += 1
        return alter(order["provenance"], value=self.current_source)

    def coordinator(self, *, handler=None, positive=None, negative=None, probe=None, authorize=None,
                    acceptance=None, database="work.db", workers=4):
        coordinator = SynthesisCoordinator(Path(self.temp.name) / database,
            scope=Scope(REGISTRY_SHA256, "v0.7", "test-owner", 1), campaign_id="private-test-room",
            handlers={"build": LocalHandler(handler or self.handler, self.handler_sha)},
            checks={"positive": LocalCheck(positive or self.positive, "POSITIVE", self.positive_sha),
                    "negative": LocalCheck(negative or self.negative, "NEGATIVE", self.negative_sha)},
            observe_provenance=probe or self.probe,
            authorize=authorize or (lambda scope, phase: self.permission), acceptance=acceptance, workers=workers)
        self.coordinators.append(coordinator)
        return coordinator

    def order(self, number=1, *, deps=(), peers=None, check_ids=("positive", "negative"),
              subject_sha=None, challenge_refs=(), acceptance_task_id=None):
        peer_rows = self.peers if peers is None else peers
        refs = tuple(row["sha256"] for row in peer_rows)
        subject = {"artifactId": "source-module-" + str(number), "baselineSha256": subject_sha or sha(b"baseline")}
        payload = {"n": number}
        check_codes = {key: {"positive": self.positive_sha, "negative": self.negative_sha}[key] for key in check_ids}
        provenance = make_order_provenance(handler_code_sha256=self.handler_sha, payload=payload, subject=subject,
            dependencies={item.order_id: item.provenance["sha256"] for item in deps}, peer_refs=refs,
            check_codes=check_codes, inputs={"source": self.current_source})
        return BuildOrder("O%02d" % number, number, "build", payload, subject, provenance,
            dependencies=tuple(item.order_id for item in deps), check_ids=tuple(check_ids), peer_refs=refs,
            challenge_refs=tuple(challenge_refs), acceptance_task_id=acceptance_task_id)

    async def test_real_executor_pass_receipts_and_public_redaction(self):
        report = await self.coordinator().run([self.order()], peer_observations=self.peers)
        row = report["orders"][0]
        self.assertEqual((report["status"], row["status"], row["phase"]), ("HOLD", "PASS", "TESTED"))
        self.assertEqual((self.handler_count, self.check_count), (1, 2))
        self.assertEqual((report["counts"]["executorCalls"], report["counts"]["implementedOrders"]), (2, 1))
        self.assertEqual(row["executor"], {"evaluationStatus": "SUCCEEDED", "gateStatus": "SUCCEEDED", "actualCalls": 2, "handlerCalls": 1})
        self.assertEqual(row["artifactSha256"], sha(b"artifact:1"))
        self.assertTrue(all(x["subjectSha256"] == row["artifactSha256"] and x["outputSha256"] == row["outputSha256"] for x in row["checks"]))
        body = report_bundle(report)["reportJson"]
        for private in ("PRIVATE TEST MESSAGE BODY", "private-test-room", "private-member", "private-request", "artifact:1", self.temp.name):
            self.assertNotIn(private, body)
        self.assertEqual(report["counts"]["canonicalTasksCompleted"], 0)
        self.assertEqual(report["counts"]["genuineResidentTurns"], 0)

    async def test_twenty_distinct_orders_complete_with_bounded_actual_counts(self):
        peers = [observed(index) for index in range(1, 21)]
        orders = [self.order(index, peers=[peer]) for index, peer in enumerate(peers, 1)]
        report = await self.coordinator().run(orders, peer_observations=peers)
        self.assertEqual(report["status"], "PASS")
        self.assertEqual(report["counts"]["observedReviewRounds"], 20)
        self.assertEqual(report["counts"]["ordersComputed"], 20)
        self.assertEqual(report["counts"]["executorCalls"], 40)
        self.assertEqual(report["counts"]["testReceipts"], 40)
        self.assertEqual(report["counts"]["implementedOrders"], 20)
        self.assertEqual((self.handler_count, self.check_count), (20, 40))

    async def test_durable_replay_has_zero_new_work_and_retained_receipts(self):
        coordinator = self.coordinator()
        order = self.order()
        first = await coordinator.run([order], peer_observations=self.peers)
        second = await coordinator.run([order], peer_observations=self.peers)
        self.assertEqual(second["orders"][0]["phase"], "VERIFIED_REUSE")
        self.assertEqual(second["counts"]["executorCalls"], 0)
        self.assertEqual(second["counts"]["implementedOrders"], 0)
        self.assertEqual(second["counts"]["ordersComputed"], 0)
        self.assertEqual(second["orders"][0]["checks"], first["orders"][0]["checks"])
        self.assertEqual((self.handler_count, self.check_count), (1, 2))
        coordinator.close()
        self.coordinators.remove(coordinator)
        third = await self.coordinator().run([order], peer_observations=self.peers)
        self.assertEqual(third, second)

    async def test_round_relabel_does_not_create_a_new_implementation(self):
        coordinator = self.coordinator()
        order = self.order()
        await coordinator.run([order], peer_observations=self.peers)
        renamed = replace(order, order_id="another-public-label", round_number=2)
        report = await coordinator.run([renamed], peer_observations=self.peers)
        self.assertEqual(report["orders"][0]["phase"], "VERIFIED_REUSE")
        self.assertEqual(report["counts"]["ordersComputed"], 0)
        self.assertEqual(report["counts"]["executorCalls"], 1)  # new gate, reused evaluation
        self.assertEqual(self.handler_count, 1)

    async def test_same_evidence_singleflight_counts_shared_call_once(self):
        async def delayed(payload, parents):
            await asyncio.sleep(0)
            return self.handler(payload, parents)
        coordinator = self.coordinator(handler=delayed)
        one = self.order()
        two = replace(one, order_id="O00", round_number=2)
        report = await coordinator.run([one, two], peer_observations=self.peers)
        self.assertEqual(report["counts"]["ordersComputed"], 1)
        self.assertEqual(report["counts"]["implementedOrders"], 1)
        self.assertEqual(report["counts"]["ordersReused"], 1)
        self.assertEqual(report["counts"]["executorCalls"], 3)
        self.assertEqual(self.handler_count, 1)

    async def test_no_change_is_tested_but_not_new_implementation(self):
        report = await self.coordinator().run([self.order(subject_sha=sha(b"artifact:1"))], peer_observations=self.peers)
        self.assertEqual(report["orders"][0]["phase"], "NO_CHANGE")
        self.assertEqual(report["counts"]["ordersNoChange"], 1)
        self.assertEqual(report["counts"]["implementedOrders"], 0)

    async def test_negative_check_failure_preserved_and_blocks_dependent_only(self):
        coordinator = self.coordinator(negative=lambda artifact, output, payload: payload["n"] != 1)
        one = self.order()
        two = self.order(2, deps=(one,))
        three = self.order(3)
        report = await coordinator.run([two, three, one], peer_observations=self.peers)
        by_id = {row["id"]: row for row in report["orders"]}
        self.assertEqual([by_id[x]["status"] for x in ("O01", "O02", "O03")], ["FAIL", "HOLD", "PASS"])
        self.assertEqual(by_id["O02"]["executor"]["evaluationStatus"], "BLOCKED_DEPENDENCY")
        self.assertEqual(by_id["O02"]["executor"]["handlerCalls"], 0)
        self.assertEqual([row["passed"] for row in by_id["O01"]["checks"] if row["kind"] == "NEGATIVE"], [False])
        self.assertEqual((report["status"], self.handler_count), ("FAIL", 2))

    async def test_truthy_non_boolean_check_is_failure(self):
        report = await self.coordinator(positive=lambda *args: 1).run([self.order()], peer_observations=self.peers)
        self.assertEqual(report["orders"][0]["status"], "FAIL")

    async def test_handler_and_check_exceptions_never_leak_private_state(self):
        def fail(*args):
            raise RuntimeError("foreign private state / secret-key")
        report = await self.coordinator(handler=fail).run([self.order()], peer_observations=self.peers)
        self.assertEqual(report["orders"][0]["reasonCodes"], ["HANDLER_FAILED"])
        self.assertNotIn("secret", report_bundle(report)["reportJson"])
        other = await self.coordinator(positive=fail, database="check.db").run([self.order()], peer_observations=self.peers)
        self.assertEqual(other["orders"][0]["status"], "FAIL")
        self.assertNotIn("secret", report_bundle(other)["reportJson"])

    async def test_missing_peer_or_positive_negative_evidence_holds_without_build(self):
        for kwargs, expected in (({"peers": []}, "MISSING_PEER_EVIDENCE"),
                                 ({"check_ids": ("positive",)}, "MISSING_NEGATIVE_CHECK"),
                                 ({"check_ids": ("negative",)}, "MISSING_POSITIVE_CHECK")):
            with self.subTest(expected=expected):
                report = await self.coordinator(database=expected + ".db").run([self.order(**kwargs)], peer_observations=self.peers)
                self.assertEqual(report["orders"][0]["status"], "HOLD")
                self.assertIn(expected, report["orders"][0]["reasonCodes"])
        self.assertEqual(self.handler_count, 0)

    async def test_source_stale_before_dispatch_never_builds(self):
        order = self.order()
        self.current_source = sha(b"source-v2")
        report = await self.coordinator().run([order], peer_observations=self.peers)
        self.assertEqual(report["orders"][0]["phase"], "STALE")
        self.assertEqual(report["orders"][0]["staleCauses"][0]["category"], "DATA")
        self.assertTrue(report["orders"][0]["staleCauses"][0]["key"].startswith("key:"))
        self.assertEqual(self.handler_count, 0)

    async def test_cached_results_still_reobserve_changed_source(self):
        coordinator = self.coordinator()
        order = self.order()
        await coordinator.run([order], peer_observations=self.peers)
        self.current_source = sha(b"source-v2")
        report = await coordinator.run([order], peer_observations=self.peers)
        self.assertEqual((report["orders"][0]["phase"], report["counts"]["implementedOrders"]), ("STALE", 0))
        self.assertEqual(self.handler_count, 1)

    async def test_change_during_build_preserves_tests_but_holds_and_blocks_child(self):
        def change(payload, parents):
            result = self.handler(payload, parents)
            self.current_source = sha(b"source-changed-during-build")
            return result
        one = self.order()
        report = await self.coordinator(handler=change).run([one, self.order(2, deps=(one,))], peer_observations=self.peers)
        self.assertEqual(report["orders"][0]["phase"], "STALE")
        self.assertEqual(len(report["orders"][0]["checks"]), 2)
        self.assertEqual(report["orders"][1]["executor"]["evaluationStatus"], "BLOCKED_DEPENDENCY")
        self.assertEqual(report["counts"]["implementedOrders"], 0)

    async def test_all_provenance_change_categories_hold(self):
        for field, key in (("code_sha256", "ignored"), ("dependencies", "other"),
                           ("peer_evidence", "peer"), ("checks", "positive")):
            with self.subTest(field=field):
                coordinator = self.coordinator(probe=lambda order, f=field, k=key: alter(order["provenance"], field=f, key=k, value=sha(b"changed")), database=field + ".db")
                report = await coordinator.run([self.order()], peer_observations=self.peers)
                self.assertEqual(report["orders"][0]["phase"], "STALE")
        self.assertEqual(self.handler_count, 0)

    async def test_provenance_probe_exception_is_a_bounded_hold(self):
        def fail(order):
            raise RuntimeError("private-source-path")
        report = await self.coordinator(probe=fail).run([self.order()], peer_observations=self.peers)
        self.assertEqual(report["orders"][0]["reasonCodes"], ["PROVENANCE_UNAVAILABLE"])
        self.assertIsNone(report["orders"][0]["observedProvenanceSha256"])
        self.assertNotIn("private-source-path", report_bundle(report)["reportJson"])

    async def test_return_permission_gate_also_applies_to_cached_work(self):
        coordinator = self.coordinator()
        order = self.order()
        await coordinator.run([order], peer_observations=self.peers)
        def permission(scope, phase):
            return phase != "RETURN"
        coordinator.authorize = permission
        with self.assertRaisesRegex(PermissionError, "AUTHORIZATION_DENIED"):
            await coordinator.run([order], peer_observations=self.peers)
        self.assertEqual(self.handler_count, 1)

    async def test_scope_mutation_and_truthy_permission_are_rejected(self):
        coordinator = self.coordinator()
        object.__setattr__(coordinator.scope, "rights_epoch", 2)
        with self.assertRaises(PermissionError):
            await coordinator.run([self.order()], peer_observations=self.peers)
        with self.assertRaises(PermissionError):
            self.coordinator(authorize=lambda scope, phase: 1, database="truthy.db")

    async def test_cycles_and_unknown_dependencies_fail_before_probe_or_work(self):
        one, two = self.order(), self.order(2)
        cases = ([replace(one, dependencies=(two.order_id,)), replace(two, dependencies=(one.order_id,))],
                 [replace(one, dependencies=("missing",))])
        coordinator = self.coordinator()
        for orders in cases:
            with self.assertRaises(ValueError):
                await coordinator.run(orders, peer_observations=self.peers)
        self.assertEqual((self.probe_count, self.handler_count), (0, 0))
        self.assertEqual(coordinator.executor.db.execute("SELECT COUNT(*) FROM beast_execution").fetchone()[0], 0)

    async def test_budget_nonfinite_and_bad_namespace_rejected_before_dispatch(self):
        coordinator = self.coordinator()
        cases = ([self.order()] * 21, [replace(self.order(), round_number=True)],
                 [replace(self.order(), payload={"n": float("nan")})],
                 [replace(self.order(), order_id="EX.W01.C01.P01")],
                 [replace(self.order(), order_id="H01.S01.N01")],
                 [replace(self.order(), subject={"artifactId": "/private/path", "baselineSha256": sha(b"old")})])
        for orders in cases:
            with self.subTest(orders=repr(orders)[:60]), self.assertRaises(ValueError):
                await coordinator.run(orders, peer_observations=self.peers)
        self.assertEqual((self.probe_count, self.handler_count), (0, 0))

    async def test_wrong_payload_code_check_peer_or_dependency_pin_rejected(self):
        coordinator = self.coordinator()
        one = self.order()
        for mutation in (replace(one, payload={"n": 77}), replace(one, peer_refs=()),
                         replace(one, check_ids=("positive",)),
                         replace(one, provenance=alter(one.provenance, field="code_sha256", value=sha(b"wrong")))):
            with self.assertRaisesRegex(ValueError, "PROVENANCE_MISMATCH"):
                await coordinator.run([mutation], peer_observations=self.peers)
        self.assertEqual(self.handler_count, 0)

    async def test_unresolved_dissent_is_visible_and_held(self):
        objection = observed(2, kind="objection", parent=1)
        peers = self.peers + [objection]
        order = self.order(peers=peers, challenge_refs=(objection["sha256"],))
        report = await self.coordinator().run([order], peer_observations=peers)
        self.assertEqual(report["orders"][0]["status"], "HOLD")
        self.assertEqual(report["challenges"][0]["status"], "UNRESOLVED")
        self.assertEqual(report["counts"]["unresolvedChallenges"], 1)
        self.assertEqual(self.handler_count, 0)

    async def test_bound_reply_and_checks_preserve_declared_dissent_disposition(self):
        objection = observed(2, kind="objection", parent=1)
        reply = observed(3, kind="revision", parent=2)
        peers = self.peers + [objection, reply]
        order = self.order(peers=peers, challenge_refs=(objection["sha256"],))
        disposition = ChallengeDisposition(objection["sha256"], "ADDRESSED", reply["sha256"], ("positive", "negative"))
        report = await self.coordinator().run([order], peer_observations=peers, dispositions=[disposition])
        self.assertEqual(report["orders"][0]["status"], "PASS")
        self.assertEqual(report["challenges"][0]["status"], "DECLARED_ADDRESSED")
        self.assertEqual(report["challenges"][0]["ref"], objection["sha256"])
        self.assertNotIn("VERIFIED_IDENTITY", json.dumps(report))

    async def test_disposition_without_bound_checks_is_held(self):
        objection, reply = observed(2, kind="objection", parent=1), observed(3, kind="revision", parent=2)
        peers = self.peers + [objection, reply]
        order = self.order(peers=peers, challenge_refs=(objection["sha256"],))
        disposition = ChallengeDisposition(objection["sha256"], "REJECTED", reply["sha256"])
        report = await self.coordinator().run([order], peer_observations=peers, dispositions=[disposition])
        self.assertEqual(report["orders"][0]["status"], "HOLD")
        self.assertIn("DISPOSITION_CHECK_MISSING", report["orders"][0]["reasonCodes"])
        self.assertEqual(report["challenges"][0]["status"], "DECLARED_REJECTED")

    async def test_objection_omission_cross_room_reply_and_conflicting_revision_rejected(self):
        objection = observed(2, kind="objection", parent=1)
        reply = observed(3, kind="revision", parent=2, room="foreign-private-room")
        peers = self.peers + [objection, reply]
        coordinator = self.coordinator()
        with self.assertRaisesRegex(ValueError, "CHALLENGE_REFERENCE"):
            await coordinator.run([self.order(peers=peers)], peer_observations=peers)
        order = self.order(peers=peers, challenge_refs=(objection["sha256"],))
        with self.assertRaisesRegex(ValueError, "REPLY_BINDING"):
            await coordinator.run([order], peer_observations=peers,
                dispositions=[ChallengeDisposition(objection["sha256"], "ADDRESSED", reply["sha256"], ("positive",))])
        record = dict(self.peers[0]["record"])
        record["text"] = "forged alternate revision"
        alternate = make_peer_observation(record)
        with self.assertRaisesRegex(ValueError, "REVISION_CONFLICT"):
            await coordinator.run([self.order()], peer_observations=self.peers + [alternate])
        self.assertEqual(self.handler_count, 0)

    async def test_peer_observation_is_detached_and_tampering_rejected(self):
        peer = observed()
        record = dict(peer["record"])
        detached = make_peer_observation(record)
        record["text"] = "changed outside"
        self.assertNotEqual(detached["record"]["text"], record["text"])
        detached["record"]["text"] = "tampered seal"
        with self.assertRaisesRegex(ValueError, "PEER_HASH_MISMATCH"):
            await self.coordinator().run([], peer_observations=[detached])

    async def test_output_and_artifact_bounds_are_observed_failures(self):
        for index, result in enumerate((ArtifactResult(b"a" * 1048577, {}),
                                        ArtifactResult(b"valid", "x" * 65537),
                                        ArtifactResult(b"valid", {"n": float("inf")}),
                                        {"artifactSha256": sha(b"forged"), "passed": True})):
            report = await self.coordinator(handler=lambda *args, result=result: result, database="bounded%d.db" % index).run(
                [self.order()], peer_observations=self.peers)
            self.assertEqual(report["orders"][0]["reasonCodes"], ["OUTPUT_INVALID"])
            self.assertEqual(report["orders"][0]["status"], "FAIL")
            self.assertFalse(report["orders"][0]["implemented"])

    async def test_actual_parent_output_is_available_to_dependent_handler(self):
        seen = []
        def handle(payload, parents):
            seen.append(parents)
            return self.handler(payload, parents)
        one = self.order()
        report = await self.coordinator(handler=handle).run([one, self.order(2, deps=(one,))], peer_observations=self.peers)
        self.assertEqual([row["status"] for row in report["orders"]], ["PASS", "PASS"])
        self.assertEqual(seen[1]["gate:O01"]["output"]["n"], 1)

    async def test_empty_partial_campaign_is_hold_not_complete(self):
        report = await self.coordinator().run([])
        self.assertEqual(report["status"], "HOLD")
        self.assertEqual(report["counts"]["executorCalls"], 0)
        self.assertTrue(all(row["status"] == "PLANNED" for row in report["rounds"]))

    async def test_unbound_canonical_task_never_earns_local_or_canonical_credit(self):
        order = self.order(acceptance_task_id="EX.W01.C01.P01")
        report = await self.coordinator().run([order], peer_observations=self.peers)
        self.assertEqual(report["orders"][0]["status"], "HOLD")
        self.assertIn("ACCEPTANCE_UNBOUND", report["orders"][0]["reasonCodes"])
        self.assertEqual(report["counts"]["canonicalTasksCompleted"], 0)
        self.assertEqual(self.handler_count, 0)

    async def test_rehashed_wrong_output_receipt_and_false_counts_rejected(self):
        report = await self.coordinator().run([self.order()], peer_observations=self.peers)
        copy = json.loads(json.dumps(report))
        receipt = copy["orders"][0]["checks"][0]
        receipt["outputSha256"] = sha(b"wrong-output")
        receipt["receiptSha256"] = evidence_sha256({"schema": "atlas.beast20.synthesis-check/v1",
            **{key: value for key, value in receipt.items() if key != "receiptSha256"}})
        with self.assertRaisesRegex(ValueError, "SUBJECT_MISMATCH"):
            validate_report(copy)
        copy = json.loads(json.dumps(report))
        copy["counts"]["genuineResidentTurns"] = 20
        with self.assertRaisesRegex(ValueError, "COUNTS_MISMATCH"):
            validate_report(copy)
        copy = json.loads(json.dumps(report))
        copy["orders"][0]["privateRoom"] = "must not leak"
        with self.assertRaisesRegex(ValueError, "ORDER_REPORT_FIELDS"):
            validate_report(copy)

    async def test_bundle_exact_utf8_digest_and_summary_detachment(self):
        report = await self.coordinator().run([self.order()], peer_observations=self.peers)
        bundle = report_bundle(report)
        self.assertEqual(bundle["reportSha256"], sha(bundle["reportJson"].encode("utf-8")))
        self.assertEqual(json.loads(bundle["reportJson"]), report)
        summary = compact_summary(report)
        summary["counts"]["ordersPassed"] = 999
        self.assertEqual(report["counts"]["ordersPassed"], 1)

    async def test_recounted_changed_artifact_cannot_be_promoted_to_no_change(self):
        report = await self.coordinator().run([self.order()], peer_observations=self.peers)
        row = report["orders"][0]
        row.update(phase="NO_CHANGE", implemented=False, reasonCodes=["NO_ARTIFACT_CHANGE"])
        report["counts"].update(implementedOrders=0, ordersNoChange=1)
        with self.assertRaisesRegex(ValueError, "NO_CHANGE_MISMATCH"):
            validate_report(report)

    async def test_passing_order_cannot_carry_a_stale_or_missing_evidence_reason(self):
        report = await self.coordinator().run([self.order()], peer_observations=self.peers)
        for reason in ("SOURCE_STALE", "DEPENDENCY_STALE", "MISSING_PEER_EVIDENCE", "EXECUTOR_FAILED"):
            with self.subTest(reason=reason):
                copy = json.loads(json.dumps(report))
                copy["orders"][0]["reasonCodes"] = [reason]
                with self.assertRaises(ValueError):
                    validate_report(copy)

    async def test_rehashed_deferred_challenge_cannot_coexist_with_affected_pass(self):
        report = await self.coordinator().run([self.order()], peer_observations=self.peers)
        ref = self.peers[0]["sha256"]
        report["orders"][0]["challengeRefs"] = [ref]
        disposition = {"challengeRef": ref, "action": "DEFERRED", "responseRef": None, "checkIds": []}
        report["challenges"] = [{"ref": ref, "orderIds": ["O01"], "status": "DEFERRED", "responseRef": None,
                                  "checkIds": [], "dispositionSha256": evidence_sha256(disposition)}]
        report["counts"]["unresolvedChallenges"] = 1
        with self.assertRaisesRegex(ValueError, "UNRESOLVED_CHALLENGE_PROMOTED"):
            validate_report(report)

    async def test_boolean_counts_and_malformed_enum_reject_as_value_error(self):
        report = await self.coordinator().run([self.order()], peer_observations=self.peers)
        copy = json.loads(json.dumps(report))
        copy["counts"]["canonicalTasksCompleted"] = False
        with self.assertRaisesRegex(ValueError, "COUNT_INTEGER_REQUIRED"):
            validate_report(copy)
        for field in ("status", "phase"):
            copy = json.loads(json.dumps(report))
            copy["orders"][0][field] = ["PASS"]
            with self.assertRaisesRegex(ValueError, "REPORT_INVALID"):
                validate_report(copy)

    async def test_registry_rejects_external_effects_and_forged_acceptance(self):
        args = dict(scope=Scope(REGISTRY_SHA256, "v0.7", "owner", 1), campaign_id="campaign",
                    checks={}, observe_provenance=self.probe, authorize=lambda *args: True)
        with self.assertRaisesRegex(ValueError, "PURE_LOCAL_HANDLER"):
            SynthesisCoordinator(Path(self.temp.name) / "effects.db", handlers={"send": LocalHandler(self.handler, self.handler_sha, "NON_IDEMPOTENT_WRITE")}, **args)
        with self.assertRaisesRegex(ValueError, "GENUINE_ACCEPTANCE_BINDING"):
            SynthesisCoordinator(Path(self.temp.name) / "forged.db", handlers={"build": LocalHandler(self.handler, self.handler_sha)}, acceptance={"passed": True}, **args)
        self.assertFalse((Path(self.temp.name) / "effects.db").exists())


@unittest.skipUnless(os.environ.get("ATLAS_EXCELLENCE_ROOT") and os.environ.get("ATLAS_EXCELLENCE_PLAN"),
                     "Explicit genuine source-mounted Excellence checkout/plan not configured")
class ExistingAcceptanceBindingTests(unittest.TestCase):
    def setUp(self):
        package = Path(__file__).resolve().parents[1]
        inventory = json.loads((package / "docs/native1728/PUBLIC_COMPONENT_INVENTORY.json").read_text())
        self.federation = PinnedFederation.from_inventory(inventory,
            roots={"EXCELLENCE1728_CORE": os.environ["ATLAS_EXCELLENCE_ROOT"]},
            plan_path=os.environ["ATLAS_EXCELLENCE_PLAN"],
            expected_plan_sha256="47084b895a6317db16275a92c3878a340d31af15fb9ab479db7101953c18e49c")
        api, plan = self.federation._plan()
        policy = {"schema": "atlas.excellence.runner-policy.v1", "plan_sha256": self.federation._plan_sha,
                  "allowed_roots": [str(Path(os.environ["ATLAS_EXCELLENCE_ROOT"]).resolve())], "source_paths": {}, "checks": []}
        self.runner = api.AcceptanceRunner(plan, policy, expected_policy_sha256=api.digest(policy),
                                          receipt_key=b"test-only-source-binding-key-32bytes")
        self.ledger = api.EvidenceLedger(plan, self.runner)

    def tearDown(self):
        self.federation.close()

    def test_real_mounted_runner_and_ledger_remain_planned(self):
        binding = ExcellenceBinding(self.federation, self.ledger)
        result = binding.inspect("EX.W01.C01.P01", sha(b"unaccepted local artifact"))
        self.assertEqual(result, {"bound": True, "taskId": "EX.W01.C01.P01", "state": "PLANNED", "subjectMatched": False})
        self.assertEqual(self.ledger.snapshot()["events"], 0)
        self.assertEqual(self.ledger.snapshot()["genuine_macroturns_completed"], 0)

    def test_json_receipt_forgery_cannot_be_bound_as_genuine_ledger(self):
        with self.assertRaisesRegex(ValueError, "GENUINE_PLAN_LEDGER"):
            ExcellenceBinding(self.federation, {"state": "VERIFIED", "passed": True})
        with self.assertRaisesRegex(ValueError, "ENGINEERING_ID"):
            ExcellenceBinding(self.federation, self.ledger).inspect("H01.S01.N01", sha(b"artifact"))


if __name__ == "__main__":
    unittest.main()
