"""Adversarial Unicode source-key ambiguity controls; stdlib only."""
import unittest

from registry.strict_inventory_json import InventoryJSONError, strict_inventory_loads


class UnicodeKeyCollisionTests(unittest.TestCase):
    def test_canonical_equivalent_spellings_hold(self):
        for raw in ('{"e\\u0301":1,"\\u00e9":2}',
                    '{"\\u00e9":1,"e\\u0301":2}',
                    '{"nested":{"e\\u0301":1,"\\u00e9":2}}'):
            with self.subTest(raw=raw):
                with self.assertRaisesRegex(InventoryJSONError,
                                             "^CANONICAL_EQUIVALENT_REGISTRY_KEY$"):
                    strict_inventory_loads(raw)

    def test_exact_decoded_duplicate_still_has_original_code(self):
        with self.assertRaisesRegex(InventoryJSONError, "^DUPLICATE_REGISTRY_KEY$"):
            strict_inventory_loads('{"na\\u006de":1,"name":2}')

    def test_single_decomposed_key_reaches_later_schema_validation(self):
        self.assertEqual(strict_inventory_loads('{"e\\u0301":1}'), {"e\\u0301": 1})

    def test_case_distinction_is_preserved(self):
        self.assertEqual(strict_inventory_loads('{"Name":1,"name":2}'),
                         {"Name": 1, "name": 2})

    def test_normal_public_metadata_stays_accepted(self):
        self.assertEqual(strict_inventory_loads('{"name":"atlas","count":272}'),
                         {"name":"atlas","count":272})


if __name__ == "__main__":
    unittest.main()
