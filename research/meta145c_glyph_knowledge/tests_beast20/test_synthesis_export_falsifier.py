"""Only the executed, source-bound falsifier evidence may reach host exports."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from benchmarks.export_synthesis20_hosts import (
    FALSIFIER_RECEIPT_SHA256, FALSIFIER_SOURCE_PATHS, ROOT, validate_falsifier,
)


RECEIPT = ROOT / "benchmarks/synthesis20/PROVENANCE_FALSIFIER_RESULTS.json"


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")


def reseal(value):
    value["reportSha256"] = hashlib.sha256(canonical({key: item for key, item in value.items()
                                                    if key != "reportSha256"})).hexdigest()
    return json.dumps(value, indent=2, sort_keys=True).encode("ascii") + b"\n"


class SynthesisExportFalsifierTests(unittest.TestCase):
    def setUp(self):
        self.raw = RECEIPT.read_bytes()
        self.receipt = json.loads(self.raw)

    def test_actual_retained_receipt_exports_exact_counts_losses_and_limits(self):
        validated = validate_falsifier(self.raw)
        self.assertEqual(hashlib.sha256(self.raw).hexdigest(), FALSIFIER_RECEIPT_SHA256)
        self.assertEqual(validated, self.receipt)
        self.assertEqual(validated["counts"]["registeredModuleCalls"], 100)
        self.assertEqual([validated["summary"][name]["losses"] for name in
                          ("VALUES_ONLY_ALL_DOMAINS", "WHOLE_PACKET", "FULL_KEYED_PROVENANCE")], [3, 4, 0])
        self.assertIn("not a generalization estimate", " ".join(validated["limitations"]))

    def test_self_resealed_invented_counts_cannot_replace_executed_evidence(self):
        altered = deepcopy(self.receipt)
        altered["counts"]["registeredModuleCalls"] = 999999
        with self.assertRaisesRegex(ValueError, "FALSIFIER_RECORDED_RECEIPT_CHANGED"):
            validate_falsifier(reseal(altered))

    def test_self_resealed_losses_source_or_unknown_fields_are_rejected(self):
        for kind in ("loss", "source", "oracle", "invocation", "unknown"):
            with self.subTest(kind=kind):
                altered = deepcopy(self.receipt)
                if kind == "loss":
                    altered["summary"]["VALUES_ONLY_ALL_DOMAINS"].update(losses=0, matchesBoth=20)
                elif kind == "source":
                    altered["implementation"]["beforeSha256"]["runner"] = "0" * 64
                elif kind == "oracle":
                    altered["workload"][8]["expected"]["identityRelation"] = "UNCHANGED"
                elif kind == "invocation":
                    altered["execution"]["registeredModuleInvocations"].pop()
                else:
                    altered["authenticatedPeerQuality"] = True
                with self.assertRaisesRegex(ValueError, "FALSIFIER_RECORDED_RECEIPT_CHANGED"):
                    validate_falsifier(reseal(altered))

    def test_current_source_mutation_rejects_an_otherwise_genuine_receipt(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for key, path in FALSIFIER_SOURCE_PATHS.items():
                target = root / path
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes((ROOT / path).read_bytes())
            self.assertEqual(validate_falsifier(self.raw, source_root=root), self.receipt)
            for key, path in FALSIFIER_SOURCE_PATHS.items():
                with self.subTest(source=key):
                    target = root / path
                    original = target.read_bytes()
                    target.write_bytes(original + b"\n# changed after evidence\n")
                    with self.assertRaisesRegex(ValueError, "FALSIFIER_SOURCE_CHANGED"):
                        validate_falsifier(self.raw, source_root=root)
                    target.write_bytes(original)

    def test_missing_source_has_a_bounded_nonprivate_error(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError, "^FALSIFIER_SOURCE_UNAVAILABLE$"):
                validate_falsifier(self.raw, source_root=Path(directory))

    def test_bytes_and_size_boundary_rejects_custom_or_overlong_input(self):
        class CustomBytes(bytes):
            pass
        for raw in (None, bytearray(self.raw), CustomBytes(self.raw), b"x" * (1024 * 1024 + 1)):
            with self.subTest(kind=type(raw).__name__):
                with self.assertRaisesRegex(ValueError, "FALSIFIER_RECEIPT_BYTES_INVALID"):
                    validate_falsifier(raw)

    def test_returned_evidence_is_detached_and_does_not_update_retained_receipt(self):
        output = validate_falsifier(self.raw)
        output["summary"]["VALUES_ONLY_ALL_DOMAINS"]["losses"] = 0
        self.assertEqual(validate_falsifier(self.raw)["summary"]["VALUES_ONLY_ALL_DOMAINS"]["losses"], 3)
        self.assertEqual(RECEIPT.read_bytes(), self.raw)


if __name__ == "__main__":
    unittest.main()
