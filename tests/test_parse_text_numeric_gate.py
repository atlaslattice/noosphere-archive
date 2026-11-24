"""Numeric source-text gate regression; source-only and dependency-free."""
import unittest
from core.digital_continuity import parse_text, ContinuityHold


class NumericHolds(unittest.TestCase):
    def test_overflow_number_holds(self):
        with self.assertRaisesRegex(ContinuityHold, 'NONFINITE_JSON_NUMBER'):
            parse_text('{"weight":1e10000}')

    def test_underflow_nonzero_holds(self):
        with self.assertRaisesRegex(ContinuityHold, 'UNDERFLOW_JSON_NUMBER'):
            parse_text('{"weight":1e-10000}')

    def test_negative_underflow_holds(self):
        with self.assertRaisesRegex(ContinuityHold, 'UNDERFLOW_JSON_NUMBER'):
            parse_text('{"weight":-1e-10000}')

    def test_exact_zero_and_subnormal_allowed(self):
        self.assertEqual(parse_text('{"weight":0e-10000}')["weight"],0.0)
        self.assertGreater(parse_text('{"weight":5e-324}')["weight"],0.0)

    def test_duplicate_and_nan_still_hold(self):
        for raw in ('{"a":1,"a":2}', '{"a":NaN}'):
            with self.subTest(raw=raw), self.assertRaises(ContinuityHold):
                parse_text(raw)

if __name__ == '__main__':
    unittest.main()
