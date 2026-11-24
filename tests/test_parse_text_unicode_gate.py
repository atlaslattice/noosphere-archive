"""Synthetic Unicode scalar controls for offline public-source continuity parser."""
import unittest
from core.digital_continuity import (
    ContinuityHold, _snapshot_plain_json, canonical_sha256, parse_text
)


class UnicodeScalarHolds(unittest.TestCase):
    def test_high_surrogate_json_value_holds(self):
        with self.assertRaisesRegex(ContinuityHold, "INVALID_UNICODE_SCALAR"):
            parse_text('{"field":"\\ud800"}')

    def test_low_surrogate_json_key_holds(self):
        with self.assertRaisesRegex(ContinuityHold, "INVALID_UNICODE_SCALAR"):
            parse_text('{"\\udfff":"value"}')

    def test_nested_surrogate_holds(self):
        with self.assertRaisesRegex(ContinuityHold, "INVALID_UNICODE_SCALAR"):
            parse_text('{"a":[1,{"b":"\\udc00"}]}')

    def test_python_caller_surrogate_holds_before_hash(self):
        with self.assertRaisesRegex(ContinuityHold, "NON_JSON_OR_MUTABLE_INPUT_HOLD"):
            _snapshot_plain_json({"field": "\ud800"})

    def test_valid_paired_emoji_escape_can_hash(self):
        parsed = parse_text('{"field":"\\ud83d\\ude00"}')
        self.assertEqual(parsed["field"], "\U0001F600")
        self.assertEqual(len(canonical_sha256(parsed)), 64)

    def test_prior_numeric_and_duplicate_guards_remain(self):
        for sample in (
            '{"a":1e10000}', '{"a":1e-10000}', '{"a":NaN}', '{"a":1,"a":2}'
        ):
            with self.subTest(sample=sample), self.assertRaises(ContinuityHold):
                parse_text(sample)
        self.assertEqual(parse_text('{"a":0e-10000}')["a"], 0.0)
        self.assertGreater(parse_text('{"a":5e-324}')["a"], 0.0)


if __name__ == "__main__":
    unittest.main()
