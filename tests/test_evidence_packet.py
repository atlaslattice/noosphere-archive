"""Non-destructive synthetic acceptance tests for issues #8, #11 and #12."""
import copy
import json
import tempfile
import unittest
from pathlib import Path

from scripts.validate_evidence_packet import inspect_packet, validate_file

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "examples" / "noosphere_evidence_chain_v0_1.json"


def encode(obj):
    return (json.dumps(obj, separators=(",", ":")) + "\n").encode("utf-8")


class EvidencePacketTests(unittest.TestCase):
    def setUp(self):
        self.good = json.loads(EXAMPLE.read_text(encoding="utf-8"))

    def verdict(self, changed):
        return inspect_packet(encode(changed))

    def test_synthetic_chain_is_structural_candidate_only(self):
        v = validate_file(EXAMPLE)
        self.assertEqual(v["disposition"], "CANDIDATE_ONLY")
        self.assertFalse(v["can_promote"])
        self.assertFalse(v["can_claim_completeness"])
        self.assertFalse(v["source_mode_verified"])

    def test_missing_raw_export_status_holds(self):
        self.good.pop("raw_export_status")
        self.assertEqual(self.verdict(self.good)["disposition"], "HOLD")

    def test_false_completeness_holds(self):
        self.good["completeness_claim"] = True
        v = self.verdict(self.good)
        self.assertEqual(v["disposition"], "HOLD")

    def test_hashed_claim_requires_manifest_digest_and_export_receipt(self):
        self.good["raw_export_status"] = "raw_complete_hashed"
        self.good["completeness_claim"] = True
        self.assertEqual(self.verdict(self.good)["disposition"], "HOLD")
        self.good["source_roots"][0]["sha256"] = "0" * 64
        self.good["export_receipt_sha256"] = "1" * 64
        v = self.verdict(self.good)
        self.assertEqual(v["disposition"], "CANDIDATE_ONLY")
        self.assertFalse(v["can_claim_completeness"])  # no actual preimage checked

    def test_self_declared_canon_and_deployment_are_rejected(self):
        for field in ("canon", "deployed"):
            candidate = copy.deepcopy(self.good)
            candidate["lifecycle"][field] = True
            self.assertEqual(self.verdict(candidate)["disposition"], "HOLD")

    def test_non_work_modes_rejected(self):
        for source_mode in ("play", "social", "imagine", "dream", "quiet"):
            candidate = copy.deepcopy(self.good)
            candidate["source_mode"] = source_mode
            self.assertEqual(self.verdict(candidate)["disposition"], "HOLD")

    def test_invalid_graph_references_and_duplicate_ids_hold(self):
        candidate = copy.deepcopy(self.good)
        candidate["edges"][0]["to"] = "missing-node"
        self.assertEqual(self.verdict(candidate)["disposition"], "HOLD")
        candidate = copy.deepcopy(self.good)
        candidate["nodes"].append(copy.deepcopy(candidate["nodes"][0]))
        self.assertEqual(self.verdict(candidate)["disposition"], "HOLD")

    def test_derived_from_is_type_checked_in_both_directions(self):
        # Valid source->manifest->artifact ancestry remains reviewable.
        self.assertEqual(self.verdict(self.good)["disposition"], "CANDIDATE_ONLY")
        for source_id, target_id in (("g1", "s1"), ("m1", "g1"), ("r1", "r1")):
            candidate = copy.deepcopy(self.good)
            candidate["edges"][0]["from"] = source_id
            candidate["edges"][0]["to"] = target_id
            verdict = self.verdict(candidate)
            self.assertEqual(verdict["disposition"], "HOLD", (source_id, target_id))
            self.assertTrue(any("invalid node types for derived_from" in e for e in verdict["errors"]))

    def test_incorrect_relation_types_hold(self):
        candidate = copy.deepcopy(self.good)
        candidate["edges"][3]["from"] = "s1"  # supports must originate in Evidence
        self.assertEqual(self.verdict(candidate)["disposition"], "HOLD")

    def test_candidate_cannot_self_declare_ratified_stage(self):
        candidate = copy.deepcopy(self.good)
        candidate["lifecycle"]["stage"] = "RATIFIED"
        self.assertEqual(self.verdict(candidate)["disposition"], "HOLD")

    def test_malformed_values_fail_closed_without_crashing(self):
        candidate = copy.deepcopy(self.good)
        candidate["nodes"][0]["type"] = {"unexpected": "object"}
        candidate["edges"][0]["from"] = ["not-a-string"]
        candidate["edges"][0]["type"] = ["not-a-string"]
        self.assertEqual(self.verdict(candidate)["disposition"], "HOLD")

    def test_claim_without_source_ref_holds(self):
        candidate = copy.deepcopy(self.good)
        candidate["nodes"][3].pop("source_ref")
        self.assertEqual(self.verdict(candidate)["disposition"], "HOLD")

    def test_duplicate_json_keys_hold(self):
        raw = b'{"source_mode":"public","source_mode":"play"}'
        self.assertEqual(inspect_packet(raw)["disposition"], "HOLD")
        self.assertIn("Duplicate JSON key", inspect_packet(raw)["errors"][0])

    def test_quarantine_preserves_exact_invalid_bytes_and_writes_review_receipt(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            input_path = root / "input.json"
            quarantine = root / "private-review"
            bad = copy.deepcopy(self.good)
            bad.pop("raw_export_status")
            original = encode(bad)
            input_path.write_bytes(original)
            v = validate_file(input_path, quarantine)
            self.assertEqual(v["disposition"], "HOLD")
            self.assertEqual(input_path.read_bytes(), original)
            copied = Path(v["quarantine"]["source"])
            self.assertEqual(copied.read_bytes(), original)
            receipt = json.loads(Path(v["quarantine"]["receipt"]).read_text())
            self.assertTrue(receipt["original_preserved"])
            self.assertTrue(receipt["review_required"])
            self.assertFalse(receipt["canon"])
            self.assertFalse(receipt["deployed"])

    def test_quarantine_repeat_is_idempotent_without_rewriting_receipt(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            path = root / "bad.json"
            bad = copy.deepcopy(self.good)
            bad.pop("raw_export_status")
            path.write_bytes(encode(bad))
            first = validate_file(path, root / "hold")
            receipt = Path(first["quarantine"]["receipt"])
            old_bytes = receipt.read_bytes()
            old_mtime = receipt.stat().st_mtime_ns
            again = validate_file(path, root / "hold")
            self.assertEqual(again["disposition"], "HOLD")
            self.assertEqual(receipt.read_bytes(), old_bytes)
            self.assertEqual(receipt.stat().st_mtime_ns, old_mtime)

    def test_quarantine_receipt_conflict_preserves_existing_objection(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            path = root / "bad.json"
            bad = copy.deepcopy(self.good)
            bad.pop("raw_export_status")
            original = encode(bad)
            path.write_bytes(original)
            first = validate_file(path, root / "hold")
            receipt = Path(first["quarantine"]["receipt"])
            old = json.loads(receipt.read_text())
            old["review_objection"] = "retained objection, not erased"
            modified = encode(old)
            receipt.write_bytes(modified)
            with self.assertRaisesRegex(RuntimeError, "existing quarantine record differs"):
                validate_file(path, root / "hold")
            self.assertEqual(receipt.read_bytes(), modified)
            self.assertEqual(Path(first["quarantine"]["source"]).read_bytes(), original)

    def test_existing_quarantine_source_conflict_holds_original(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            path = root / "bad.json"
            bad = copy.deepcopy(self.good)
            bad.pop("raw_export_status")
            path.write_bytes(encode(bad))
            first = validate_file(path, root / "hold")
            preserved = Path(first["quarantine"]["source"])
            preserved.write_bytes(b"prior reviewer source")
            with self.assertRaisesRegex(RuntimeError, "existing quarantine record differs"):
                validate_file(path, root / "hold")
            self.assertEqual(preserved.read_bytes(), b"prior reviewer source")

    def test_quarantine_symlink_record_does_not_touch_target(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            path = root / "bad.json"
            bad = copy.deepcopy(self.good)
            bad.pop("raw_export_status")
            path.write_bytes(encode(bad))
            first = validate_file(path, root / "hold")
            receipt = Path(first["quarantine"]["receipt"])
            external = root / "valuable.txt"
            external.write_bytes(b"valuable preserved history")
            receipt.unlink()
            receipt.symlink_to(external)
            with self.assertRaisesRegex(RuntimeError, "refuse symlink"):
                validate_file(path, root / "hold")
            self.assertEqual(external.read_bytes(), b"valuable preserved history")

    def test_quarantine_symlink_dir_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            path = root / "bad.json"
            bad = copy.deepcopy(self.good)
            bad.pop("raw_export_status")
            path.write_bytes(encode(bad))
            other = root / "other"
            other.mkdir()
            linked = root / "linked"
            linked.symlink_to(other, target_is_directory=True)
            with self.assertRaisesRegex(RuntimeError, "refuse symlink quarantine directory"):
                validate_file(path, linked)
            self.assertEqual(list(other.iterdir()), [])

    def test_no_implicit_write_on_rejection(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "bad.json"
            path.write_text("invalid", encoding="utf-8")
            self.assertEqual(validate_file(path)["disposition"], "HOLD")
            self.assertEqual([x.name for x in Path(d).iterdir()], ["bad.json"])


if __name__ == "__main__":
    unittest.main()
