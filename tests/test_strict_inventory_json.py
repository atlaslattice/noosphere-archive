"""No GitHub calls, secrets, or writable external state."""
import json
import unittest
from pathlib import Path
from registry.public_registry import RegistryError, validate_catalog
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


if __name__ == "__main__":
    unittest.main()
