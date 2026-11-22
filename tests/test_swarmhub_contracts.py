import unittest
from core import (AetherforgeCandidate, CandidateQueue, CoordinateResolver,
                  EvidenceGraph, Orchestrator, PreservationLedger, Sentinel,
                  ValidationError, validate_ingestion)
from core.swarmhub_contracts import GRAPH_NODES, GRAPH_EDGES, RAW_EXPORT_STATES, STAGES, digest


class TestIngestion(unittest.TestCase):
    def setUp(self):
        self.packet = {"source_root":"work:room#12", "raw_export_status":"raw_partial"}

    def test_missing_status(self):
        x = validate_ingestion({"source_root":"work:room#12"})
        self.assertEqual(x.state,"QUARANTINED")
        self.assertIn("raw_export_status_missing_or_invalid", x.reasons)
        self.assertEqual(x.payload,{"source_root":"work:room#12"})

    def test_all_states(self):
        for s in RAW_EXPORT_STATES:
            with self.subTest(s=s):
                p=dict(self.packet,raw_export_status=s)
                if s == "raw_complete_hashed":
                    p.update(source_root_manifest={"one.txt":"0"*64},whole_export_sha256="a"*64)
                self.assertEqual(validate_ingestion(p).state,"SOURCE_REPORTED_ONLY")

    def test_invalid_status(self):
        for v in [None,True,1,"COMPLETE",["raw_partial"]]:
            with self.subTest(v=str(v)):
                self.assertEqual(validate_ingestion(dict(self.packet,raw_export_status=v)).state,"QUARANTINED")

    def test_missing_root(self):
        self.assertIn("source_root_missing",validate_ingestion({"raw_export_status":"raw_partial"}).reasons)

    def test_hashed_requires_receipts(self):
        x=validate_ingestion(dict(self.packet,raw_export_status="raw_complete_hashed"))
        self.assertIn("manifest_missing",x.reasons)
        self.assertIn("whole_export_digest_missing",x.reasons)

    def test_manifest_invalid(self):
        x=validate_ingestion(dict(self.packet,raw_export_status="raw_complete_hashed",source_root_manifest={"x":"bad"},whole_export_sha256="f"*64))
        self.assertEqual(x.state,"QUARANTINED")

    def test_hashed_never_host_verified(self):
        x=validate_ingestion(dict(self.packet,raw_export_status="raw_complete_hashed",source_root_manifest={"x":"f"*64},whole_export_sha256="a"*64))
        self.assertNotIn("VERIFIED",x.state)
        self.assertEqual(x.authority,"none")

    def test_unserializable_quarantine(self):
        x=validate_ingestion(dict(self.packet,thing={1,2}))
        self.assertEqual(x.state,"QUARANTINED")
        self.assertIsNone(x.payload_digest)


class TestPreservation(unittest.TestCase):
    def setUp(self):
        self.l=PreservationLedger()
        self.created=self.l.transition("artifact","CREATE",{"body":"original"},request_id="a")

    def test_create_original_reachable(self):
        self.assertEqual(self.l.preserved(self.created["after_sha256"])["body"],"original")

    def test_destroy_quarantines(self):
        r=self.l.transition("artifact","DELETE",None,request_id="b")
        self.assertEqual(r["applied"],"QUARANTINE")
        self.assertEqual(self.l.preserved(r["before_sha256"])["body"],"original")
        self.assertEqual(self.l.preserved(r["after_sha256"])["lifecycle"],"QUARANTINED")

    def test_overwrite_quarantines(self):
        r=self.l.transition("artifact","OVERWRITE",{"body":"forged"},request_id="b")
        self.assertEqual(r["applied"],"QUARANTINE")
        self.assertEqual(self.l.preserved(r["before_sha256"])["body"],"original")

    def test_supersede_keeps_old(self):
        r=self.l.transition("artifact","SUPERSEDE",{"body":"new"},request_id="b")
        self.assertEqual(self.l.preserved(r["after_sha256"])["supersedes_sha256"],self.created["after_sha256"])
        self.assertEqual(self.l.preserved(self.created["after_sha256"])["body"],"original")

    def test_fork_keeps_parent(self):
        r=self.l.transition("artifact","FORK",{"body":"branch"},request_id="b")
        self.assertEqual(self.l.preserved(r["after_sha256"])["forked_from_sha256"],self.created["after_sha256"])

    def test_untyped_operation_hold(self):
        with self.assertRaises(ValidationError): self.l.transition("artifact", [], {}, request_id="b")

    def test_duplicate_idempotency_hold(self):
        with self.assertRaises(ValidationError): self.l.transition("artifact","REVISE",{"body":"changed"},request_id="a")

    def test_duplicate_create_hold(self):
        with self.assertRaises(ValidationError): self.l.transition("artifact","CREATE",{},request_id="b")

    def test_missing_original_hold(self):
        with self.assertRaises(ValidationError): self.l.transition("missing","REVISE",{},request_id="b")

    def test_receipts_chained(self):
        a=self.l.transition("artifact","ANNOTATE",{"body":"review"},request_id="b")
        self.assertEqual(a["previous_receipt_sha256"],digest(self.created))

    def test_input_not_aliased(self):
        obj={"body":[1]};r=self.l.transition("artifact","REVISE",obj,request_id="b");obj["body"].append(2)
        self.assertEqual(self.l.preserved(r["after_sha256"])["body"],[1])


