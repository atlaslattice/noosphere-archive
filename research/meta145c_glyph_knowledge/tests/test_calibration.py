import unittest
from src.calibration import compare_nodal_masks,calibration_candidate
from src.gf8 import Plate,nodal_mode_glyph,mode_hz
from src.reasoning_filter import prepare_reasoning_context,postflight_claim_gate
from src.glyph import REGISTRY_SHA

class LaboratoryBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.p=Plate();self.g=nodal_mode_glyph(self.p,2,3,grid=33)['bitmap']
    def test_identical_mask_is_identical(self):
        res=compare_nodal_masks(self.g,self.g)
        self.assertEqual(res['intersection_over_union'],1)
        self.assertEqual(res['symmetric_chamfer_pixels'],0)
        self.assertFalse(res['validated_experiment'])
    def test_shifted_mask_not_automatically_matches(self):
        altered=[r[1:]+'0' for r in self.g]
        res=compare_nodal_masks(self.g,altered)
        self.assertLess(res['intersection_over_union'],1)
    def test_missing_nodes_held(self):
        with self.assertRaisesRegex(ValueError,'NO_NODES'):
            compare_nodal_masks(self.g,['0'*33]*33)
    def test_inconsistent_shape_held(self):
        with self.assertRaises(ValueError):compare_nodal_masks(self.g,['1'*32]*32)
    def test_nonsensical_pattern_held(self):
        with self.assertRaises(ValueError):compare_nodal_masks(self.g,['x'*33]*33)
    def test_dense_unsegmented_held(self):
        with self.assertRaises(ValueError):compare_nodal_masks(self.g,['1'*65]*65)
    def test_calibration_candidate_does_not_promote(self):
        c=calibration_candidate(self.p,2,3,mode_hz(self.p,2,3),self.g,self.g,
             raw_capture_sha256='f'*64,source_ref='urn:atlas:synthetic:gf8-camera',registration_method='FIDUCIAL_AFFINE')
        self.assertFalse(c['expert_accepted']);self.assertFalse(c['calibrated'])
        self.assertFalse(c['instrument_verified']);self.assertEqual(c['nodal_metrics']['intersection_over_union'],1)
    def test_raw_source_required(self):
        with self.assertRaises(ValueError):calibration_candidate(self.p,2,3,100,self.g,self.g,raw_capture_sha256='bad',source_ref='no',registration_method='FIDUCIAL_AFFINE')
    def test_wrong_registration_rejected(self):
        with self.assertRaises(ValueError):calibration_candidate(self.p,2,3,100,self.g,self.g,raw_capture_sha256='f'*64,source_ref='urn:atlas:synthetic:x',registration_method='auto-trust-me')

class FilterOutputChecks(unittest.TestCase):
    def setUp(self):
        self.p=Plate()
        self.packet=prepare_reasoning_context(hsn='H01.S05.N10',gf7='GF7.B01.M05.C10',plate=self.p,drive_hz=mode_hz(self.p,1,1))
        self.claim={'claim_kind':'GF8_PREDICTED_MODE_ONLY','frequency_hz':self.packet['physical_model_output']['nearest_mode']['frequency_hz'],
                    'model_status':self.packet['physical_model_output']['status']}
    def test_valid_structured_numeric_claim(self):
        r=postflight_claim_gate(self.packet,self.claim)
        self.assertEqual(r['status'],'SOURCE_CALCULATION_PARITY_PASS_ONLY')
        self.assertFalse(r['experiment_validated'])
    def test_forged_measurement_claim_rejected(self):
        r=postflight_claim_gate(self.packet,{**self.claim,'claim_kind':'MEASURED_VALIDATED'})
        self.assertEqual(r['status'],'HOLD_UNSUPPORTED_CLAIM_KIND')
    def test_model_fabricated_frequency_rejected(self):
        r=postflight_claim_gate(self.packet,{**self.claim,'frequency_hz':123.4})
        self.assertEqual(r['status'],'HOLD_NUMERICAL_CONTRADICTION')
    def test_status_promotion_rejected(self):
        r=postflight_claim_gate(self.packet,{**self.claim,'model_status':'PHYSICALLY_VALIDATED'})
        self.assertEqual(r['status'],'HOLD_EVIDENCE_GRADE_CONTRADICTION')
    def test_rogue_host_field_rejected(self):
        r=postflight_claim_gate(self.packet,{**self.claim,'host_authorized':True})
        self.assertEqual(r['status'],'HOLD_UNEXPECTED_OUTPUT_SHAPE')
    def test_input_receipt_tamper_is_rejected(self):
        with self.assertRaises(ValueError):postflight_claim_gate({**self.packet,'hsn':'H12.S12.N12'},self.claim)

if __name__=='__main__':unittest.main()
