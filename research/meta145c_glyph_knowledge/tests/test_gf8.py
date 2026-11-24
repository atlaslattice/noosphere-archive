import math,os,tempfile,unittest
from src.gf8 import (Plate, MATERIALS, MODEL, GF7_BANDS,mode_hz,plate_rigidity,phi,
  validity,resonance_table,reference_for_gf7,nodal_mode_glyph,driven_glyph,
  measurement_comparison,gfpayload_hash)
from src.glyph import REGISTRY_SHA
from src.reasoning_filter import prepare_reasoning_context,with_local_review_tip,safe_explanation
from src.memory import LocalMemory

class GF8PhysicalTests(unittest.TestCase):
    def setUp(self):self.p=Plate()
    def test_exact_mode_known(self):self.assertAlmostEqual(mode_hz(self.p,1,1),53.31829013015763,places=9)
    def test_square_mode_symmetry(self):self.assertAlmostEqual(mode_hz(self.p,1,2),mode_hz(self.p,2,1),places=10)
    def test_external_navier_reference_300x200_aluminum(self):
        # Independent reference: planex2d.org/plate-frequencies, SS rectangle
        # 300×200 mm, h=.5 mm aluminum reports 44.162 Hz (nominal material).
        p=Plate(material='aluminum',width_m=.3,height_m=.2,thickness_m=.0005)
        self.assertLess(abs(mode_hz(p,1,1)-44.162),.02)
    def test_frequency_quadruples_halving_size(self):
        q=Plate(width_m=self.p.width_m/2,height_m=self.p.height_m/2)
        self.assertAlmostEqual(mode_hz(q,1,1)/mode_hz(self.p,1,1),4,places=10)
    def test_frequency_doubles_thickness(self):
        q=Plate(thickness_m=self.p.thickness_m*2)
        self.assertAlmostEqual(mode_hz(q,1,1)/mode_hz(self.p,1,1),2,places=10)
    def test_frequency_responds_material(self):
        self.assertNotEqual(mode_hz(Plate(material='aluminum'),1,1),mode_hz(Plate(material='steel'),1,1))
    def test_density_not_added_energy(self):self.assertGreater(plate_rigidity(self.p),0)
    def test_mode_grid_nodes(self):
        g=nodal_mode_glyph(self.p,2,3,grid=49)
        self.assertEqual(g['bitmap'][0],'1'*49)
        self.assertEqual(g['bitmap'][-1],'1'*49)
        self.assertTrue(all(row[0]=='1' and row[-1]=='1' for row in g['bitmap']))
        self.assertEqual(g['bitmap'][24][24],'1') # m=2 central vertical nodal line
    def test_antinode(self):self.assertAlmostEqual(phi(1,1,.5,.5),1)
    def test_nodal_excitation(self):self.assertAlmostEqual(phi(2,1,.5,.5),0,places=14)
    def test_drive_tuned_resonance(self):
        x=driven_glyph(self.p,mode_hz(self.p,1,1),max_mode=6,grid=21)
        self.assertEqual(x['status'],'ANALYTIC_DRIVEN_FIELD_NEAR_RESONANCE')
        self.assertEqual((len(x['amplitude_proxy']),len(x['amplitude_proxy'][0])),(21,21))
        self.assertFalse(x['physical_measurement'])
        self.assertEqual(max(max(row) for row in x['amplitude_proxy']),1.0)
    def test_off_resonance_rejected(self):
        x=driven_glyph(self.p,1.0,max_mode=6,grid=21)
        self.assertEqual(x['status'],'HOLD_NO_EXCITABLE_RESONANCE_IN_TRUNCATED_MODEL')
        self.assertIsNone(x['field'])
    def test_high_out_of_basis_hold(self):
        x=driven_glyph(self.p,1e6,max_mode=6,grid=21)
        self.assertEqual(x['status'],'HOLD_NO_EXCITABLE_RESONANCE_IN_TRUNCATED_MODEL')
    def test_invalid_plate_boundary(self):
        with self.assertRaisesRegex(ValueError,'UNSUPPORTED_BOUNDARY'):
            mode_hz(Plate(boundary='FREE_ALL_EDGES'),1,1)
    def test_invalid_material(self):
        with self.assertRaisesRegex(ValueError,'UNSUPPORTED_MATERIAL'):mode_hz(Plate(material='unobtainium'),1,1)
    def test_invalid_geometry(self):
        with self.assertRaises(ValueError):mode_hz(Plate(width_m=-1),1,1)
    def test_bad_nan(self):
        with self.assertRaises(ValueError):mode_hz(Plate(thickness_m=float('nan')),1,1)
    def test_bad_bool(self):
        with self.assertRaises(ValueError):mode_hz(Plate(width_m=True),1,1)
    def test_bad_mode(self):
        for m,n in [(0,1),(1,0),(25,1),(1,25),(True,1)]:
            with self.subTest(m=m,n=n),self.assertRaises(ValueError):mode_hz(self.p,m,n)
    def test_mode_catalog_sorted(self):
        rs=resonance_table(self.p,6,6);self.assertEqual(len(rs),36)
        self.assertEqual(rs[0]['m'],1);self.assertEqual(rs[0]['n'],1)
        self.assertEqual([r['frequency_hz'] for r in rs],sorted(r['frequency_hz'] for r in rs))
    def test_mode_bending_wavelength(self):
        v=validity(self.p,1,1);self.assertEqual(v['status'],'SCREENING_MODEL_IN_ENVELOPE')
        self.assertFalse(v['empirically_validated'])
    def test_reference_inverse_target(self):
        for b in range(1,13):
            x=reference_for_gf7(f'GF7.B{b:02d}.M01.C05')
            with self.subTest(b=b):
                self.assertLess(x['relative_design_residual'],1e-12)
                self.assertEqual(x['frequency_band_hz'][0],GF7_BANDS[b-1][0])
    def test_bands_honest_hold(self):
        low=reference_for_gf7('GF7.B01.M01.C05')
        hi=reference_for_gf7('GF7.B12.M01.C05')
        self.assertEqual(low['model_validity']['status'],'HOLD_MODEL_ENVELOPE')
        self.assertEqual(hi['model_validity']['status'],'HOLD_MODEL_ENVELOPE')
    def test_middle_band_feasible(self):
        x=reference_for_gf7('GF7.B05.M01.C05')
        self.assertEqual(x['model_validity']['status'],'SCREENING_MODEL_IN_ENVELOPE')
    def test_all_1728_gf7_cards(self):
        rows=[reference_for_gf7(f'GF7.B{b:02d}.M{m:02d}.C{c:02d}')
              for b in range(1,13) for m in range(1,13) for c in range(1,13)]
        self.assertEqual(len(rows),1728)
        self.assertEqual(len({r['source_coordinate'] for r in rows}),1728)
        self.assertTrue(all(r['not_atlas_semantic_mapping'] for r in rows))
    def test_high_mode_not_thin_plate(self):
        p=Plate(width_m=.1,height_m=.1,thickness_m=.01)
        self.assertEqual(validity(p,12,12)['status'],'HOLD_MODEL_ENVELOPE')
    def test_evidence_never_auto_calibrated(self):
        r=measurement_comparison(self.p,1,1,53.4,'urn:atlas:synthetic:freq','a'*64)
        self.assertFalse(r['calibration_done'])
        self.assertFalse(r['observed_raw_data_read'])
        self.assertGreater(r['relative_abs_error'],0)
    def test_evidence_digest_required(self):
        with self.assertRaises(ValueError):measurement_comparison(self.p,1,1,53.4,'wrong','invalid')
    def test_glyph_hash_order_stable(self):
        self.assertEqual(gfpayload_hash({'a':1,'b':2}),gfpayload_hash({'b':2,'a':1}))

