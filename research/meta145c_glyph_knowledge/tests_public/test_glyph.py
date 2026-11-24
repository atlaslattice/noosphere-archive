import unittest
from src.glyph import *

class GlyphTests(unittest.TestCase):
    def test_bounds(self):
        self.assertEqual(hsn_parts('H01.S01.N01'),(1,1,1));self.assertEqual(hsn_parts('H12.S12.N12'),(12,12,12))
    def test_invalid_hsn(self):
        for x in ['H00.S01.N01','H13.S01.N01','H01.S00.N01','H01.S13.N01','H01.S01.N00','H01.S01.N13','H1.S1.N1','H01.S01.N01 extra','','GF7.B01.M01.C01',None]:
            with self.subTest(x=x),self.assertRaises(ValueError):hsn_parts(x)
    def test_gf7_bounds(self):
        self.assertEqual(gf7_parts('GF7.B01.M01.C01'),(1,1,1));self.assertEqual(gf7_parts('GF7.B12.M12.C12'),(12,12,12))
    def test_full_distinct_1728(self):
        addresses=[f'H{h:02d}.S{s:02d}.N{n:02d}' for h in range(1,13) for s in range(1,13) for n in range(1,13)]
        gf=[positional_gf7(x) for x in addresses]
        axg=[encode_axg1(x,REGISTRY_SHA) for x in addresses]
        self.assertEqual((len(set(gf)),len(set(axg))),(1728,1728))
        self.assertEqual([decode_axg1(y,REGISTRY_SHA) for y in axg],addresses)
        self.assertEqual([gf7_positional_hsn(y) for y in gf],addresses)
    def test_gf7_modes(self):self.assertEqual(len(GF7_MODES),12);self.assertEqual(len(set(GF7_MODES)),12)
    def test_gf7_bands(self):self.assertEqual(len(GF7_BANDS),12);self.assertTrue(all(a>0 and b>a for a,b in GF7_BANDS))
    def test_gf7_context(self):self.assertEqual(len(GF7_MATERIALS),12);self.assertEqual(len(set(GF7_MATERIALS)),12)
    def test_gf7_report_nonclaim(self):
        d=gf7_descriptor('GF7.B12.M12.C12');self.assertFalse(d['physical_measurement']);self.assertFalse(d['atlas_semantic_equivalence']);self.assertIn('ANALYTIC',d['prediction_status'])
    def test_gf7_not_original(self):
        route=typed_route('H01.S05.N10',REGISTRY_SHA);self.assertIn('NOT_SEMANTIC',route['relationship_type']);self.assertEqual(route['kg8_alias'],'RESOLVE_FROM_CURRENT_AUTHORIZED_KG8_SOURCE')
    def test_glyph_names(self):self.assertEqual(len(GLYPHFORGE_HISTORIC_NAMES),3)
    def test_glyph_forgery(self):
        good=encode_axg1('H01.S05.N10',REGISTRY_SHA)
        for v in [good[:-1]+'f',good.replace('H01','H02'),good.replace('AXG1','KG8Q'),good+'XX']:
            if v==good:continue
            with self.assertRaises(ValueError):decode_axg1(v,REGISTRY_SHA)
    def test_wrong_version(self):
        with self.assertRaises(ValueError):decode_axg1(encode_axg1('H01.S05.N10',REGISTRY_SHA),'a'*64)
    def test_bad_digest(self):
        with self.assertRaises(ValueError):encode_axg1('H01.S05.N10','a'*32)
    def test_invalid_gf(self):
        for x in ['GF7.B00.M01.C01','GF7.B13.M01.C01','GF7.B01.M13.C01','GF7.B01.M01.C99','H01.S01.N01','GF7.B1.M1.C1']:
            with self.subTest(x=x),self.assertRaises(ValueError):gf7_parts(x)
