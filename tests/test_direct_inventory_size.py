"""Synthetic direct-parser size tests; no external state."""
import unittest
from registry.strict_inventory_json import (
    InventoryJSONError, MAX_INVENTORY_BYTES, strict_inventory_loads,
)


class DirectInventorySize(unittest.TestCase):
    def test_oversized_text_size_precedes_encoding(self):
        # An oversized str cannot fit UTF-8 even before examining its contents.
        raw = ' ' * MAX_INVENTORY_BYTES + chr(0xd800)
        with self.assertRaisesRegex(InventoryJSONError, '^REGISTRY_BYTES_EXCEEDED$'):
            strict_inventory_loads(raw)

    def test_oversized_ascii_text(self):
        with self.assertRaisesRegex(InventoryJSONError, '^REGISTRY_BYTES_EXCEEDED$'):
            strict_inventory_loads(' ' * (MAX_INVENTORY_BYTES + 1))

    def test_exact_ascii_limit(self):
        self.assertEqual(strict_inventory_loads('{}' + ' ' * (MAX_INVENTORY_BYTES - 2)), {})

    def test_multibyte_byte_limit(self):
        raw = '"' + 'é' * (MAX_INVENTORY_BYTES // 2) + '"'
        self.assertLess(len(raw), MAX_INVENTORY_BYTES)
        with self.assertRaisesRegex(InventoryJSONError, '^REGISTRY_BYTES_EXCEEDED$'):
            strict_inventory_loads(raw)

    def test_small_malformed_text(self):
        with self.assertRaisesRegex(InventoryJSONError, '^REGISTRY_JSON_INVALID$'):
            strict_inventory_loads('"' + chr(0xd800) + '"')

    def test_bytes_limit(self):
        with self.assertRaisesRegex(InventoryJSONError, '^REGISTRY_BYTES_EXCEEDED$'):
            strict_inventory_loads(b' ' * (MAX_INVENTORY_BYTES + 1))

    def test_existing_duplicate_and_float_holds(self):
        for raw, code in [('{"x":1,"x":2}', 'DUPLICATE_REGISTRY_KEY'),
                          ('{"x":1e999}', 'FLOAT_REGISTRY_VALUE')]:
            with self.subTest(raw=raw), self.assertRaisesRegex(InventoryJSONError, '^' + code + '$'):
                strict_inventory_loads(raw)
