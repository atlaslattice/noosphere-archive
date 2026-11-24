"""Read-error receipts must not echo synthetic input filenames or byte details."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class ContinuityCLIReadErrorTests(unittest.TestCase):
    def run_cli(self, *args):
        optimize = ["-O"] if sys.flags.optimize else []
        return subprocess.run(
            [sys.executable, *optimize, "-m", "core.digital_continuity", *args],
            cwd=ROOT, capture_output=True, text=True, timeout=10,
        )

    def assert_read_hold(self, result, path):
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertEqual(result.stderr, "")
        self.assertEqual(json.loads(result.stdout), {"status": "HOLD", "reason": "INPUT_READ_FAILED"})
        self.assertNotIn(str(path), result.stdout)
        self.assertNotIn(path.name, result.stdout)
        self.assertNotIn("0xff", result.stdout)

    def test_missing_bundle_filename_is_not_returned(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "synthetic_missing_bundle_8bf9.json"
            result = self.run_cli("--bundle", str(path))
        self.assert_read_hold(result, path)

    def test_missing_contract_filename_is_not_returned(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "synthetic_missing_contract_a719.json"
            result = self.run_cli("--contract", str(path))
        self.assert_read_hold(result, path)

    def test_invalid_bundle_utf8_details_are_not_returned(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "synthetic_invalid_bundle_utf8.json"
            path.write_bytes(bytes([255]))
            result = self.run_cli("--bundle", str(path))
        self.assert_read_hold(result, path)

    def test_invalid_contract_utf8_details_are_not_returned(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "synthetic_invalid_contract_utf8.json"
            path.write_bytes(bytes([255]))
            result = self.run_cli("--contract", str(path))
        self.assert_read_hold(result, path)

    def test_valid_synthetic_preparation_remains_inert(self):
        result = self.run_cli()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, "")
        receipt = json.loads(result.stdout)
        self.assertEqual(receipt["status"], "PREPARED_NOT_EXECUTED")
        self.assertEqual(receipt["model_calls"], 0)
        self.assertEqual(receipt["host_authorization"], "NOT_ESTABLISHED")
        self.assertFalse(receipt["source_bodies_returned"])

    def test_semantic_hold_retains_existing_reason(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "synthetic_invalid_shape.json"
            path.write_text("{}", encoding="utf-8")
            result = self.run_cli("--bundle", str(path))
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertEqual(result.stderr, "")
        self.assertEqual(json.loads(result.stdout), {
            "status": "HOLD", "reason": "ContinuityHold: BUNDLE_FIELDS_INVALID",
        })


if __name__ == "__main__":
    unittest.main()
