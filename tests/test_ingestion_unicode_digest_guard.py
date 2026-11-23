"""Synthetic-only Unicode digest boundary checks; no source or private-mode reads."""
import copy
import unittest

from core import Sentinel, validate_ingestion


BASE = {"raw_export_status": "raw_partial", "source_root": "synthetic:fixture"}


class IngestionUnicodeDigestTests(unittest.TestCase):
    def test_unpaired_surrogates_quarantine_and_preserve_original(self):
        for scalar in (0xD800, 0xDBFF, 0xDC00, 0xDFFF):
            with self.subTest(code_point=hex(scalar)):
                packet = dict(BASE, source_root="synthetic:" + chr(scalar))
                original = copy.deepcopy(packet)
                verdict = validate_ingestion(packet)
                self.assertEqual(verdict.state, "QUARANTINED")
                self.assertIn("payload_not_json_serializable", verdict.reasons)
                self.assertIsNone(verdict.payload_digest)
                self.assertEqual(verdict.payload, original)
                self.assertEqual(packet, original)
                self.assertEqual(verdict.authority, "none")

    def test_sentinel_holds_malformed_unicode_without_throwing(self):
        packet = dict(BASE, kind="IngestionPacket", source_class="Work",
                      canon=False, deployment=False, authority="none",
                      requested_action="PREPARE", source_root="synthetic:" + chr(0xD800))
        review = Sentinel().review_packet(packet)
        self.assertFalse(review["allowed"])
        self.assertIn("ingestion_validation_failed", review["findings"])
        self.assertEqual(review["authority"], "none")

    def test_valid_nonascii_source_root_retains_reported_status(self):
        packet = dict(BASE, source_root="synthetic:hé漢")
        verdict = validate_ingestion(packet)
        self.assertEqual(verdict.state, "SOURCE_REPORTED_ONLY")
        self.assertIsInstance(verdict.payload_digest, str)
        self.assertEqual(len(verdict.payload_digest), 64)
        self.assertEqual(verdict.authority, "none")


if __name__ == "__main__":
    unittest.main()
