"""Synthetic decoder nesting regressions, source-only."""
import unittest

from core.digital_continuity import ContinuityHold, parse_text


class DecoderNestingHolds(unittest.TestCase):
    def test_deep_array_holds(self):
        with self.assertRaisesRegex(ContinuityHold, "JSON_NESTING_LIMIT"):
            parse_text("[" * 10000 + "0" + "]" * 10000)

    def test_deep_object_holds(self):
        with self.assertRaisesRegex(ContinuityHold, "JSON_NESTING_LIMIT"):
            parse_text('{"x":' * 10000 + "0" + "}" * 10000)

    def test_normal_nesting_and_bracket_strings(self):
        self.assertEqual(parse_text('{"x":[{"y":"[[[]]]"}]}'),
                         {"x": [{"y": "[[[]]]"}]})

    def test_previous_strict_gates_preserved(self):
        for raw, code in (
            ('{"x":1,"x":2}', "DUPLICATE_JSON_KEY"),
            ('[1e9999]', "NONFINITE_JSON_NUMBER"),
            ('["\\ud800"]', "INVALID_UNICODE_SCALAR"),
            ('[' + '9' * 5000 + ']', "OVERSIZED_JSON_INTEGER"),
        ):
            with self.subTest(code=code), self.assertRaisesRegex(ContinuityHold, code):
                parse_text(raw)


if __name__ == "__main__":
    unittest.main()
