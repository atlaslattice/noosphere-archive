import unittest
import json
from core.coordinate_resolver import CoordinateResolver, EARTH
from core.sentinel import review_packet
from core.preservation import PreservationLog
from core.ingestion import validate_ingestion
from core.canon_queue import CanonCandidateQueue
from core.orchestrator import Orchestrator
from core.rhythm import proposed_macrocycle


class TestCoordinate(unittest.TestCase):
    def setUp(self): self.r = CoordinateResolver("Ariadne-v0.7-source-reported", "example-digest-not-source-verified")

    def test_earth_routing_not_node(self):
        p = self.r.resolve_to_earth({"claim": "water depletion"})
        self.assertEqual(p["hsn"], EARTH)
        self.assertEqual(p["grounding"], "EARTH_ROUTING_ONLY")
        self.assertTrue(self.r.validate_grounding(p)["valid"])

    def test_whole_1728_syntax(self):
        addresses = set()
        for h in range(1,13):
            for s in range(1,13):
                for n in range(1,13):
                    p = self.r.wrap_as_coordinate_packet({"claim": "test"}, {"hsn":f"H{h:02}.S{s:02}.N{n:02}"})
                    self.assertTrue(self.r.validate_grounding(p)["valid"])
                    addresses.add(p["hsn"])
        self.assertEqual(len(addresses), 1728)
        self.assertNotIn(EARTH, addresses)

    def test_invalid_hsn_quarantined(self):
        for value in ("H13.S01.N01", "H00.S00.N01", "GF7.B01.M01.C01", "H01.S01", "H01.S13.N02"):
            p = self.r.wrap_as_coordinate_packet({"x":1},{"hsn":value})
            self.assertEqual(p["status"], "QUARANTINED_PENDING_REVIEW")

    def test_no_authority_passthrough(self):
        p = self.r.wrap_as_coordinate_packet({"authorized": True, "content": "owner"})
        self.assertEqual(p["authority"], "NONE")
        self.assertNotIn("hsn",p)

    def test_payload_tamper(self):
        p = self.r.wrap_as_coordinate_packet({"x":"truth"})
        p["payload"]["x"]="false"
        self.assertEqual(self.r.validate_grounding(p)["reason"], "payload_integrity_failure")

    def test_wrong_edition(self):
        p=self.r.wrap_as_coordinate_packet({"x":1})
        p["sourceEdition"]="different"
        self.assertFalse(self.r.validate_grounding(p)["valid"])

    def test_no_cross_registry_inference(self):
        p=self.r.wrap_as_coordinate_packet({"x":"resonance"},{"hsn":"H01.S01.N01"})
        self.assertNotIn("GF7",json.dumps(p))
        self.assertEqual(p["grounding"], "HISTORICAL_HSN_ADDRESS_ONLY")


class TestSentinel(unittest.TestCase):
    def setUp(self): self.p={"status":"CANDIDATE_UNREVIEWED","authority":"NONE","sourceEdition":"x","sourceDigest":"y","action":"propose"}

    def test_allow_route_only(self):
        r=review_packet(self.p)
        self.assertTrue(r["allowed"])
        self.assertEqual(r["authority"],"NONE")

    def test_unauthorized_actions(self):
        for action in ("deploy","ratify","canonize","delete","erase","publish_private","execute_external"):
            p={**self.p,"action":action}
            r=review_packet(p)
            self.assertFalse(r["allowed"])
            self.assertTrue(r["requires_human_root"])

    def test_wrong_authority(self):
        self.assertFalse(review_packet({**self.p,"authority":"ADMIN"})["allowed"])

    def test_source_required(self):
        for key in ("sourceDigest","sourceEdition"):
            p={**self.p,key:None}
            self.assertFalse(review_packet(p)["allowed"])

    def test_no_play_to_work(self):
        for mode in ("play","social","quiet","imagine","brain","palace"):
            self.assertFalse(review_packet({**self.p,"kind":mode,"purpose":"work"})["allowed"])

    def test_bad_input(self): self.assertFalse(review_packet(None)["allowed"])


class TestPreservation(unittest.TestCase):
    def setUp(self): self.log=PreservationLog()

    def test_destructive_always_retained(self):
        for verb in ("delete","erase","overwrite","truncate","purge","drop","destroy"):
            e=self.log.transition({"v":verb},{"deleted":True},verb,"issue:7")
            self.assertEqual(e["beforeDigest"],e["afterDigest"])
            self.assertEqual(self.log.read_snapshot(e["beforeDigest"])["v"],verb)

    def test_superseded_old_reachable(self):
        e=self.log.supersede({"status":"old"},{"status":"new"},"issue:7")
        self.assertEqual(self.log.read_snapshot(e["beforeDigest"])["status"],"old")
        self.assertEqual(self.log.read_snapshot(e["afterDigest"])["status"],"new")

    def test_quarantine_preserves_original(self):
        e=self.log.quarantine({"secret":"redacted_test_only"},"need source", "issue:7")
        self.assertIn("secret",self.log.read_snapshot(e["beforeDigest"]))
        self.assertEqual(len(self.log.events()),1)

    def test_mutating_caller_does_not_erase(self):
        a={"list":[1,2]}
        e=self.log.transition(a,{"list":[3]},"supersede","issue:7")
        a["list"].clear()
        self.assertEqual(self.log.read_snapshot(e["beforeDigest"])["list"],[1,2])
        ret=self.log.read_snapshot(e["afterDigest"])
        ret["list"].clear()
        self.assertEqual(self.log.read_snapshot(e["afterDigest"])["list"],[3])

    def test_no_source(self):
        with self.assertRaises(ValueError):self.log.transition(1,2,"supersede","")


