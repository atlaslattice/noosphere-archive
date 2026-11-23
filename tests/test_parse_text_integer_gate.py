"""Public synthetic regressions: bounded JSON integer conversion stays a HOLD."""
import unittest

from core.digital_continuity import (
    ContinuityHold, _snapshot_plain_json, parse_text
)


class OversizedIntegerHolds(unittest.TestCase):
    def test_large_positive_integer_holds(self):
        for digits in (4301, 5000, 50000):
            with self.subTest(digits=digits), self.assertRaisesRegex(
                ContinuityHold, "OVERSIZED_JSON_INTEGER"
            ):
                parse_text('{"n":' + "9" * digits + "}")

    def test_large_negative_integer_holds(self):
        with self.assertRaisesRegex(ContinuityHold, "OVERSIZED_JSON_INTEGER"):
            parse_text('{"n":-' + "9" * 5000 + "}")

    def test_standard_numbers_still_parse(self):
        parsed = parse_text('{"n":-123456,"zero":0,"fraction":0.125}')
        self.assertEqual(parsed, {"n": -123456, "zero": 0, "fraction": 0.125})
        self.assertEqual(parse_text('{"n":' + "9" * 120 + "}")["n"], int("9" * 120))

    def test_prior_strict_gates_still_hold(self):
        for raw in (
            '{"n":NaN}', '{"n":1e10000}', '{"n":1e-10000}',
            '{"n":1,"n":2}', '{"n":"\\ud800"}'
        ):
            with self.subTest(raw=raw), self.assertRaises(ContinuityHold):
                parse_text(raw)

    def test_python_caller_oversized_integer_holds(self):
        with self.assertRaisesRegex(
            ContinuityHold, "NON_JSON_OR_MUTABLE_INPUT_HOLD"
        ):
            _snapshot_plain_json({"n": 10 ** 5000})


if __name__ == "__main__":
    unittest.main()
