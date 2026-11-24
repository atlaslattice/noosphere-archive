"""Public export schemas and finite-run arithmetic, using local test fixtures."""
import asyncio
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from benchmarks.export_synthesis20_hosts import (
    CAMPAIGN_SOURCE_PATHS, ROOT, campaign_projection, replication_projection,
)
from src.beast20.storage import Scope
from src.beast20.synthesis import (
    ArtifactResult, BuildOrder, ChallengeDisposition, LocalCheck, LocalHandler,
    REGISTRY_SHA256, SynthesisCoordinator, make_order_provenance, make_peer_observation,
    report_bundle,
)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


async def local_reports():
    # These are synthetic client observations for a real local executor test,
    # not Work posts, verified people, or another campaign completion.
    objection = make_peer_observation({"roomId": "export-test", "seq": 1, "requestId": "fixture-one",
        "memberId": "fixture-a", "kind": "objection", "topic": "test", "text": "Quality claim deferred."})
    response = make_peer_observation({"roomId": "export-test", "seq": 2, "requestId": "fixture-two",
        "memberId": "fixture-b", "kind": "decision", "topic": "test", "text": "Preserve the limitation.",
        "parentSeq": 1})
    code = sha(Path(__file__).read_bytes())
    checks = {"positive": LocalCheck(lambda artifact, output, payload: artifact == b"fixture", "POSITIVE", code),
              "negative": LocalCheck(lambda artifact, output, payload: artifact != b"wrong", "NEGATIVE", code)}
    orders = []
    for number, refs in ((1, (objection["sha256"], response["sha256"])), (2, (response["sha256"],))):
        payload = {"fixture": number}
        subject = {"artifactId": "fixture-%d" % number, "baselineSha256": sha(b"")}
        provenance = make_order_provenance(handler_code_sha256=code, payload=payload, subject=subject,
            peer_refs=refs, check_codes={key: code for key in checks})
        orders.append(BuildOrder("fixture-%d" % number, number, "fixture", payload, subject, provenance,
            check_ids=tuple(checks), peer_refs=refs, challenge_refs=(objection["sha256"],) if number == 1 else ()))

    def current(order):
        current_code = sha(Path(__file__).read_bytes())
        return make_order_provenance(handler_code_sha256=current_code, payload=order["payload"],
            subject=order["subject"], peer_refs=order["peerRefs"],
            check_codes={key: current_code for key in order["checkIds"]})

    scope = Scope(REGISTRY_SHA256, "export-test", "local-fixture", "current")
    with tempfile.TemporaryDirectory() as directory:
        coordinator = SynthesisCoordinator(Path(directory) / "fixture.sqlite", scope=scope,
            campaign_id="export-boundary-fixture", handlers={"fixture": LocalHandler(
                lambda payload, parents: ArtifactResult(b"fixture", {"fixture": payload["fixture"]}), code)},
            checks=checks, observe_provenance=current,
            authorize=lambda observed, phase: observed == scope and phase in {"READ", "DISPATCH", "RETURN"})
        try:
            arguments = {"peer_observations": [objection, response], "dispositions": [
                ChallengeDisposition(objection["sha256"], "DEFERRED", response_ref=response["sha256"])]}
            report = await coordinator.run(orders, **arguments)
            replay = await coordinator.run(orders, **arguments)
        finally:
            coordinator.close()
    proof = {"schema": "atlas.beast20.synthesis-campaign-execution/v1", "status": "COMPLETED_LOCAL_CAMPAIGN",
        "campaignStatus": report["status"], "evidenceKind": "LOCAL_REVIEW_ARTIFACTS_AND_EXECUTOR_REPLAY",
        "reportSha256": report_bundle(report)["reportSha256"], "replayReportSha256": report_bundle(replay)["reportSha256"],
        "sourceSha256": {key: sha((ROOT / path).read_bytes()) for key, path in CAMPAIGN_SOURCE_PATHS.items()},
        "privateObservationFileSha256": "a" * 64, "actualObservedRoundMessages": 2,
        "counts": report["counts"], "replayCounts": replay["counts"],
        "reservedNonWorkSlotsPerformed": 0, "modelCalls": 0, "externalEffects": 0,
        **{key: "PRIVATE-NARRATIVE-SENTINEL" for key in ("buildArtifactMeaning", "scope", "authority", "freshness", "completion")}}
    return proof, report, replay


class CampaignExportBoundaryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = asyncio.run(local_reports())

    def setUp(self):
        self.proof, self.report, self.replay = deepcopy(self.fixture)

    def project(self, **kwargs):
        return campaign_projection(self.proof, self.report, self.replay, allow_partial=True, **kwargs)

    def test_public_projection_omits_narratives_and_private_pin_preserves_hold(self):
        output = self.project()
        self.assertEqual(output["schema"], "atlas.native1728.synthesis-execution-projection/v1")
        self.assertEqual(output["campaignStatus"], "HOLD")
        self.assertEqual(output["counts"]["unresolvedChallenges"], 1)
        self.assertEqual(output["replayCounts"]["ordersComputed"], 0)
        self.assertEqual(self.report["challenges"][0]["status"], "DEFERRED")
        self.assertNotIn("PRIVATE-NARRATIVE-SENTINEL", json.dumps(output))
        self.assertNotIn("privateObservationFileSha256", output)
        output["counts"]["unresolvedChallenges"] = 0
        self.assertEqual(self.proof["counts"]["unresolvedChallenges"], 1)

    def test_unknown_proof_or_source_fields_reject_before_export(self):
        for where in ("top", "source"):
            with self.subTest(where=where):
                self.proof = deepcopy(self.fixture[0])
                target = self.proof if where == "top" else self.proof["sourceSha256"]
                target["privateMessageBody"] = "must not export"
                with self.assertRaises(ValueError):
                    self.project()

    def test_boolean_float_negative_and_invented_counters_reject(self):
        for value in (False, 0.0, -1, 9007199254740992, 1):
            with self.subTest(value=repr(value)):
                self.proof = deepcopy(self.fixture[0])
                self.proof["counts"]["canonicalTasksCompleted"] = value
                with self.assertRaises(ValueError):
                    self.project()

    def test_wrong_report_status_digest_or_observation_count_rejects(self):
        for key, value in (("campaignStatus", "PASS"), ("reportSha256", "0" * 64),
                           ("replayReportSha256", "0" * 64), ("actualObservedRoundMessages", 3),
                           ("actualObservedRoundMessages", True)):
            with self.subTest(field=key, value=value):
                self.proof = deepcopy(self.fixture[0])
                self.proof[key] = value
                with self.assertRaises(ValueError):
                    self.project()

    def test_declared_effects_and_unbounded_narratives_reject(self):
        for key, value in (("modelCalls", 1), ("externalEffects", 1),
                           ("reservedNonWorkSlotsPerformed", 1), ("modelCalls", False),
                           ("authority", "x" * 2049)):
            with self.subTest(field=key):
                self.proof = deepcopy(self.fixture[0])
                self.proof[key] = value
                with self.assertRaises(ValueError):
                    self.project()

    def test_partial_export_requires_the_explicit_option(self):
        with self.assertRaisesRegex(ValueError, "TWENTY_OBSERVED_ROUNDS_REQUIRED"):
            campaign_projection(self.proof, self.report, self.replay)
        self.assertEqual(self.project()["actualObservedRoundMessages"], 2)

    def test_changed_current_source_rejects_original_receipt(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for path in CAMPAIGN_SOURCE_PATHS.values():
                target = root / path
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes((ROOT / path).read_bytes())
            self.assertEqual(self.project(source_root=root)["campaignStatus"], "HOLD")
            target = root / CAMPAIGN_SOURCE_PATHS["runner"]
            target.write_bytes(target.read_bytes() + b"\n# changed\n")
            with self.assertRaisesRegex(ValueError, "CAMPAIGN_SOURCE_CHANGED"):
                self.project(source_root=root)


class ReplicationExportBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.engine = "c" * 64
        counts = {"acceptedCandidateChanges": 4, "epochs": 1729, "evaluatedTimelineYearUpdates": 5162766336,
            "holdoutEpochs": 432, "houses": 12, "nodes": 1728, "representedTimelineYears": 5162766336,
            "spheres": 144, "timelines": 1728, "trainEpochs": 1297, "yearsPerTimeline": 1728}
        self.first = {"reportSha256": "1" * 64, "seed": 1451728, "counts": counts,
            "auditReplayUpdates": 5975424, "elapsedNs": 100, "selectedCandidateId": "CFG.W01.M12.B12",
            "baselineCandidateId": "CFG.W01.M12.B12", "engineSourceSha256": self.engine}
        self.second = deepcopy(self.first)
        self.second.update(reportSha256="2" * 64, seed=1451748)

    def project(self):
        return replication_projection(self.first, self.second, engine_sha256=self.engine)

    def test_two_run_counts_conserve_and_output_detaches(self):
        output = self.project()
        self.assertEqual(output["totalDirectTransitions"], 10325532672)
        self.assertEqual(output["totalAdditionalAuditTransitions"], 11950848)
        self.assertEqual(output["distinctModeledCacheChunkBehaviorsPerRun"], 144)
        output["runs"][0]["counts"]["nodes"] = 999
        self.assertEqual(self.first["counts"]["nodes"], 1728)

    def test_repeated_seed_or_report_cannot_claim_a_second_run(self):
        for key in ("seed", "reportSha256"):
            with self.subTest(field=key):
                original = self.second[key]
                self.second[key] = self.first[key]
                with self.assertRaisesRegex(ValueError, "SIMULATION_DISTINCT_RUNS_REQUIRED"):
                    self.project()
                self.second[key] = original

    def test_changed_control_or_engine_cannot_retain_the_claim(self):
        for key, value in (("selectedCandidateId", "CFG.W02.M12.B12"),
                           ("baselineCandidateId", "CFG.W02.M12.B12"), ("engineSourceSha256", "d" * 64)):
            with self.subTest(field=key):
                original = self.second[key]
                self.second[key] = value
                with self.assertRaises(ValueError):
                    self.project()
                self.second[key] = original

    def test_malformed_or_nonconserved_counts_are_rejected(self):
        for target, key, value in ((self.second, "seed", True), (self.second, "auditReplayUpdates", 5975423),
            (self.second["counts"], "evaluatedTimelineYearUpdates", 5162766335),
            (self.second["counts"], "representedTimelineYears", 5162766335),
            (self.second["counts"], "holdoutEpochs", 431), (self.second["counts"], "nodes", 1728.0),
            (self.second["counts"], "acceptedCandidateChanges", 1298)):
            with self.subTest(field=key, value=value):
                original = target[key]
                target[key] = value
                with self.assertRaises(ValueError):
                    self.project()
                target[key] = original

    def test_unknown_projection_or_count_field_is_rejected(self):
        for target in (self.second, self.second["counts"]):
            target["privateBody"] = "not public evidence"
            with self.assertRaises(ValueError):
                self.project()
            del target["privateBody"]


if __name__ == "__main__":
    unittest.main()
