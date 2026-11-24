"""No GitHub calls, secrets, or writable external state."""
import json
import contextlib
import io
from unittest.mock import patch
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from registry.public_registry import RegistryError, validate_catalog, load_catalog_text, _read_bounded_catalog_text, main
from registry.strict_inventory_json import (
    InventoryJSONError, MAX_INVENTORY_BYTES, strict_inventory_loads,
)


class StrictPublicRegistryInput(unittest.TestCase):
    def test_nontext_snapshot_date_is_rejected_as_registry_hold(self):
        src = Path(__file__).resolve().parents[1] / "registry" / "public_repo_inventory_2026-11-22.json"
        baseline = json.loads(src.read_text(encoding="utf-8"))
        for invalid in (None, True, 20261122, [], {}):
            with self.subTest(value=repr(invalid)):
                candidate = dict(baseline, observed_date_utc=invalid)
                with self.assertRaisesRegex(RegistryError, "MISSING_SNAPSHOT_PASSPORT"):
                    validate_catalog(candidate)

    def test_cli_size_gate_before_complete_file_read(self):
        # The prior CLI used Path.read_text(), allocating the entire supplied file.
        with tempfile.TemporaryDirectory() as tmp:
            candidate = Path(tmp) / "public-synthetic-oversize.json"
            candidate.write_bytes(b" " * (MAX_INVENTORY_BYTES + 1))
            with self.assertRaisesRegex(RegistryError, "^CATALOG_TOO_LARGE$"):
                _read_bounded_catalog_text(candidate)
            out = io.StringIO()
            # If the CLI regresses to its prior unbounded Path.read_text,
            # this assertion fails even when the downstream parser later HOLDS.
            with patch.object(Path, "read_text", side_effect=AssertionError("UNBOUNDED_READ")), contextlib.redirect_stdout(out):
                result = main(["--input", str(candidate)])
            self.assertEqual(result, 2)
            self.assertEqual(json.loads(out.getvalue()),
                             {"status": "HOLD", "reason": "RegistryError: CATALOG_TOO_LARGE"})

    def test_exact_byte_limit_has_no_false_size_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            candidate = Path(tmp) / "public-exact-limit.json"
            candidate.write_bytes(b" " * MAX_INVENTORY_BYTES)
            self.assertEqual(len(_read_bounded_catalog_text(candidate)), MAX_INVENTORY_BYTES)

    def test_multibyte_utf8_byte_limit_not_character_limit(self):
        with tempfile.TemporaryDirectory() as tmp:
            candidate = Path(tmp) / "public-multibyte-limit.json"
            candidate.write_bytes("é".encode("utf-8") * (MAX_INVENTORY_BYTES // 2 + 1))
            with self.assertRaisesRegex(RegistryError, "^CATALOG_TOO_LARGE$"):
                _read_bounded_catalog_text(candidate)

    def test_direct_huge_string_hold_precedes_json_decode(self):
        with self.assertRaisesRegex(RegistryError, "^CATALOG_TOO_LARGE$"):
            load_catalog_text(" " * (MAX_INVENTORY_BYTES + 1))

    def test_valid_python_literal_types(self):
        self.assertEqual(strict_inventory_loads('{"name":"atlaslattice/noosphere-archive","archived":false,"count":272}'),
                         {"name":"atlaslattice/noosphere-archive","archived":False,"count":272})

    def test_unicode_escaped_duplicate_key_denied(self):
        with self.assertRaisesRegex(InventoryJSONError, "DUPLICATE_REGISTRY_KEY"):
            strict_inventory_loads('{"repo":"public","\\u0072epo":"private"}')

    def test_duplicate_nested_key_denied(self):
        with self.assertRaisesRegex(InventoryJSONError, "DUPLICATE_REGISTRY_KEY"):
            strict_inventory_loads('{"repo":{"visibility":"public","visibility":"private"}}')

    def test_nan_infinity_denied(self):
        for bad in ("NaN", "Infinity", "-Infinity"):
            with self.subTest(bad=bad):
                with self.assertRaisesRegex(InventoryJSONError, "NONFINITE_NUMBER"):
                    strict_inventory_loads('{"value":'+bad+'}')

    def test_numeric_overflow_denied(self):
        with self.assertRaisesRegex(InventoryJSONError, "FLOAT_REGISTRY_VALUE"):
            strict_inventory_loads('{"count":1e9999}')

    def test_decimal_denied(self):
        with self.assertRaisesRegex(InventoryJSONError, "FLOAT_REGISTRY_VALUE"):
            strict_inventory_loads('{"count":3.14}')

    def test_absurd_integer_denied(self):
        with self.assertRaisesRegex(InventoryJSONError, "OVERSIZED_REGISTRY_INTEGER"):
            strict_inventory_loads('{"count":'+ '9'*100 +'}')

    def test_max_bytes_denied(self):
        with self.assertRaisesRegex(InventoryJSONError, "REGISTRY_BYTES_EXCEEDED"):
            strict_inventory_loads(b" "*(MAX_INVENTORY_BYTES+1))

    def test_unpaired_unicode_escape_is_denied(self):
        # Python json.loads accepts these escaped non-scalar code points,
        # but no conforming UTF-8 serialization can represent them.
        for bad in (b'{"note":"\\ud800"}', b'{"note":"\\udc00"}',
                    b'{"\\ud800":1}', b'{"nested":["\\udfff"]}'):
            with self.subTest(raw=bad):
                with self.assertRaisesRegex(InventoryJSONError, 'REGISTRY_JSON_INVALID'):
                    strict_inventory_loads(bad)

    def test_valid_surrogate_pair_remains_accepted(self):
        self.assertEqual(strict_inventory_loads(b'{"note":"\\ud83d\\ude00"}'),
                         {'note': chr(0x1f600)})

    def test_bad_utf8_denied(self):
        with self.assertRaisesRegex(InventoryJSONError, "REGISTRY_JSON_INVALID"):
            strict_inventory_loads(b'{"name":"\xff"}')

    def test_missing_brace_denied(self):
        with self.assertRaisesRegex(InventoryJSONError, "REGISTRY_JSON_INVALID"):
            strict_inventory_loads('{"foo":')

    def test_unknown_nontext_denied(self):
        for bad in (True,0,None,[],{}):
            with self.subTest(bad=bad):
                with self.assertRaisesRegex(InventoryJSONError, "REGISTRY_TEXT_REQUIRED"):
                    strict_inventory_loads(bad)

    def test_valid_raw_bytes_denied_only_if_malformed(self):
        self.assertEqual(strict_inventory_loads(b'{"count":272}'),{"count":272})

    def test_rejects_negative_zero_float_format(self):
        with self.assertRaisesRegex(InventoryJSONError, "FLOAT_REGISTRY_VALUE"):
            strict_inventory_loads('{"count":0.0}')

    def test_rejects_duplicate_keys_after_json_escaping(self):
        with self.assertRaisesRegex(InventoryJSONError, "DUPLICATE_REGISTRY_KEY"):
            strict_inventory_loads('{"a":1,"\\u0061":2}')

    def test_python_unpaired_surrogate_is_a_structured_catalog_hold(self):
        # Simulates a malformed in-process caller; no private source involved.
        with self.assertRaisesRegex(RegistryError, "^REGISTRY_JSON_INVALID$"):
            load_catalog_text('{"note":"' + chr(0xD800) + '"}')

    def test_cli_missing_file_does_not_disclose_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            marker = "synthetic_secret_local_path_do_not_echo.json"
            missing = Path(tmp) / marker
            run = subprocess.run(
                [sys.executable, "-m", "registry.public_registry", "--input", str(missing)],
                cwd=Path(__file__).resolve().parents[1], capture_output=True, text=True,
                check=False,
            )
            self.assertEqual(run.returncode, 2)
            self.assertEqual(json.loads(run.stdout),
                             {"status": "HOLD", "reason": "INPUT_READ_FAILED"})
            self.assertNotIn(marker, run.stdout + run.stderr)

    def test_cli_invalid_utf8_does_not_disclose_filename(self):
        with tempfile.TemporaryDirectory() as tmp:
            marker = "synthetic_secret_invalid_utf8_do_not_echo.json"
            invalid = Path(tmp) / marker
            invalid.write_bytes(bytes([0xff]))
            run = subprocess.run(
                [sys.executable, "-m", "registry.public_registry", "--input", str(invalid)],
                cwd=Path(__file__).resolve().parents[1], capture_output=True, text=True,
                check=False,
            )
            self.assertEqual(run.returncode, 2)
            self.assertEqual(json.loads(run.stdout),
                             {"status": "HOLD", "reason": "INPUT_READ_FAILED"})
            self.assertNotIn(marker, run.stdout + run.stderr)


if __name__ == "__main__":
    unittest.main()