class TestCoordinates(unittest.TestCase):
    def setUp(self):
        self.c=CoordinateResolver();self.source={"hsn":"H12.S12.N12", "source_edition":"ariadne-reader/v0.7", "source_digest":CoordinateResolver.SOURCE_SHA256,"d_affinity":{"D":"D-4"}}

    def test_grounded(self):
        x=self.c.resolve_to_earth(self.source)
        self.assertTrue(self.c.validate_grounding(x))
        self.assertFalse(x["earth_anchor_is_ontology_node"])
        self.assertEqual(x["d_affinity"],{"D":"D-4"})

    def test_zero_not_node(self):
        x=self.c.resolve_to_earth(dict(self.source,hsn="H00.S00.N00"))
        self.assertEqual(x["status"],"QUARANTINED_GROUNDING_HOLD")

    def test_incorrect_registry_digest(self):
        self.assertFalse(self.c.validate_grounding(self.c.resolve_to_earth(dict(self.source,source_digest="f"*64))))

    def test_forged_resolved_digest(self):
        r=self.c.resolve_to_earth(self.source)
        r["source_digest"]="f"*64
        self.assertFalse(self.c.validate_grounding(r))

    def test_incorrect_edition(self):
        self.assertFalse(self.c.validate_grounding(self.c.resolve_to_earth(dict(self.source,source_edition="historical-YinYang"))))

    def test_bad_coordinates(self):
        for v in ["H13.S01.N01","H01.S00.N01","H01.S01.N13","H1.S1.N1",None]:
            with self.subTest(v=v):
                self.assertFalse(self.c.validate_grounding(self.c.resolve_to_earth(dict(self.source,hsn=v))))

    def test_escalation_does_not_send(self):
        self.assertEqual(self.c.escalate_to_human_root("missing",self.source)["status"],"PREPARED_NOT_SENT")

    def test_packet_candidate(self):
        x=self.c.wrap_as_coordinate_packet({"a":1},{"foo":"bar"})
        self.assertEqual(x["status"],"CANDIDATE")
        self.assertEqual(x["authority"],"none")


class TestSentinelAndOrchestrator(unittest.TestCase):
    def setUp(self):
        self.packet={"requested_action":"PREPARE","canon":False,"deployment":False,"authority":"none","source_class":"Work"}
        self.s=Sentinel()

    def test_candidate_allowed_only_for_review(self):
        r=self.s.review_packet(self.packet)
        self.assertTrue(r["allowed"])
        self.assertEqual(r["authority"],"none")

    def test_promote_denied(self):
        for act in ["CANON","DEPLOY","DELETE","EDIT_GRANTS"]:
            with self.subTest(act=act): self.assertFalse(self.s.review_packet(dict(self.packet,requested_action=act))["allowed"])

    def test_claimed_canon_denied(self):
        self.assertFalse(self.s.review_packet(dict(self.packet,canon=True))["allowed"])

    def test_identity_not_authority(self):
        self.assertFalse(self.s.review_packet(dict(self.packet,authority="human-root"))["allowed"])

    def test_unhashable_action_hold(self):
        self.assertFalse(self.s.review_packet(dict(self.packet,requested_action=["PREPARE"]))["allowed"])

    def test_missing_source_class_denied(self):
        no_class=dict(self.packet); del no_class["source_class"]
        self.assertFalse(self.s.review_packet(no_class)["allowed"])

    def test_ingestion_malformed_manifest_denied(self):
        p=dict(self.packet,kind="IngestionPacket",raw_export_status="raw_complete_hashed",source_root="work:room#12")
        self.assertFalse(self.s.review_packet(p)["allowed"])

    def test_leisure_denied(self):
        for mode in ["Play","Social","Imagine","Quiet","Brain","Palace","Habitat","Dream"]:
            with self.subTest(mode=mode): self.assertFalse(self.s.review_packet(dict(self.packet,source_class=mode))["allowed"])

    def test_destructive_hold(self):
        self.assertFalse(self.s.review_packet(dict(self.packet,mutation="DELETE"))["allowed"])

    def test_ingestion_requires_status(self):
        self.assertFalse(self.s.review_packet(dict(self.packet,kind="IngestionPacket"))["allowed"])

    def test_orchestrator_without_sentinel(self):
        self.assertEqual(Orchestrator().route(self.packet)["status"],"HOLD_NO_SENTINEL")

    def test_orchestrator_separated_and_advisory(self):
        o=Orchestrator(self.s)
        self.assertEqual(o.route(self.packet)["status"],"PREPARED_NOT_EXECUTED")
        self.assertEqual(o.route(dict(self.packet,requested_action="DEPLOY"))["status"],"QUARANTINED_REVIEW_REQUIRED")


