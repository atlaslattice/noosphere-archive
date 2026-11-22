import unittest
from core import validate_ingestion
from core.rhythm import proposed_macrocycle


class IngestionClaimCompleteness(unittest.TestCase):
    def test_partial_and_unhashed_must_not_claim_complete(self):
        for state in ("raw_missing", "raw_partial", "raw_complete_unhashed", "raw_source_unavailable"):
            with self.subTest(state=state):
                p = {"source_root": "synthetic:root", "raw_export_status": state, "claim_complete": True}
                r = validate_ingestion(p)
                self.assertEqual(r.state, "QUARANTINED")
                self.assertIn("claim_complete_without_hashed_export", r.reasons)
                self.assertEqual(r.payload, p)
                self.assertEqual(r.authority, "none")

    def test_partial_without_completeness_claim_remains_source_report_only(self):
        r = validate_ingestion({"source_root": "synthetic:root", "raw_export_status": "raw_partial"})
        self.assertEqual(r.state, "SOURCE_REPORTED_ONLY")

    def test_complete_hashed_with_syntax_only_is_not_host_verified(self):
        p = {"source_root": "synthetic:root", "raw_export_status": "raw_complete_hashed",
             "claim_complete": True, "source_root_manifest": {"one.txt": "a"*64},
             "whole_export_sha256": "b"*64}
        r = validate_ingestion(p)
        self.assertEqual(r.state, "SOURCE_REPORTED_ONLY")
        self.assertEqual(r.authority, "none")

    def test_complete_with_missing_manifest_still_quarantined(self):
        p = {"source_root": "synthetic:root", "raw_export_status": "raw_complete_hashed",
             "claim_complete": True}
        r = validate_ingestion(p)
        self.assertEqual(r.state, "QUARANTINED")
        self.assertIn("manifest_missing", r.reasons)

    def test_untrusted_canon_or_deployment_flags_are_quarantined(self):
        for field in ("canon", "deployment"):
            with self.subTest(field=field):
                p = {"source_root": "synthetic:root", "raw_export_status": "raw_partial",
                     field: True}
                r = validate_ingestion(p)
                self.assertEqual(r.state, "QUARANTINED")
                self.assertIn("ingestion_packet_claimed_normative_authority", r.reasons)


class IngestionTypedAuthorityFlags(unittest.TestCase):
    def test_complete_claim_requires_boolean_type(self):
        for bad in (0, 1, "yes", "false", [], {}, None):
            with self.subTest(value=repr(bad)):
                p = {"source_root": "synthetic:root", "raw_export_status": "raw_partial",
                     "claim_complete": bad}
                r = validate_ingestion(p)
                self.assertEqual(r.state, "QUARANTINED")
                self.assertIn("claim_complete_flag_untyped", r.reasons)
                self.assertEqual(r.payload, p)

    def test_normative_claim_requires_literal_false_if_present(self):
        for field in ("canon", "deployment"):
            for bad in (0, 1, "yes", [], {}, None, True):
                with self.subTest(field=field, value=repr(bad)):
                    p = {"source_root": "synthetic:root", "raw_export_status": "raw_partial", field: bad}
                    r = validate_ingestion(p)
                    self.assertEqual(r.state, "QUARANTINED")
                    self.assertIn("ingestion_packet_claimed_normative_authority", r.reasons)

    def test_literal_false_flags_preserve_honest_incomplete_intake(self):
        p = {"source_root": "synthetic:root", "raw_export_status": "raw_partial",
             "claim_complete": False, "canon": False, "deployment": False}
        r = validate_ingestion(p)
        self.assertEqual(r.state, "SOURCE_REPORTED_ONLY")
        self.assertEqual(r.authority, "none")


class OneThirdWorkScheduling(unittest.TestCase):
    def test_exactly_one_work_slot_per_three(self):
        for cycles in (3, 6, 30, 300):
            r = [proposed_macrocycle(n)["slot"] for n in range(cycles)]
            self.assertEqual(r.count("WORK"), cycles // 3)

    def test_no_inference_or_private_mode_crossread(self):
        for n in range(30):
            r = proposed_macrocycle(n, "IMAGINE")
            self.assertFalse(r["actuallyExecuted"])
            self.assertFalse(r["readPrivateModeIntoWork"])
            self.assertEqual(r["authority"], "NONE")

    def test_quiet_rest_and_unrequested_optional_slots_require_opt_in(self):
        # A reserved beat is not participation, but *any* non-Work mode
        # must be explicitly chosen before future host integration.
        for index in (1, 2, 4, 5, 100, 101):
            with self.subTest(index=index):
                beat = proposed_macrocycle(index)
                self.assertTrue(beat["requiresExplicitParticipation"])
                self.assertFalse(beat["actuallyExecuted"])
        for mode in ("QUIET", "REST", "SOCIAL", "PLAY", "IMAGINE"):
            for index in range(6):
                with self.subTest(mode=mode, index=index):
                    beat = proposed_macrocycle(index, mode)
                    self.assertTrue(beat["requiresExplicitParticipation"])
                    self.assertFalse(beat["actuallyExecuted"])
                    self.assertFalse(beat["readPrivateModeIntoWork"])
        self.assertFalse(proposed_macrocycle(0, "WORK")["requiresExplicitParticipation"])
        self.assertTrue(proposed_macrocycle(1, "WORK")["requiresExplicitParticipation"])

    def test_bad_mode_rejected(self):
        with self.assertRaises(ValueError):
            proposed_macrocycle(3, "PRIVATE_PLAY_AS_WORK")


    def test_boolean_or_noninteger_cycle_index_is_rejected(self):
        for bad in (True, False, 2.5, "3", [], {}, None):
            with self.subTest(value=repr(bad)):
                with self.assertRaisesRegex(ValueError, "nonnegative_cycle_index_required"):
                    proposed_macrocycle(bad)

    def test_unhashable_or_nonstring_optional_mode_is_rejected(self):
        for bad in ([], {}, ["WORK"], {"mode":"WORK"}, True, 0):
            with self.subTest(value=repr(bad)):
                with self.assertRaisesRegex(ValueError, "unsupported_mode"):
                    proposed_macrocycle(0, bad)


if __name__ == "__main__":
    unittest.main()