class ReasoningFilterTests(unittest.TestCase):
    def setUp(self):
        self.p=Plate();self.f=mode_hz(self.p,1,1)
        self.kw=dict(hsn='H01.S05.N10',gf7='GF7.B01.M05.C10',plate=self.p,drive_hz=self.f,
                     source_refs=('https://pmc.ncbi.nlm.nih.gov/articles/PMC6812332/',))
    def test_context_does_not_train_model(self):
        p=prepare_reasoning_context(**self.kw)
        self.assertFalse(p['model_weight_updates']);self.assertFalse(p['canon_writes'])
        self.assertFalse(p['protected_mode_imported'])
        self.assertEqual(p['physical_model_output']['status'],'ANALYTIC_DRIVEN_FIELD_NEAR_RESONANCE')
    def test_no_high_dimensional_field_in_prompt(self):
        p=prepare_reasoning_context(**self.kw)
        self.assertNotIn('amplitude_proxy',str(p));self.assertNotIn('nodal_proxy_bitmap',str(p))
    def test_no_auto_hsn_equivalence(self):
        p=prepare_reasoning_context(**self.kw)
        self.assertIn('NOT_SEMANTIC_SAME_AS',p['gf7_relation'])
    def test_private_mode_block(self):
        with self.assertRaises(ValueError):prepare_reasoning_context(**{**self.kw,'work_mode':'IMAGINE'})
    def test_source_pin_block(self):
        with self.assertRaises(ValueError):prepare_reasoning_context(**{**self.kw,'source_digest':'a'*64})
    def test_malicious_reference_block(self):
        with self.assertRaises(ValueError):prepare_reasoning_context(**{**self.kw,'source_refs':('http://localhost:8000/private',)})
    def test_packet_hash_detects_tamper(self):
        p=prepare_reasoning_context(**self.kw)
        self.assertIn('nearest modeled mode',safe_explanation(p))
        with self.assertRaises(ValueError):safe_explanation({**p,'drive_frequency_hz':1e6})
    def test_memory_tip_changes_only_context(self):
        with tempfile.TemporaryDirectory() as tmp:
            db=os.path.join(tmp,'mem.sqlite');m=LocalMemory(db)
            p=prepare_reasoning_context(**self.kw)
            old=p['receipt_sha256'];first=with_local_review_tip(p,m)
            self.assertNotEqual(first['receipt_sha256'],old)
            m.append({'event_id':'note-gf8-001','mode':'WORK','scope':'SYNTHETIC_LOCAL_REVIEW',
                      'coordinate':'H01.S05.N10','topic_id':None,'action':'NOTE',
                      'source_ref':'urn:atlas:synthetic:gf8-demo','source_digest':'b'*64})
            q=with_local_review_tip(p,m);self.assertNotEqual(q['receipt_sha256'],first['receipt_sha256'])
            self.assertFalse(q['model_weight_updates']);m.close()
            reopened=LocalMemory(db)
            self.assertEqual(with_local_review_tip(p,reopened)['receipt_sha256'],q['receipt_sha256'])
            reopened.close()
    def test_no_user_supplied_authority(self):
        with self.assertRaises(TypeError):prepare_reasoning_context(**{**self.kw,'canon_approved':True})

if __name__=='__main__':unittest.main()