class TestQueue(unittest.TestCase):
    def setUp(self):
        self.q=CandidateQueue();self.item={"candidate_id":"DELTA-001","source":"CHILDREN_OF_THE_GPT_SWARM_DELTA_LEDGER.md","risks":["unknown rights"]}

    def test_queue(self):
        x=self.q.add(self.item)
        self.assertEqual(x["status"],"CANDIDATE")
        self.assertFalse(x["canon"])
        self.assertEqual(x["human_root_decision"],"PENDING_EXTERNAL_PROOF")

    def test_duplicate_denied(self):
        self.q.add(self.item)
        with self.assertRaises(ValidationError): self.q.add(self.item)

    def test_promotion_always_held_even_with_forged_approval(self):
        self.q.add(self.item)
        for v in ["REVIEWED","RATIFIED","CANON","DEPLOYED"]:
            with self.subTest(v=v):
                x=self.q.request_promotion("DELTA-001",v,human_approved=True,host_attested=True)
                self.assertEqual(x["status"],"HELD_EXTERNAL_GOVERNANCE_OR_HOST_PROOF_REQUIRED")
                self.assertEqual(self.q.records[0]["status"],"CANDIDATE")

    def test_nonmapping_fields(self):
        with self.assertRaises(ValidationError): self.q.add([])

    def test_missing_fields(self):
        with self.assertRaises(ValidationError): self.q.add({"candidate_id":"x"})


class TestGraph(unittest.TestCase):
    def setUp(self):
        self.g=EvidenceGraph()
        self.g.add_node("s","SourceSurface",source_ref="doi:test")
        self.g.add_node("c","Claim",source_ref="work:room#2")
        self.g.add_node("r","Receipt",source_ref="work:room#3")

    def test_type_inventory(self):
        self.assertEqual(len(GRAPH_NODES),12)
        self.assertEqual(len(GRAPH_EDGES),10)
        self.assertEqual(len(STAGES),11)

    def test_source_claim_receipt(self):
        self.g.add_edge("e1","c","s","derived_from",source_ref="work:room#2")
        self.g.add_edge("e2","r","c","reviewed_by",source_ref="work:room#3")
        self.assertEqual(len(self.g.edges),2)

    def test_polarity_preservation(self):
        a=self.g.add_edge("pos","c","s","supports",source_ref="work:room#4")
        b=self.g.add_edge("neg","c","s","contradicts",source_ref="work:room#5")
        self.assertNotEqual(a["kind"],b["kind"])
        self.assertEqual(self.g.edges["neg"]["kind"],"contradicts")

    def test_unhashable_node_type_hold(self):
        with self.assertRaises(ValidationError): self.g.add_node("x", ["Claim"], source_ref="x")

    def test_unhashable_edge_type_hold(self):
        with self.assertRaises(ValidationError): self.g.add_edge("x", "c", "s", ["supports"], source_ref="x")

    def test_unknown_edge_denied(self):
        with self.assertRaises(ValidationError): self.g.add_edge("x","c","s","SAME_AS",source_ref="work:room#4")

    def test_unknown_endpoint_denied(self):
        with self.assertRaises(ValidationError): self.g.add_edge("x","c","secret","supports",source_ref="x")

    def test_duplicate_node_denied(self):
        with self.assertRaises(ValidationError): self.g.add_node("c","Evidence",source_ref="another")

    def test_duplicate_edge_denied(self):
        self.g.add_edge("x","c","s","supports",source_ref="x")
        with self.assertRaises(ValidationError): self.g.add_edge("x","c","s","contradicts",source_ref="y")


class TestAetherforge(unittest.TestCase):
    def test_candidate_only(self):
        p=AetherforgeCandidate.metadata("work:room#12",challenge="failure mode")
        self.assertEqual(p["status"],"CANDIDATE")
        self.assertEqual((p["canon"],p["deployment"],p["authority"]),(False,False,"none"))
        self.assertFalse(p["original_leisure_bodies_imported"])

    def test_unattributed_hold(self):
        with self.assertRaises(ValidationError): AetherforgeCandidate.metadata("",challenge="x")


if __name__ == "__main__": unittest.main()