class TestIngestion(unittest.TestCase):
    def setUp(self): self.valid={"source_ref":"repo:org/path","raw_export_status":"raw_complete_hashed","raw_sha256":"a"*64,"source_manifest":[{"path":"file.md","sha":"a"*64}],"claim_complete":True}

    def test_missing_raw_status(self):
        p=dict(self.valid);p.pop("raw_export_status")
        r=validate_ingestion(p)
        self.assertFalse(r["accepted"])
        self.assertEqual(r["status"],"QUARANTINED_INCOMPLETE")

    def test_hashed_complete_not_host_verified(self):
        r=validate_ingestion(self.valid)
        self.assertTrue(r["accepted"])
        self.assertEqual(r["completenessEvidence"],"SOURCE_HASH_PRESENT_NOT_EXTERNALLY_VERIFIED")
        self.assertEqual(r["authority"],"NONE")

    def test_no_false_complete(self):
        for status in ("raw_missing","raw_partial","raw_complete_unhashed","raw_source_unavailable"):
            p={**self.valid,"raw_export_status":status}
            self.assertFalse(validate_ingestion(p)["accepted"])

    def test_source_incomplete_can_be_received_without_completeness(self):
        for status in ("raw_missing","raw_partial","raw_source_unavailable"):
            p={"raw_export_status":status,"source_ref":"a","claim_complete":False}
            self.assertTrue(validate_ingestion(p)["accepted"])

    def test_hash_syntax(self):
        for h in ("A"*64,"abc","z"*64,None):
            p={**self.valid,"raw_sha256":h}
            self.assertFalse(validate_ingestion(p)["accepted"])

    def test_no_manifest(self):
        p={**self.valid,"source_manifest":[]}
        self.assertFalse(validate_ingestion(p)["accepted"])

    def test_no_auto_canon(self):
        self.assertFalse(validate_ingestion({**self.valid,"canon":True})["accepted"])


class TestCanonQueue(unittest.TestCase):
    def setUp(self):
        self.q=CanonCandidateQueue()
        self.a={"candidate_id":"candidate-001","artifact_source":"public:delta-ledger","why_useful":"traceability",
                "evidence_refs":["issue:4"],"risks":["unreviewed"],"contradictions":[],"review_required":["owner"]}

    def test_insert_never_ratifed(self):
        r=self.q.add(self.a)
        self.assertEqual(r["status"],"CANDIDATE_UNREVIEWED")
        self.assertFalse(r["canon"]);self.assertFalse(r["deployment"])

    def test_untrusted_promotion_fails(self):
        self.q.add(self.a)
        result=self.q.promote("candidate-001",token="forged_owner")
        self.assertEqual(result["status"],"HOLD_EXTERNAL_HUMAN_ROOT_GATE")

    def test_duplicate(self):
        self.q.add(self.a)
        with self.assertRaises(ValueError): self.q.add(self.a)

    def test_play_grant_not_inferred(self):
        with self.assertRaises(ValueError):self.q.add({**self.a,"sourceMode":"play","workIngestAuthorized":True})

    def test_untrusted_authority(self):
        for k,v in (("canon",True),("deployment",True),("authority","SYSTEM")):
            with self.assertRaises(ValueError):self.q.add({**self.a,k:v})


class TestOrchestrator(unittest.TestCase):
    def setUp(self): self.p={"status":"CANDIDATE_UNREVIEWED","authority":"NONE","sourceEdition":"v1","sourceDigest":"hash","action":"propose"}

    def test_no_sentinel_hold(self):
        self.assertEqual(Orchestrator().route(self.p)["status"],"HOLD_UNREVIEWED_NO_SENTINEL")

    def test_injected_reviewer_routes_not_runs(self):
        result=Orchestrator(sentinel=review_packet).route(self.p)
        self.assertEqual(result["status"],"SOURCE_ONLY_REVIEW_QUEUE")
        self.assertFalse(result["actualExecution"])

    def test_reviewer_blocks(self):
        result=Orchestrator(sentinel=review_packet).route({**self.p,"action":"deploy"})
        self.assertEqual(result["status"],"QUARANTINED_PENDING_REVIEW")

    def test_malicious_reviewer_cannot_grant(self):
        result=Orchestrator(sentinel=lambda p:{"allowed":True,"authority":"HOST"}).route(self.p)
        self.assertEqual(result["status"],"HOLD_INVALID_REVIEW")


class TestRhythm(unittest.TestCase):
    def test_one_third_work_in_300_slots(self):
        a=[proposed_macrocycle(n)["slot"] for n in range(300)]
        self.assertEqual(a.count("WORK"),100)
        self.assertEqual(a.count("QUIET_OPTIONAL"),100)
        self.assertEqual(a.count("SOCIAL_OR_IMAGINE_OPTIONAL"),100)

    def test_not_actual_runs(self):
        self.assertFalse(proposed_macrocycle(999_999_999)["actuallyExecuted"])

    def test_no_private_auto_ingest(self):
        for n in range(3):
            for mode in ("IMAGINE","PLAY","SOCIAL","REST"):
                r=proposed_macrocycle(n,mode)
                self.assertFalse(r["readPrivateModeIntoWork"])
                self.assertEqual(r["authority"],"NONE")


if __name__ == "__main__": unittest.main()
