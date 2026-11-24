"""Regression coverage for PR41 using the real, source-only GF8 model.

No dependency stubs, original registry, external service or physical device.
These tests check numerical-claim/context integrity, not host authority.
"""
from copy import deepcopy
from pathlib import Path
import tempfile
import unittest

from src.gf8 import Plate, mode_hz
from src.memory import LocalMemory
from src.reasoning_filter import (
    postflight_claim_gate, prepare_reasoning_context,
    safe_explanation, with_local_review_tip,
)


class ReasoningFilterIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.memory = LocalMemory(Path(self.tmp.name) / 'review.sqlite')
        self.plate = Plate()
        self.frequency = mode_hz(self.plate, 1, 1)
        self.packet = prepare_reasoning_context(
            hsn='H01.S07.N12', gf7='GF7.B01.M07.C12', plate=self.plate,
            drive_hz=self.frequency, max_mode=2, grid=17)

    def tearDown(self):
        self.memory.close()
        self.tmp.cleanup()

    def claim(self, **changes):
        return {'claim_kind': 'GF8_PREDICTED_MODE_ONLY',
                'frequency_hz': self.frequency,
                'model_status': self.packet['physical_model_output']['status'],
                **changes}

    def test_matching_calculation_preserves_all_nonclaims(self):
        result = postflight_claim_gate(self.packet, self.claim())
        self.assertEqual(result['status'], 'SOURCE_CALCULATION_PARITY_PASS_ONLY')
        for key in ('experiment_validated', 'semantic_approval',
                    'model_weights_changed', 'host_authorized'):
            self.assertIs(result[key], False)
        self.assertEqual(result['canon_effect'], 'NONE')

    def test_nan_cannot_pass_numerical_parity(self):
        self.assertEqual(postflight_claim_gate(self.packet, self.claim(frequency_hz=float('nan')))['status'],
                         'HOLD_NUMERICAL_CONTRADICTION')

    def test_positive_infinity_is_held(self):
        self.assertEqual(postflight_claim_gate(self.packet, self.claim(frequency_hz=float('inf')))['status'],
                         'HOLD_NUMERICAL_CONTRADICTION')

    def test_negative_infinity_is_held(self):
        self.assertEqual(postflight_claim_gate(self.packet, self.claim(frequency_hz=-float('inf')))['status'],
                         'HOLD_NUMERICAL_CONTRADICTION')

    def test_oversized_integer_is_held_without_throwing(self):
        self.assertEqual(postflight_claim_gate(self.packet, self.claim(frequency_hz=10**1000))['status'],
                         'HOLD_NUMERICAL_CONTRADICTION')

    def test_boolean_is_not_a_frequency(self):
        self.assertEqual(postflight_claim_gate(self.packet, self.claim(frequency_hz=True))['status'],
                         'HOLD_NUMERICAL_CONTRADICTION')

    def test_numeric_string_is_not_a_frequency(self):
        self.assertEqual(postflight_claim_gate(self.packet, self.claim(frequency_hz=str(self.frequency)))['status'],
                         'HOLD_NUMERICAL_CONTRADICTION')

    def test_finite_wrong_frequency_is_held(self):
        self.assertEqual(postflight_claim_gate(self.packet, self.claim(frequency_hz=self.frequency*2))['status'],
                         'HOLD_NUMERICAL_CONTRADICTION')

    def test_measurement_grade_cannot_be_claimed(self):
        self.assertEqual(postflight_claim_gate(self.packet, self.claim(model_status='PHYSICALLY_MEASURED'))['status'],
                         'HOLD_EVIDENCE_GRADE_CONTRADICTION')

    def test_model_cannot_change_claim_kind_to_authorization(self):
        self.assertEqual(postflight_claim_gate(self.packet, self.claim(claim_kind='HOST_AUTHORIZED'))['status'],
                         'HOLD_UNSUPPORTED_CLAIM_KIND')

    def test_extra_authority_field_is_held(self):
        self.assertEqual(postflight_claim_gate(self.packet, self.claim(host_authorized=True))['status'],
                         'HOLD_UNEXPECTED_OUTPUT_SHAPE')

    def test_valid_refresh_preserves_physics_and_unverified_authority(self):
        self.memory.append({'event_id': 'note01', 'mode': 'WORK',
            'scope': 'SYNTHETIC_LOCAL_REVIEW', 'coordinate': 'H01.S07.N12',
            'action': 'NOTE', 'source_ref': 'urn:atlas:synthetic:gf8-regression',
            'source_digest': 'a'*64})
        original = deepcopy(self.packet)
        refreshed = with_local_review_tip(self.packet, self.memory)
        self.assertEqual(self.packet, original)
        self.assertEqual(refreshed['physical_model_output'], self.packet['physical_model_output'])
        self.assertEqual(refreshed['synthetic_review_tip_sha256'], self.memory.verify()['tip'])
        self.assertEqual(refreshed['authorization'], 'UNVERIFIED_REQUIRE_HOST_READ_AND_RETURN')
        self.assertFalse(refreshed['model_weight_updates'])
        self.assertFalse(refreshed['canon_writes'])
        self.assertIn('No model weights changed', safe_explanation(refreshed))

    def test_refresh_cannot_reseal_changed_frequency(self):
        self.packet['physical_model_output']['nearest_mode']['frequency_hz'] *= 2
        before = deepcopy(self.packet)
        with self.assertRaisesRegex(ValueError, 'CONTEXT_SOURCE_TAMPERED'):
            with_local_review_tip(self.packet, self.memory)
        self.assertEqual(self.packet, before)

    def test_refresh_cannot_reseal_changed_authorization(self):
        self.packet['authorization'] = 'HOST_AUTHORIZED'
        with self.assertRaisesRegex(ValueError, 'CONTEXT_SOURCE_TAMPERED'):
            with_local_review_tip(self.packet, self.memory)

    def test_refresh_requires_original_receipt(self):
        del self.packet['receipt_sha256']
        with self.assertRaisesRegex(ValueError, 'INVALID_CONTEXT_PACKET'):
            with_local_review_tip(self.packet, self.memory)

    def test_refresh_rejects_corrupted_review_ledger(self):
        self.memory.append({'event_id': 'note01', 'mode': 'WORK',
            'scope': 'SYNTHETIC_LOCAL_REVIEW', 'coordinate': 'H01.S07.N12',
            'action': 'NOTE', 'source_ref': 'urn:atlas:synthetic:gf8-regression',
            'source_digest': 'a'*64})
        self.memory.db.execute("UPDATE review_events SET action='CHALLENGE'")
        self.memory.db.commit()
        with self.assertRaisesRegex(ValueError, 'MEMORY_TAMPERED'):
            with_local_review_tip(self.packet, self.memory)


if __name__ == '__main__':
    unittest.main()
